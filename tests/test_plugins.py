from types import SimpleNamespace

import pytest

from dotify.plugins import PluginManager


@pytest.mark.asyncio
async def test_metadata_plugins_run_in_registration_order():
    events = []

    class First:
        async def enrich(self, media):
            events.append("first")
            media.title = "first"

    class Second:
        async def enrich(self, media):
            events.append("second")
            media.title += "+second"
            return media

    manager = PluginManager()
    manager.register(First())
    manager.register(Second())
    media = await manager.enrich(SimpleNamespace(title=""))

    assert events == ["first", "second"]
    assert media.title == "first+second"


@pytest.mark.asyncio
async def test_custom_downloader_precedes_fallback_and_runs_post_processor():
    events = []
    item = SimpleNamespace(kind="fixture")

    class CustomDownloader:
        def supports(self, candidate):
            return candidate.kind == "fixture"

        async def download(self, candidate):
            events.append("custom")

    class Processor:
        async def process(self, candidate):
            events.append("post")

    async def fallback(candidate):
        events.append("fallback")

    manager = PluginManager()
    manager.register(CustomDownloader())
    manager.register(Processor())
    await manager.download(item, fallback)
    await manager.post_process(item)

    assert events == ["custom", "post"]


def test_invalid_and_ambiguous_plugins_are_rejected():
    manager = PluginManager()
    with pytest.raises(TypeError, match="must implement"):
        manager.register(object())

    class Ambiguous:
        async def enrich(self, media):
            return media

        async def process(self, item):
            return None

    with pytest.raises(TypeError, match="exactly one"):
        manager.register(Ambiguous())


def test_entry_point_discovery_collects_non_strict_load_errors(monkeypatch):
    class Provider:
        async def enrich(self, media):
            return media

    class EntryPoint:
        def __init__(self, name, loaded=None, error=None):
            self.name = name
            self.loaded = loaded
            self.error = error

        def load(self):
            if self.error:
                raise self.error
            return self.loaded

    class EntryPoints(list):
        def select(self, *, group):
            return self if group == "dotify.metadata" else []

    discovered = EntryPoints(
        [
            EntryPoint("provider", loaded=Provider),
            EntryPoint("broken", error=RuntimeError("boom")),
        ]
    )
    monkeypatch.setattr("dotify.plugins.entry_points", lambda: discovered)

    manager = PluginManager.discover()

    assert len(manager.metadata_providers) == 1
    assert len(manager.load_errors) == 1
    assert "broken" in str(manager.load_errors[0])
