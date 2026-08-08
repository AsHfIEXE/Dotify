import configparser
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
from click.testing import CliRunner

from dotify.api.api import SpotifyApi
from dotify.api.enums import SessionType
from dotify.api.exceptions import (
    DotifyAuthenticationException,
    DotifyLibrespotConnectionException,
    DotifyRequestException,
)
from dotify.cli.cli import cli
from dotify.downloader.exceptions import (
    DotifyDependencyNotFound,
    DotifyMediaFileExists,
)
from dotify.env.paths import DotifyPaths
from dotify.env.errors import DotifyErrorHandler
from dotify.env.setup import DotifySetup
from dotify.client import DotifyClient
from dotify.tui import TerminalUI


SPOTIFY_URL = "https://open.spotify.com/track/18gqCQzqYb0zvurQPlRkpo"
SPOTIFY_PLAYLIST_URL = "https://open.spotify.com/playlist/43d8h63sKulXq8awGHbCna"


class FakeRawApi:
    def __init__(self) -> None:
        self.session_type = SessionType.WEB
        self.librespot = None
        self.anonymous_session = False
        self.premium_session = False
        self.closed = False

    async def aclose(self) -> None:
        self.closed = True


def invoke_download(tmp_path, *args: str):
    return CliRunner().invoke(
        cli,
        [
            "download",
            "--no-config-file",
            "--config-path",
            str(tmp_path / "config.ini"),
            "--queue-state-path",
            str(tmp_path / "queue.json"),
            "--skip-preflight",
            "--wait-interval",
            "0",
            *args,
        ],
    )


def test_config_file_serializes_float_range_defaults(tmp_path, monkeypatch):
    config_path = tmp_path / "config.ini"
    captured = []

    async def capture_config(config):
        captured.append(config)

    monkeypatch.setattr("dotify.cli.cli._execute_download", capture_config)

    result = CliRunner().invoke(
        cli,
        [
            "download",
            "--config-path",
            str(config_path),
            "--queue-state-path",
            str(tmp_path / "queue.json"),
            SPOTIFY_URL,
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured[0].widevine_request_interval == 0
    config = configparser.ConfigParser()
    config.read(config_path, encoding="utf-8")
    assert config["dotify"]["widevine_request_interval"] == "0"


def install_fake_api(monkeypatch) -> FakeRawApi:
    raw_api = FakeRawApi()
    monkeypatch.setattr(
        SpotifyApi,
        "create_from_netscape_cookies",
        AsyncMock(return_value=raw_api),
    )
    return raw_api


def make_item() -> SimpleNamespace:
    return SimpleNamespace(
        media=SimpleNamespace(
            media_metadata={
                "name": "Fixture Track",
                "uri": "spotify:track:fixture",
            },
            error=None,
        ),
        staged_path=None,
        final_path=None,
    )


def test_preflight_failure_has_nonzero_exit_and_visible_message(tmp_path, monkeypatch):
    monkeypatch.setattr("dotify.cli.cli._run_preflight_checks", lambda *_: False)
    result = CliRunner().invoke(
        cli,
        [
            "download",
            "--no-config-file",
            "--config-path",
            str(tmp_path / "config.ini"),
            "--queue-state-path",
            str(tmp_path / "queue.json"),
            SPOTIFY_URL,
        ],
    )

    assert result.exit_code == 1
    assert "Preflight checks failed" in result.output


def test_missing_url_is_reported_before_preflight(tmp_path):
    result = CliRunner().invoke(
        cli,
        [
            "download",
            "--no-config-file",
            "--config-path",
            str(tmp_path / "config.ini"),
            "--queue-state-path",
            str(tmp_path / "queue.json"),
        ],
    )

    assert result.exit_code == 2
    assert "Missing argument" in result.output
    assert "URLS" in result.output


def test_authentication_failure_has_nonzero_exit_and_does_not_prompt(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        SpotifyApi,
        "create_from_netscape_cookies",
        AsyncMock(side_effect=DotifyAuthenticationException("cookies rejected")),
    )

    result = invoke_download(tmp_path, SPOTIFY_URL)

    assert result.exit_code == 1
    assert "Authentication error" in result.output
    assert "Cookies file not found or invalid" in result.output
    assert "does not exist" not in result.output


def test_initialization_timeout_is_not_reported_as_authentication_failure(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        SpotifyApi,
        "create_from_netscape_cookies",
        AsyncMock(side_effect=httpx.ReadTimeout("")),
    )

    result = invoke_download(tmp_path, SPOTIFY_URL)

    assert result.exit_code == 1
    assert "Network error" in result.output
    assert "initialization timed out" in result.output
    assert "Authentication error" not in result.output
    assert "Download error:" not in result.output


def test_empty_unexpected_initialization_error_keeps_exception_type(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        SpotifyApi,
        "create_from_netscape_cookies",
        AsyncMock(side_effect=RuntimeError()),
    )

    result = invoke_download(tmp_path, SPOTIFY_URL)

    assert result.exit_code == 1
    assert "Initialization error" in result.output
    assert "Download error: RuntimeError" in result.output


def test_librespot_connection_failure_is_not_reported_as_authentication(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        SpotifyApi,
        "create_from_netscape_cookies",
        AsyncMock(
            side_effect=DotifyLibrespotConnectionException(
                "Librespot access point refused the connection"
            )
        ),
    )

    result = invoke_download(tmp_path, SPOTIFY_URL)

    assert result.exit_code == 1
    assert "Network error" in result.output
    assert "credentials were not rejected" in result.output
    assert "Authentication error" not in result.output
    assert "dotify auth librespot" not in result.output


def test_missing_cookie_file_fails_without_interactive_prompt(tmp_path):
    result = invoke_download(
        tmp_path,
        "--cookies-path",
        str(tmp_path / "missing.txt"),
        SPOTIFY_URL,
    )

    assert result.exit_code == 1
    assert "Cookies file not found or invalid" in result.output
    assert "press enter to continue" not in result.output


def test_exceptions_flag_preserves_traceback_exception(tmp_path, monkeypatch):
    monkeypatch.setattr(
        SpotifyApi,
        "create_from_netscape_cookies",
        AsyncMock(side_effect=RuntimeError("debug failure")),
    )

    result = invoke_download(tmp_path, "--exceptions", SPOTIFY_URL)

    assert result.exit_code == 1
    assert isinstance(result.exception, RuntimeError)
    assert str(result.exception) == "debug failure"


def test_invalid_spotify_url_is_an_error_and_closes_api(tmp_path, monkeypatch):
    raw_api = install_fake_api(monkeypatch)

    result = invoke_download(tmp_path, "not-a-spotify-url")

    assert result.exit_code == 1
    assert "Failed to parse Spotify URL" in result.output
    assert raw_api.closed


def test_missing_dependency_is_failed_instead_of_skipped(tmp_path, monkeypatch):
    raw_api = install_fake_api(monkeypatch)
    item = make_item()

    async def iter_items(self, *_args, **_kwargs):
        yield item

    async def fail_download(self, _item):
        raise DotifyDependencyNotFound("aria2c")

    monkeypatch.setattr(DotifyClient, "iter_items", iter_items)
    monkeypatch.setattr(DotifyClient, "download_item", fail_download)
    sleep = AsyncMock()
    monkeypatch.setattr("dotify.cli.cli.asyncio.sleep", sleep)

    result = invoke_download(tmp_path, "--wait-interval", "10", SPOTIFY_URL)

    assert result.exit_code == 1
    assert "aria2c not found in PATH" in result.output
    assert "Skipping" not in result.output
    assert raw_api.closed
    sleep.assert_not_awaited()


def test_existing_file_remains_a_successful_skip(tmp_path, monkeypatch):
    raw_api = install_fake_api(monkeypatch)
    item = make_item()

    async def iter_items(self, *_args, **_kwargs):
        yield item

    async def skip_download(self, _item):
        raise DotifyMediaFileExists("/tmp/existing.ogg")

    monkeypatch.setattr(DotifyClient, "iter_items", iter_items)
    monkeypatch.setattr(DotifyClient, "download_item", skip_download)

    result = invoke_download(tmp_path, SPOTIFY_URL)

    assert result.exit_code == 0
    assert "Skipping" in result.output
    assert "Media file already exists" in result.output
    assert raw_api.closed


def test_unexpected_tui_error_closes_tui_and_api(tmp_path, monkeypatch):
    raw_api = install_fake_api(monkeypatch)
    item = make_item()
    state = {"tui_closed": False}

    async def iter_items(self, *_args, **_kwargs):
        yield item
        yield item

    async def fail_selection(self, _items):
        raise RuntimeError("selection failed")

    def close_tui(self):
        state["tui_closed"] = True

    monkeypatch.setattr(DotifyClient, "iter_items", iter_items)
    monkeypatch.setattr(TerminalUI, "select_items", fail_selection)
    monkeypatch.setattr(TerminalUI, "close", close_tui)

    result = invoke_download(tmp_path, "--tui", SPOTIFY_URL)

    assert result.exit_code == 1
    assert "Unexpected error: selection failed" in result.output
    assert state["tui_closed"]
    assert raw_api.closed


def test_tui_resolves_stream_only_for_selected_item(tmp_path, monkeypatch):
    install_fake_api(monkeypatch)
    first = make_item()
    second = make_item()
    first.media.ensure_stream = AsyncMock()
    second.media.ensure_stream = AsyncMock()

    async def iter_items(self, *_args, **_kwargs):
        yield first
        yield second

    async def select_second(self, _items):
        return [second]

    async def prepare_only(self, item):
        await item.media.ensure_stream()

    monkeypatch.setattr(DotifyClient, "iter_items", iter_items)
    monkeypatch.setattr(DotifyClient, "download_item", prepare_only)
    monkeypatch.setattr(TerminalUI, "select_items", select_second)

    result = invoke_download(tmp_path, "--tui", SPOTIFY_URL)

    assert result.exit_code == 0
    first.media.ensure_stream.assert_not_awaited()
    second.media.ensure_stream.assert_awaited_once()


def test_tui_download_all_streams_playlist_without_precollecting(tmp_path, monkeypatch):
    raw_api = install_fake_api(monkeypatch)
    first = make_item()
    second = make_item()
    events = []

    async def iter_items(self, *_args, **_kwargs):
        events.append("yield:first")
        yield first
        events.append("yield:second")
        yield second

    async def download_item(self, item):
        events.append("download:first" if item is first else "download:second")

    async def select_all(self):
        return "all"

    async def selection_must_not_open(self, _items):
        raise AssertionError("track selection should not open in download-all mode")

    monkeypatch.setattr(DotifyClient, "iter_items", iter_items)
    monkeypatch.setattr(DotifyClient, "download_item", download_item)
    monkeypatch.setattr(TerminalUI, "select_playlist_mode", select_all)
    monkeypatch.setattr(TerminalUI, "select_items", selection_must_not_open)

    result = invoke_download(tmp_path, "--tui", SPOTIFY_PLAYLIST_URL)

    assert result.exit_code == 0, result.output
    assert events == [
        "yield:first",
        "download:first",
        "yield:second",
        "download:second",
    ]
    assert callable(raw_api.widevine_wait_callback)


def test_wait_interval_runs_before_next_tui_item_resolution(tmp_path, monkeypatch):
    install_fake_api(monkeypatch)
    first = make_item()
    second = make_item()
    events = []

    async def iter_items(self, *_args, **_kwargs):
        yield first
        yield second

    async def select_all(self, items):
        return items

    async def resolve_item(self, item):
        events.append(f"resolve:{id(item)}")

    async def record_sleep(seconds):
        events.append(f"sleep:{seconds}")

    monkeypatch.setattr(DotifyClient, "iter_items", iter_items)
    monkeypatch.setattr(DotifyClient, "download_item", resolve_item)
    monkeypatch.setattr(TerminalUI, "select_items", select_all)
    monkeypatch.setattr("dotify.cli.cli.asyncio.sleep", record_sleep)

    result = invoke_download(tmp_path, "--tui", "--wait-interval", "3", SPOTIFY_URL)

    assert result.exit_code == 0
    assert events == [f"resolve:{id(first)}", "sleep:3", f"resolve:{id(second)}"]


def test_retry_and_pacing_cli_options_reach_api(tmp_path, monkeypatch):
    raw_api = FakeRawApi()
    create = AsyncMock(return_value=raw_api)
    strict_values = []
    monkeypatch.setattr(SpotifyApi, "create_from_netscape_cookies", create)

    async def no_items(self, *_args, **_kwargs):
        strict_values.append(self.interface.song.strict_audio_quality)
        if False:
            yield None

    monkeypatch.setattr(DotifyClient, "iter_items", no_items)

    result = invoke_download(
        tmp_path,
        "--widevine-retries",
        "4",
        "--widevine-backoff",
        "7",
        "--widevine-max-wait",
        "90",
        "--widevine-request-interval",
        "2.5",
        "--strict-audio-quality",
        SPOTIFY_URL,
    )

    assert result.exit_code == 0
    kwargs = create.await_args.kwargs
    assert kwargs["widevine_retries"] == 4
    assert kwargs["widevine_backoff"] == 7
    assert kwargs["widevine_max_wait"] == 90
    assert kwargs["widevine_request_interval"] == 2.5
    assert strict_values == [True]


def test_download_can_refresh_cookie_from_browser_before_api_start(tmp_path, monkeypatch):
    install_fake_api(monkeypatch)
    cookies_path = tmp_path / "cookies.txt"
    imported = []

    def import_cookie(browser, output, profile):
        imported.append((browser, output, profile))
        cookies_path.write_text("fixture", encoding="utf-8")
        return "chrome"

    async def no_items(self, *_args, **_kwargs):
        if False:
            yield None

    monkeypatch.setattr("dotify.cli.cli.import_spotify_cookie_from_browser", import_cookie)
    monkeypatch.setattr(DotifyClient, "iter_items", no_items)

    result = invoke_download(
        tmp_path,
        "--cookies-path",
        str(cookies_path),
        "--cookies-from-browser",
        "chrome",
        "--browser-profile",
        "Profile 2",
        SPOTIFY_URL,
    )

    assert result.exit_code == 0
    assert imported == [("chrome", str(cookies_path), "Profile 2")]


def test_turkish_rate_limit_error_has_code_and_localized_message(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        SpotifyApi,
        "create_from_netscape_cookies",
        AsyncMock(side_effect=DotifyRequestException("Widevine", 429, "")),
    )

    result = invoke_download(tmp_path, "--language", "tr", SPOTIFY_URL)

    assert result.exit_code == 1
    assert "[RATE_LIMITED]" in result.output
    assert "hız sınırına takıldı" in result.output


def test_environment_setup_writes_current_config_keys(tmp_path):
    paths = DotifyPaths(custom_config_dir=tmp_path / ".dotify")

    assert DotifySetup(paths)._setup_config_file()

    config = configparser.ConfigParser()
    config.read(paths.config_file, encoding="utf-8")
    settings = config["dotify"]
    assert settings["output"] == "./Spotify"
    assert settings["temp"] == str(paths.temp_dir)
    assert settings["widevine_retries"] == "2"
    assert settings["queue_state_path"] == str(paths.config_dir / "queue.json")
    assert settings.getboolean("resume") is True
    assert "output_path" not in settings
    assert "temp_path" not in settings


def test_widevine_api_error_is_not_misreported_as_missing_file():
    error = DotifyRequestException("Widevine license", 403, "forbidden")

    message = DotifyErrorHandler().handle_download_error(error)

    assert "status code 403" in message
    assert "Widevine key file not found" not in message


def test_turkish_existing_file_error_has_stable_code():
    error = DotifyMediaFileExists("/tmp/track.ogg")

    message = DotifyErrorHandler(language="tr").handle_download_error(error)

    assert message == "[MEDIA_EXISTS] Medya dosyası zaten mevcut: /tmp/track.ogg"


def test_web_session_without_wvd_fails_preflight(tmp_path):
    cookies_path = tmp_path / "cookies.txt"
    cookies_path.write_text("fixture", encoding="utf-8")
    missing_wvd = tmp_path / "missing.wvd"

    result = CliRunner().invoke(
        cli,
        [
            "download",
            "--no-config-file",
            "--config-path",
            str(tmp_path / "config.ini"),
            "--queue-state-path",
            str(tmp_path / "queue.json"),
            "--session-type",
            "web",
            "--cookies-path",
            str(cookies_path),
            "--wvd-path",
            str(missing_wvd),
            SPOTIFY_URL,
        ],
    )

    assert result.exit_code == 1
    assert "web session requires WVD" in result.output
