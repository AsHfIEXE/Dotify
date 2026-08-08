from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from dotify.downloader.downloader import SpotifyDownloader
from dotify.downloader.exceptions import DotifyMediaFileExists
from dotify.downloader.types import DownloadItem
from dotify.interface.base import SpotifyBaseInterface
from dotify.interface.enums import MediaType
from dotify.interface.song import SpotifySongInterface
from dotify.interface.types import DecryptionKey, MediaTags, SpotifyMedia, StreamInfo, StreamInfoAv


@pytest.mark.asyncio
async def test_existing_output_skips_before_deferred_stream_loader(tmp_path):
    output = tmp_path / "existing.ogg"
    output.write_bytes(b"audio")
    media = SpotifyMedia(
        "track-id",
        {"name": "Track"},
        tags=MediaTags(media_type=MediaType.SONG),
    )
    loader = AsyncMock()
    media.stream_loader = loader
    item = DownloadItem(
        media=media,
        final_path=str(output),
        candidate_final_paths=(str(output),),
    )
    downloader = SpotifyDownloader.__new__(SpotifyDownloader)
    downloader.overwrite = False

    with pytest.raises(DotifyMediaFileExists):
        await downloader.prepare(item)

    loader.assert_not_awaited()


@pytest.mark.asyncio
async def test_song_metadata_is_ready_before_stream_is_resolved():
    song = SpotifySongInterface.__new__(SpotifySongInterface)
    song.skip_stream_info = False
    song.defer_stream_info = True
    song.get_lyrics = AsyncMock(return_value=None)
    song.parse_tags = AsyncMock(
        return_value=MediaTags(media_type=MediaType.SONG, title="Fixture")
    )
    stream = StreamInfoAv(
        audio_track=StreamInfo(
            stream_url="https://audio.test",
            widevine_pssh=None,
            file_format="ogg",
            actual_file_format="ogg",
        )
    )
    key = DecryptionKey(decryption_key=b"key")
    song.get_stream_info_with_decryption_key = AsyncMock(return_value=(stream, key))
    track_data = {
        "uri": "spotify:track:track-id",
        "albumOfTrack": {"coverArt": {"sources": []}},
    }

    media = await song.proccess_media(
        track_data=track_data,
        album_data=track_data["albumOfTrack"],
        album_items=[],
    )

    assert media.tags.title == "Fixture"
    assert media.stream_info is None
    song.get_stream_info_with_decryption_key.assert_not_awaited()

    await media.ensure_stream()

    assert media.stream_info is stream
    assert media.decryption_key is key
    song.get_stream_info_with_decryption_key.assert_awaited_once()


@pytest.mark.asyncio
async def test_cdm_open_error_is_not_masked_by_close():
    class BrokenCdm:
        def open(self):
            raise RuntimeError("original CDM open failure")

        def close(self, _session):
            raise AssertionError("close must not run without a session")

    interface = SpotifyBaseInterface.__new__(SpotifyBaseInterface)
    interface.cdm = BrokenCdm()
    interface.api = SimpleNamespace()

    with pytest.raises(RuntimeError, match="original CDM open failure"):
        await interface._get_widevine_decryption_key("pssh", "audio")


def test_download_item_reports_actual_and_fallback_audio_quality():
    media = SpotifyMedia(
        "track-id",
        {"name": "Track"},
        stream_info=StreamInfoAv(
            audio_track=StreamInfo(
                stream_url="https://audio.test",
                widevine_pssh=None,
                file_format="mp4",
                actual_file_format="m4a",
                audio_quality="aac-high",
                source_session="web",
                fallback_from="vorbis-high,vorbis-medium",
                fallback_reason="librespot-audio-key",
            )
        ),
    )
    item = DownloadItem(media=media, final_path="/tmp/track.m4a")

    assert item.audio_description == "AAC 256 kbps / M4A"
    assert item.fallback_audio_description == (
        "Vorbis 320 kbps / OGG, Vorbis 160 kbps / OGG"
    )
