"""Stable adapter boundary for Spotify's private and frequently changing APIs.

The rest of Dotify should depend on :class:`SpotifyApiPort`, not on the HTTP
implementation.  ``SpotifyApiAdapter`` keeps response-shape checks in one
place so upstream changes fail with a useful, operation-specific error.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Protocol, runtime_checkable

from .enums import SessionType


class SpotifyContractError(RuntimeError):
    """Raised when Spotify returns a response that no longer matches Dotify."""

    def __init__(self, operation: str, missing_path: str) -> None:
        super().__init__(
            f"Spotify API contract changed for '{operation}': "
            f"missing '{missing_path}'"
        )
        self.operation = operation
        self.missing_path = missing_path


# Only stable structural roots are asserted. Individual media parsers retain
# responsibility for fields specific to a format or feature.
RESPONSE_CONTRACTS: dict[str, tuple[str, ...]] = {
    "track": ("data.trackUnion",),
    "album": ("data.albumUnion",),
    "playlist": ("data.playlistV2",),
    "episode": ("data.episodeUnionV2",),
    "show": ("data.podcastUnionV2",),
    "artist_overview": ("data.artistUnion",),
    "artist_albums": ("data.artistUnion",),
    "artist_singles": ("data.artistUnion",),
    "artist_compilations": ("data.artistUnion",),
    "artist_videos": ("data.artistUnion",),
    "library_tracks": ("data.me.library.tracks",),
    "playback_info": ("media",),
}


def validate_response_contract(operation: str, response: Any) -> Any:
    """Validate and return an API response for fluent adapter delegation."""

    for dotted_path in RESPONSE_CONTRACTS.get(operation, ()):
        value = response
        for segment in dotted_path.split("."):
            if not isinstance(value, dict) or segment not in value:
                raise SpotifyContractError(operation, dotted_path)
            value = value[segment]
    return response


@runtime_checkable
class SpotifyApiPort(Protocol):
    """Structural API consumed by Dotify's interfaces."""

    session_type: SessionType
    librespot: Any

    @property
    def premium_session(self) -> bool: ...

    @property
    def anonymous_session(self) -> bool: ...

    async def get_track(self, track_id: str) -> dict: ...
    async def get_album(
        self, album_id: str, offset: int = 0, limit: int = 300
    ) -> dict: ...
    async def get_playlist(
        self, playlist_id: str, offset: int = 0, limit: int = 300
    ) -> dict: ...
    async def get_episode(self, episode_id: str) -> dict: ...
    async def get_show(
        self, show_id: str, offset: int = 0, limit: int = 300
    ) -> dict: ...
    async def get_artist_overview(self, artist_id: str) -> dict: ...
    async def get_artist_albums(
        self, artist_id: str, offset: int = 0, limit: int = 300
    ) -> dict: ...
    async def get_artist_singles(
        self, artist_id: str, offset: int = 0, limit: int = 300
    ) -> dict: ...
    async def get_artist_compilations(
        self, artist_id: str, offset: int = 0, limit: int = 300
    ) -> dict: ...
    async def get_artist_videos(
        self, artist_id: str, offset: int = 0, limit: int = 300
    ) -> dict: ...
    async def get_library_tracks(self, offset: int = 0, limit: int = 300) -> dict: ...
    async def get_video_manifest(self, file_id: str) -> dict: ...
    async def get_seek_table(self, file_id: str) -> dict: ...
    async def get_playback_info(
        self,
        media_id: str,
        media_type: str,
        file_formats: list[str] | None = None,
    ) -> dict: ...
    async def get_gid_metadata(self, media_id: str, media_type: str) -> dict: ...
    async def get_lyrics(self, track_id: str) -> dict: ...
    async def get_track_credits(self, track_id: str) -> dict: ...
    async def get_widevine_license(self, challenge: bytes, media_type: str) -> bytes: ...
    async def get_audio_stream_urls(self, format_id: str, file_id: str) -> dict: ...
    async def get_playplay_license(self, file_id: str, request: Any) -> Any: ...
    async def get_extended_metadata(self, request: Any) -> Any: ...
    async def aclose(self) -> None: ...

    @staticmethod
    def media_id_to_gid(media_id: str) -> str: ...

    @staticmethod
    def gid_to_media_id(gid: str) -> str: ...


class SpotifyApiAdapter:
    """Contract-validating facade around a concrete Spotify API client."""

    def __init__(self, client: Any, validate_contracts: bool = True) -> None:
        self.client = client
        self.validate_contracts = validate_contracts

    @property
    def session_type(self) -> SessionType:
        return self.client.session_type

    @property
    def librespot(self) -> Any:
        return getattr(self.client, "librespot", None)

    @property
    def premium_session(self) -> bool:
        return self.client.premium_session

    @property
    def anonymous_session(self) -> bool:
        return self.client.anonymous_session

    async def _json_call(
        self,
        operation: str,
        call: Callable[..., Awaitable[dict]],
        *args: Any,
        **kwargs: Any,
    ) -> dict:
        response = await call(*args, **kwargs)
        if self.validate_contracts:
            validate_response_contract(operation, response)
        return response

    async def get_track(self, track_id: str) -> dict:
        return await self._json_call("track", self.client.get_track, track_id)

    async def get_album(self, album_id: str, offset: int = 0, limit: int = 300) -> dict:
        return await self._json_call("album", self.client.get_album, album_id, offset, limit)

    async def get_playlist(self, playlist_id: str, offset: int = 0, limit: int = 300) -> dict:
        return await self._json_call("playlist", self.client.get_playlist, playlist_id, offset, limit)

    async def get_episode(self, episode_id: str) -> dict:
        return await self._json_call("episode", self.client.get_episode, episode_id)

    async def get_show(self, show_id: str, offset: int = 0, limit: int = 300) -> dict:
        return await self._json_call("show", self.client.get_show, show_id, offset, limit)

    async def get_artist_overview(self, artist_id: str) -> dict:
        return await self._json_call("artist_overview", self.client.get_artist_overview, artist_id)

    async def get_artist_albums(self, artist_id: str, offset: int = 0, limit: int = 300) -> dict:
        return await self._json_call("artist_albums", self.client.get_artist_albums, artist_id, offset, limit)

    async def get_artist_singles(self, artist_id: str, offset: int = 0, limit: int = 300) -> dict:
        return await self._json_call("artist_singles", self.client.get_artist_singles, artist_id, offset, limit)

    async def get_artist_compilations(self, artist_id: str, offset: int = 0, limit: int = 300) -> dict:
        return await self._json_call("artist_compilations", self.client.get_artist_compilations, artist_id, offset, limit)

    async def get_artist_videos(self, artist_id: str, offset: int = 0, limit: int = 300) -> dict:
        return await self._json_call("artist_videos", self.client.get_artist_videos, artist_id, offset, limit)

    async def get_library_tracks(self, offset: int = 0, limit: int = 300) -> dict:
        return await self._json_call("library_tracks", self.client.get_library_tracks, offset, limit)

    async def get_playback_info(
        self,
        media_id: str,
        media_type: str,
        file_formats: list[str] | None = None,
    ) -> dict:
        kwargs = {} if file_formats is None else {"file_formats": file_formats}
        return await self._json_call(
            "playback_info", self.client.get_playback_info, media_id, media_type, **kwargs
        )

    async def get_video_manifest(self, file_id: str) -> dict:
        return await self.client.get_video_manifest(file_id)

    async def get_seek_table(self, file_id: str) -> dict:
        return await self.client.get_seek_table(file_id)

    async def get_gid_metadata(self, media_id: str, media_type: str) -> dict:
        return await self.client.get_gid_metadata(media_id, media_type)

    async def get_lyrics(self, track_id: str) -> dict:
        return await self.client.get_lyrics(track_id)

    async def get_track_credits(self, track_id: str) -> dict:
        return await self.client.get_track_credits(track_id)

    async def get_widevine_license(self, challenge: bytes, media_type: str) -> bytes:
        return await self.client.get_widevine_license(challenge, media_type)

    async def get_audio_stream_urls(self, format_id: str, file_id: str) -> dict:
        return await self.client.get_audio_stream_urls(format_id, file_id)

    async def get_playplay_license(self, file_id: str, request: Any) -> Any:
        return await self.client.get_playplay_license(file_id, request)

    async def get_extended_metadata(self, request: Any) -> Any:
        return await self.client.get_extended_metadata(request)

    def media_id_to_gid(self, media_id: str) -> str:
        return self.client.media_id_to_gid(media_id)

    def gid_to_media_id(self, gid: str) -> str:
        return self.client.gid_to_media_id(gid)

    async def aclose(self) -> None:
        close = getattr(self.client, "aclose", None)
        if close is not None:
            await close()
            return
        http_client = getattr(self.client, "client", None)
        if http_client is not None and hasattr(http_client, "aclose"):
            await http_client.aclose()
