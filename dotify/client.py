"""CLI-independent public Python API for Dotify."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

from .plugins import PluginManager
from .queue import PersistentDownloadQueue

if TYPE_CHECKING:
    from .api.adapter import SpotifyApiPort
    from .downloader.types import DownloadItem
    from .interface.types import SpotifyMedia


class MediaInterfacePort(Protocol):
    def get_media(
        self,
        url: str | None = None,
        auto_media_option: Any = None,
    ) -> AsyncIterator[Any]: ...


class DownloaderPort(Protocol):
    def get_download_item(
        self,
        url: str | None = None,
        auto_media_option: Any = None,
    ) -> AsyncIterator[Any]: ...
    async def download(self, item: Any) -> None: ...


@dataclass(frozen=True, slots=True)
class DotifySettings:
    """Stable, high-level settings used by :meth:`DotifyClient.from_cookies`."""

    output_path: str = "./Spotify"
    temp_path: str = "."
    session_type: str = "librespot"
    audio_quality: tuple[str, ...] = ("vorbis-medium",)
    strict_audio_quality: bool = False
    cover_size: str = "extra-large"
    video_format: str = "mp4"
    video_resolution: str = "1080p"
    audio_download_mode: str = "ytdlp"
    audio_remux_mode: str = "ffmpeg"
    video_remux_mode: str = "ffmpeg"
    wvd_path: str | None = None
    librespot_credentials_path: str | None = None
    widevine_retries: int = 2
    widevine_backoff: int = 60
    widevine_max_wait: int = 120
    widevine_request_interval: float = 0
    spotify_dll_path: str | None = None
    prefer_video: bool = False
    overwrite: bool = False
    synced_lyrics_only: bool = False
    save_playlist_file: bool = False
    save_cover_file: bool = False
    no_synced_lyrics_file: bool = False
    queue_state_path: str | None = None
    resume: bool = True


@dataclass(frozen=True, slots=True)
class DownloadResult:
    """Result of one high-level URL download operation."""

    url: str
    items: tuple[Any, ...] = field(default_factory=tuple)

    @property
    def paths(self) -> tuple[Path, ...]:
        return tuple(
            Path(item.final_path)
            for item in self.items
            if getattr(item, "final_path", None)
        )


class DotifyClient:
    """Reusable async facade over Dotify's media and downloader pipelines.

    Applications can inject fake or custom components directly, while regular
    users can create a fully configured client with :meth:`from_cookies`.
    """

    def __init__(
        self,
        api: "SpotifyApiPort",
        interface: MediaInterfacePort,
        downloader: DownloaderPort,
        plugins: PluginManager | None = None,
        *,
        close_api: bool = False,
        queue: PersistentDownloadQueue | None = None,
        resume: bool = True,
    ) -> None:
        self.api = api
        self.interface = interface
        self.downloader = downloader
        self.plugins = plugins or PluginManager()
        self.close_api = close_api
        self.queue = queue
        self.resume = resume
        self._closed = False

    @classmethod
    async def from_cookies(
        cls,
        cookies_path: str,
        settings: DotifySettings | None = None,
        plugins: PluginManager | None = None,
        *,
        discover_plugins: bool = True,
        validate_contracts: bool = True,
    ) -> "DotifyClient":
        """Build the default Dotify pipeline without importing the CLI."""

        from .api.adapter import SpotifyApiAdapter
        from .api.api import SpotifyApi
        from .api.enums import SessionType
        from .downloader.audio import SpotifyAudioDownloader
        from .downloader.base import SpotifyBaseDownloader
        from .downloader.downloader import SpotifyDownloader
        from .downloader.enums import AudioDownloadMode, AudioRemuxMode, VideoRemuxMode
        from .downloader.video import SpotifyVideoDownloader
        from .interface.audio import SpotifyAudioInterface
        from .interface.base import SpotifyBaseInterface
        from .interface.enums import AudioQuality, CoverSize, VideoFormat, VideoResolution
        from .interface.episode import SpotifyEpisodeInterface
        from .interface.episode_video import SpotifyEpisodeVideoInterface
        from .interface.interface import SpotifyInterface
        from .interface.music_video import SpotifyMusicVideoInterface
        from .interface.song import SpotifySongInterface
        from .interface.video import SpotifyVideoInterface

        options = settings or DotifySettings()
        raw_api = await SpotifyApi.create_from_netscape_cookies(
            cookies_path,
            session_type=SessionType(options.session_type),
            librespot_credentials_path=options.librespot_credentials_path,
            widevine_retries=options.widevine_retries,
            widevine_backoff=options.widevine_backoff,
            widevine_max_wait=options.widevine_max_wait,
            widevine_request_interval=options.widevine_request_interval,
        )
        api = SpotifyApiAdapter(raw_api, validate_contracts=validate_contracts)

        base_interface = SpotifyBaseInterface(
            api=api,
            cover_size=CoverSize(options.cover_size),
            skip_stream_info=options.synced_lyrics_only,
            defer_stream_info=True,
            wvd_path=options.wvd_path,
            spotify_dll_path=options.spotify_dll_path,
        )
        video_interface = SpotifyVideoInterface(
            base=base_interface,
            video_format=VideoFormat(options.video_format),
            resolution=VideoResolution(options.video_resolution),
        )
        audio_interface = SpotifyAudioInterface(
            base=base_interface,
            audio_quality_priority=[AudioQuality(value) for value in options.audio_quality],
            strict_audio_quality=options.strict_audio_quality,
        )
        interface = SpotifyInterface(
            base=audio_interface,
            song=SpotifySongInterface(audio_interface),
            episode=SpotifyEpisodeInterface(audio_interface),
            music_video=SpotifyMusicVideoInterface(video_interface),
            episode_video=SpotifyEpisodeVideoInterface(video_interface),
            prefer_video=options.prefer_video,
        )
        base_downloader = SpotifyBaseDownloader(
            interface=interface,
            output_path=options.output_path,
            temp_path=options.temp_path,
        )
        downloader = SpotifyDownloader(
            base=base_downloader,
            audio=SpotifyAudioDownloader(
                base=base_downloader,
                download_mode=AudioDownloadMode(options.audio_download_mode),
                remux_mode=AudioRemuxMode(options.audio_remux_mode),
            ),
            video=SpotifyVideoDownloader(
                base=base_downloader,
                remux_mode=VideoRemuxMode(options.video_remux_mode),
            ),
            no_synced_lyrics_file=options.no_synced_lyrics_file,
            save_playlist_file=options.save_playlist_file,
            save_cover_file=options.save_cover_file,
            overwrite=options.overwrite,
            synced_lyrics_only=options.synced_lyrics_only,
        )

        plugin_manager = plugins
        if plugin_manager is None:
            plugin_manager = PluginManager.discover() if discover_plugins else PluginManager()

        return cls(
            api=api,
            interface=interface,
            downloader=downloader,
            plugins=plugin_manager,
            close_api=True,
            queue=(
                PersistentDownloadQueue(options.queue_state_path, options.output_path)
                if options.queue_state_path
                else None
            ),
            resume=options.resume,
        )

    async def iter_media(
        self,
        url: str,
        auto_media_option: Any = None,
    ) -> AsyncIterator["SpotifyMedia"]:
        self._ensure_open()
        async for media in self.interface.get_media(url, auto_media_option):
            yield await self.plugins.enrich(media)

    async def iter_items(
        self,
        url: str,
        auto_media_option: Any = None,
    ) -> AsyncIterator["DownloadItem"]:
        self._ensure_open()
        parser = getattr(self.downloader, "parse_media", None)
        if parser is not None:
            async for media in self.interface.get_media(url, auto_media_option):
                media = await self.plugins.enrich(media)
                item = parser(media)
                if item is not None:
                    item.source_url = url
                    yield item
            return

        # Compatibility path for injected downloader implementations that
        # expose only the original get_download_item() protocol.
        async for item in self.downloader.get_download_item(url, auto_media_option):
            item.media = await self.plugins.enrich(item.media)
            item.source_url = url
            yield item

    async def download_item(self, item: "DownloadItem") -> "DownloadItem":
        self._ensure_open()
        if item.media.error:
            raise item.media.error
        if self.queue and self.resume:
            completed_path = self.queue.completed_path(item)
            if completed_path:
                from .downloader.exceptions import DotifyQueueItemCompleted

                item.final_path = completed_path
                raise DotifyQueueItemCompleted(completed_path)
        if self.queue:
            self.queue.mark(item, "running")
        try:
            prepare = getattr(self.downloader, "prepare", None)
            if prepare is not None:
                await prepare(item)
            else:
                ensure_stream = getattr(item.media, "ensure_stream", None)
                if ensure_stream is not None:
                    await ensure_stream()
            await self.plugins.download(item, self.downloader.download)
            await self.plugins.post_process(item)
        except Exception as error:
            if self.queue:
                from .downloader.exceptions import DotifyMediaFileExists

                status = "skipped" if isinstance(error, DotifyMediaFileExists) else "failed"
                self.queue.mark(item, status, str(error))
            raise
        if self.queue:
            self.queue.mark(item, "success")
        return item

    async def download(
        self,
        url: str,
        auto_media_option: Any = None,
    ) -> DownloadResult:
        items = []
        async for item in self.iter_items(url, auto_media_option):
            items.append(await self.download_item(item))
        return DownloadResult(url=url, items=tuple(items))

    async def download_many(
        self,
        urls: Sequence[str],
        auto_media_option: Any = None,
    ) -> tuple[DownloadResult, ...]:
        return tuple([await self.download(url, auto_media_option) for url in urls])

    async def aclose(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self.close_api:
            close = getattr(self.api, "aclose", None)
            if close is not None:
                await close()

    async def __aenter__(self) -> "DotifyClient":
        self._ensure_open()
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.aclose()

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("DotifyClient is closed")
