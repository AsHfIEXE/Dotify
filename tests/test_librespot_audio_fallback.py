from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from dotify.api.enums import SessionType
from dotify.interface.audio import SpotifyAudioInterface
from dotify.interface.enums import AudioQuality
from dotify.interface.exceptions import DotifyLibrespotAudioKeyException
from dotify.interface.types import DecryptionKey, StreamInfo, StreamInfoAv


def stream(*, pssh=None, file_format="ogg", file_id=b"file-id") -> StreamInfoAv:
    return StreamInfoAv(
        audio_track=StreamInfo(
            stream_url="https://audio.test/file",
            widevine_pssh=pssh,
            file_format=file_format,
            file_id=file_id,
        )
    )


@pytest.mark.asyncio
async def test_librespot_audio_key_failure_gets_a_specific_error():
    manager_logger = MagicMock()

    class AudioKeyManager:
        logger = manager_logger

        def get_audio_key(self, _gid, _file_id):
            raise RuntimeError(
                "Failed fetching audio key! gid: gid, fileId: file"
            )

    api = SimpleNamespace(
        librespot=SimpleNamespace(
            session=SimpleNamespace(audio_key=lambda: AudioKeyManager())
        ),
        media_id_to_gid=lambda _media_id: "00" * 16,
    )
    audio = SpotifyAudioInterface.__new__(SpotifyAudioInterface)
    audio.api = api

    with pytest.raises(DotifyLibrespotAudioKeyException) as captured:
        await audio.get_librespot_decryption_key("track-id", b"file-id")

    assert "code 1" in str(captured.value)
    assert captured.value.media_id == "track-id"
    manager_logger.addFilter.assert_called_once()


@pytest.mark.asyncio
async def test_librespot_audio_key_failure_falls_back_to_web_when_wvd_exists():
    librespot_stream = stream()
    web_stream = stream(pssh="widevine-pssh", file_format="mp4", file_id=b"web")
    web_key = DecryptionKey(decryption_key="ab" * 16)

    audio = SpotifyAudioInterface.__new__(SpotifyAudioInterface)
    audio.api = SimpleNamespace(
        session_type=SessionType.LIBRESPOT,
        premium_session=True,
    )
    audio.cdm = object()
    audio.audio_quality_priority = [
        AudioQuality.VORBIS_HIGH,
        AudioQuality.VORBIS_MEDIUM,
    ]
    audio.get_stream_info = AsyncMock(return_value=librespot_stream)
    audio.get_decryption_key = AsyncMock(
        side_effect=[
            DotifyLibrespotAudioKeyException("track-id", b"file-id"),
            web_key,
        ]
    )
    audio._get_stream_info_web = AsyncMock(return_value=web_stream)

    resolved_stream, resolved_key = await audio.get_stream_info_with_decryption_key(
        "track-id",
        "track",
    )

    assert resolved_stream is web_stream
    assert resolved_key is web_key
    assert resolved_stream.audio_track.fallback_from == "vorbis-high,vorbis-medium"
    assert resolved_stream.audio_track.fallback_reason == "librespot-audio-key"
    assert audio._get_stream_info_web.await_args.kwargs["audio_quality"] == AudioQuality.AAC_HIGH


@pytest.mark.asyncio
async def test_librespot_audio_key_failure_does_not_fallback_without_wvd():
    audio = SpotifyAudioInterface.__new__(SpotifyAudioInterface)
    audio.api = SimpleNamespace(
        session_type=SessionType.LIBRESPOT,
        premium_session=True,
    )
    audio.cdm = None
    audio.get_stream_info = AsyncMock(return_value=stream())
    audio.get_decryption_key = AsyncMock(
        side_effect=DotifyLibrespotAudioKeyException("track-id", b"file-id")
    )
    audio._get_stream_info_web = AsyncMock()

    with pytest.raises(DotifyLibrespotAudioKeyException):
        await audio.get_stream_info_with_decryption_key("track-id", "track")

    audio._get_stream_info_web.assert_not_awaited()


@pytest.mark.asyncio
async def test_librespot_uses_alternative_gid_when_primary_has_no_file():
    quality = AudioQuality.VORBIS_MEDIUM
    audio_file = SimpleNamespace(
        format=int(quality.format_id),
        file_id=b"alternative-file",
    )
    alternative = SimpleNamespace(gid=b"alternative-gid", file=[])
    primary_metadata = SimpleNamespace(file=[], alternative=[alternative])
    alternative_metadata = SimpleNamespace(file=[audio_file], alternative=[])
    metadata_api = MagicMock()
    metadata_api.get_metadata_4_track.side_effect = [
        primary_metadata,
        alternative_metadata,
    ]
    session = SimpleNamespace(api=lambda: metadata_api)
    audio = SpotifyAudioInterface.__new__(SpotifyAudioInterface)
    audio.api = SimpleNamespace(
        librespot=SimpleNamespace(session=session),
        gid_to_media_id=lambda _gid: "alternative-id",
    )
    audio._get_stream_url = AsyncMock(return_value="https://audio.test/alternative")

    resolved = await audio._get_stream_info_librespot(
        "primary-id",
        "track",
        quality,
    )

    assert resolved.audio_track.file_id == b"alternative-file"
    assert resolved.audio_track.media_id == "alternative-id"
    assert metadata_api.get_metadata_4_track.call_count == 2


@pytest.mark.asyncio
async def test_audio_key_rejection_tries_librespot_alternative_before_web():
    primary = stream(file_id=b"primary")
    alternative = stream(file_id=b"alternative")
    alternative.audio_track.media_id = "alternative-id"
    key = DecryptionKey(decryption_key=b"alternative-key")
    audio = SpotifyAudioInterface.__new__(SpotifyAudioInterface)
    audio.api = SimpleNamespace(
        session_type=SessionType.LIBRESPOT,
        premium_session=True,
        librespot=object(),
    )
    audio.cdm = object()
    audio.audio_quality_priority = [AudioQuality.VORBIS_MEDIUM]
    audio.get_stream_info = AsyncMock(return_value=primary)
    audio.get_decryption_key = AsyncMock(
        side_effect=[
            DotifyLibrespotAudioKeyException("track-id", b"primary"),
            key,
        ]
    )
    audio._get_stream_info_librespot = AsyncMock(return_value=alternative)
    audio._get_stream_info_web = AsyncMock()

    resolved_stream, resolved_key = await audio.get_stream_info_with_decryption_key(
        "track-id",
        "track",
    )

    assert resolved_stream is alternative
    assert resolved_key is key
    audio._get_stream_info_web.assert_not_awaited()


@pytest.mark.asyncio
async def test_strict_audio_quality_disables_implicit_web_fallback():
    primary = stream(file_id=b"primary")
    audio = SpotifyAudioInterface.__new__(SpotifyAudioInterface)
    audio.api = SimpleNamespace(
        session_type=SessionType.LIBRESPOT,
        premium_session=True,
        librespot=object(),
    )
    audio.cdm = object()
    audio.strict_audio_quality = True
    audio.audio_quality_priority = [AudioQuality.VORBIS_HIGH]
    audio.get_stream_info = AsyncMock(return_value=primary)
    audio.get_decryption_key = AsyncMock(
        side_effect=DotifyLibrespotAudioKeyException("track-id", b"primary")
    )
    audio._get_stream_info_librespot = AsyncMock(return_value=None)
    audio._get_stream_info_web = AsyncMock()

    with pytest.raises(DotifyLibrespotAudioKeyException):
        await audio.get_stream_info_with_decryption_key("track-id", "track")

    audio._get_stream_info_web.assert_not_awaited()
