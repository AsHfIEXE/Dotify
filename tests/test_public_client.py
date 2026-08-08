from types import SimpleNamespace

import pytest

from dotify import (
    DotifyClient,
    DotifySettings,
    PUBLIC_API_VERSION,
    __api_version__,
    __version__,
)
from dotify.plugins import PluginManager


class FakeInterface:
    async def get_media(self, url, auto_media_option=None):
        yield SimpleNamespace(media_id="media", marker="raw", error=None)


class FakeDownloader:
    def __init__(self):
        self.downloaded = []

    async def get_download_item(self, url, auto_media_option=None):
        media = SimpleNamespace(media_id="media", marker="raw", error=None)
        yield SimpleNamespace(media=media, final_path="/tmp/media.ogg")

    def parse_media(self, media):
        return SimpleNamespace(media=media, final_path=f"/tmp/{media.marker}.ogg")

    async def download(self, item):
        self.downloaded.append(item)


class FakeApi:
    def __init__(self):
        self.closed = False

    async def aclose(self):
        self.closed = True


@pytest.mark.asyncio
async def test_public_client_downloads_without_cli_imports():
    api = FakeApi()
    downloader = FakeDownloader()
    client = DotifyClient(api, FakeInterface(), downloader, close_api=True)

    result = await client.download("spotify:track:test")
    await client.aclose()

    assert len(result.items) == 1
    assert result.paths[0].name == "raw.ogg"
    assert downloader.downloaded == list(result.items)
    assert api.closed


@pytest.mark.asyncio
async def test_metadata_enrichment_happens_before_download_item_parsing():
    class Enricher:
        async def enrich(self, media):
            media.marker = "enriched"
            return media

    plugins = PluginManager()
    plugins.register(Enricher())
    client = DotifyClient(
        FakeApi(), FakeInterface(), FakeDownloader(), plugins=plugins
    )

    result = await client.download("spotify:track:test")

    assert result.paths[0].name == "enriched.ogg"


def test_public_api_has_independent_version():
    assert isinstance(DotifySettings(), DotifySettings)
    assert PUBLIC_API_VERSION == (1, 2)
    assert __api_version__ == "1.2"
    assert __version__ == "3.0.4"
    assert DotifySettings().widevine_backoff == 60
    assert DotifySettings().strict_audio_quality is False
