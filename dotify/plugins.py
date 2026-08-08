"""Extensible metadata, download and post-processing hooks for Dotify."""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from importlib.metadata import EntryPoint, entry_points
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from .downloader.types import DownloadItem
    from .interface.types import SpotifyMedia


METADATA_ENTRY_POINT = "dotify.metadata"
DOWNLOADER_ENTRY_POINT = "dotify.downloaders"
POST_PROCESSOR_ENTRY_POINT = "dotify.postprocessors"


@runtime_checkable
class MetadataProvider(Protocol):
    """Enrich or replace media metadata before a download is parsed."""

    async def enrich(self, media: "SpotifyMedia") -> "SpotifyMedia | None": ...


@runtime_checkable
class DownloaderPlugin(Protocol):
    """Optionally handle a download instead of Dotify's built-in downloader."""

    def supports(self, item: "DownloadItem") -> bool: ...
    async def download(self, item: "DownloadItem") -> None: ...


@runtime_checkable
class PostProcessor(Protocol):
    """Run after a download has completed successfully."""

    async def process(self, item: "DownloadItem") -> None: ...


class PluginLoadError(RuntimeError):
    def __init__(self, entry_point: EntryPoint, reason: Exception) -> None:
        super().__init__(f"Could not load plugin '{entry_point.name}': {reason}")
        self.entry_point = entry_point
        self.reason = reason


@dataclass(slots=True)
class PluginManager:
    """Plugin registry with manual registration and entry-point discovery."""

    metadata_providers: list[MetadataProvider] = field(default_factory=list)
    downloaders: list[DownloaderPlugin] = field(default_factory=list)
    post_processors: list[PostProcessor] = field(default_factory=list)
    load_errors: list[PluginLoadError] = field(default_factory=list)

    def register(self, plugin: Any) -> None:
        """Register one plugin, rejecting ambiguous or invalid implementations."""

        matches = []
        if isinstance(plugin, MetadataProvider):
            matches.append(self.metadata_providers)
        if isinstance(plugin, DownloaderPlugin):
            matches.append(self.downloaders)
        if isinstance(plugin, PostProcessor):
            matches.append(self.post_processors)

        if not matches:
            raise TypeError(
                "Plugin must implement MetadataProvider, DownloaderPlugin, "
                "or PostProcessor"
            )
        if len(matches) > 1:
            raise TypeError("A plugin must implement exactly one Dotify plugin protocol")
        matches[0].append(plugin)

    @classmethod
    def discover(cls, strict: bool = False) -> "PluginManager":
        """Load installed plugins from Dotify's three entry-point groups."""

        manager = cls()
        groups = (
            METADATA_ENTRY_POINT,
            DOWNLOADER_ENTRY_POINT,
            POST_PROCESSOR_ENTRY_POINT,
        )
        available = entry_points()
        for group in groups:
            selected = (
                available.select(group=group)
                if hasattr(available, "select")
                else available.get(group, ())
            )
            for entry_point in selected:
                try:
                    plugin = manager._materialize(entry_point.load())
                    manager.register(plugin)
                except Exception as exc:
                    error = PluginLoadError(entry_point, exc)
                    if strict:
                        raise error from exc
                    manager.load_errors.append(error)
        return manager

    @staticmethod
    def _materialize(loaded: Any) -> Any:
        if inspect.isclass(loaded):
            return loaded()
        return loaded

    async def enrich(self, media: "SpotifyMedia") -> "SpotifyMedia":
        for provider in self.metadata_providers:
            enriched = await provider.enrich(media)
            if enriched is not None:
                media = enriched
        return media

    def select_downloader(self, item: "DownloadItem") -> DownloaderPlugin | None:
        return next((plugin for plugin in self.downloaders if plugin.supports(item)), None)

    async def download(
        self,
        item: "DownloadItem",
        fallback: "Callable[[DownloadItem], Awaitable[None]]",
    ) -> None:
        plugin = self.select_downloader(item)
        if plugin is None:
            await fallback(item)
        else:
            await plugin.download(item)

    async def post_process(self, item: "DownloadItem") -> None:
        for processor in self.post_processors:
            await processor.process(item)
