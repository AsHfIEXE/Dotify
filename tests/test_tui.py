import asyncio
from io import StringIO
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from rich.console import Console

from dotify.downloader.progress import DownloadProgress
from dotify.i18n import Translator
from dotify.tui import TerminalUI, format_duration


def make_item(
    path=None,
    title="Fixture Track",
    audio_description=None,
    fallback_audio_description=None,
):
    tags = SimpleNamespace(artist="Fixture Artist", title=title)
    media = SimpleNamespace(
        media_metadata={"name": title},
        tags=tags,
        error=None,
    )
    return SimpleNamespace(
        media=media,
        final_path=str(path) if path else None,
        audio_description=audio_description,
        fallback_audio_description=fallback_audio_description,
    )


def test_progress_event_normalizes_ytdlp_payload():
    event = DownloadProgress.from_ytdlp(
        {
            "status": "downloading",
            "downloaded_bytes": 50,
            "total_bytes_estimate": 100,
            "speed": 25.0,
            "eta": 2,
        }
    )
    assert event.downloaded_bytes == 50
    assert event.total_bytes == 100
    assert event.speed == 25.0
    assert event.eta == 2


@pytest.mark.asyncio
async def test_tui_tracks_progress_and_prints_turkish_summary(tmp_path):
    output = tmp_path / "track.m4a"
    output.write_bytes(b"audio")
    item = make_item(
        output,
        audio_description="AAC 256 kbps / M4A",
        fallback_audio_description="Vorbis 320 kbps / OGG",
    )
    stream = StringIO()
    console = Console(file=stream, force_terminal=False, width=100)
    ui = TerminalUI(Translator("tr"), console=console, interactive=False)

    ui.show_queue([item])
    ui.start([item])
    ui.start_item(item)
    ui.on_progress(
        {"status": "downloading", "downloaded_bytes": 5, "total_bytes": 5}
    )
    await asyncio.sleep(0)
    ui.finish_item(item, "success")
    summary = ui.close()

    assert summary.success == 1
    assert summary.transferred_bytes == 5
    assert summary.formats == {"AAC 256 kbps / M4A": 1}
    assert summary.fallbacks
    output_text = stream.getvalue()
    assert "İndirme özeti" in output_text
    assert "Gerçek biçimler" in output_text
    assert "AAC 256 kbps / M4A" in output_text
    assert "Kalite fallback'leri" in output_text
    assert output.name in output_text


@pytest.mark.asyncio
async def test_interactive_selection_returns_selected_items(monkeypatch):
    first = make_item(title="First")
    second = make_item(title="Second")
    captured = {}

    class Prompt:
        async def execute_async(self):
            return [1]

    def checkbox(**kwargs):
        captured.update(kwargs)
        return Prompt()

    monkeypatch.setattr("dotify.tui.inquirer.checkbox", checkbox)
    ui = TerminalUI(
        Translator("en"),
        console=Console(file=StringIO(), force_terminal=False),
        interactive=True,
    )

    assert await ui.select_items([first, second]) == [second]
    assert [choice.value for choice in captured["choices"]] == [0, 1]


@pytest.mark.asyncio
async def test_playlist_mode_offers_download_all_first(monkeypatch):
    captured = {}

    class Prompt:
        async def execute_async(self):
            return "all"

    def select(**kwargs):
        captured.update(kwargs)
        return Prompt()

    monkeypatch.setattr("dotify.tui.inquirer.select", select)
    ui = TerminalUI(
        Translator("tr"),
        console=Console(file=StringIO(), force_terminal=False),
        interactive=True,
    )

    assert await ui.select_playlist_mode() == "all"
    assert [choice.value for choice in captured["choices"]] == ["all", "select"]
    assert captured["choices"][0].name == "Tüm parçaları indir"


@pytest.mark.asyncio
async def test_tui_shows_widevine_429_countdown(monkeypatch):
    item = make_item(title="Rate Limited Track")
    ui = TerminalUI(
        Translator("tr"),
        console=Console(file=StringIO(), force_terminal=False),
        interactive=False,
    )
    ui.add_item(item, 1)
    ui.start_item(item)
    descriptions = []
    original_update = ui.progress.update

    def capture_update(task_id, **kwargs):
        if "description" in kwargs:
            descriptions.append(kwargs["description"])
        return original_update(task_id, **kwargs)

    monkeypatch.setattr(ui.progress, "update", capture_update)
    sleep = AsyncMock()
    monkeypatch.setattr("dotify.tui.asyncio.sleep", sleep)

    await ui.wait_for_widevine_retry(2.5, 1, 2)

    assert any("Spotify bekleniyor (429)" in value for value in descriptions)
    assert any("3 sn sonra" in value for value in descriptions)
    assert descriptions[-1].startswith("[cyan]İndiriliyor[/cyan]")
    assert [call.args[0] for call in sleep.await_args_list] == [1.0, 1.0, 0.5]


def test_duration_formatting():
    assert format_duration(65) == "01:05"
    assert format_duration(3661) == "1:01:01"
