from pathlib import Path

import pytest
from click.testing import CliRunner

from dotify.api.api import SpotifyApi
from dotify.api.enums import SessionType
from dotify.api.exceptions import (
    DotifyLibrespotAuthenticationException,
    DotifyLibrespotConnectionException,
)
from dotify.api.librespot import Librespot
from dotify.cli.cli import cli
from dotify.cli import auth_commands


def premium_profile() -> dict:
    return {
        "data": {
            "me": {
                "account": {
                    "product": "PREMIUM",
                }
            }
        }
    }


def test_missing_librespot_credentials_does_not_fall_back_to_web(tmp_path):
    api = SpotifyApi(
        session_type=SessionType.LIBRESPOT,
        librespot_credentials_path=str(tmp_path / "missing.json"),
    )
    api.user_profile = premium_profile()

    with pytest.raises(DotifyLibrespotAuthenticationException) as captured:
        api._initialize_librespot()

    assert "dotify auth librespot" in str(captured.value)
    assert api.session_type == SessionType.LIBRESPOT
    assert api.librespot is None


def test_librespot_403_reports_confirmed_premium_without_fallback(
    tmp_path,
    monkeypatch,
):
    credentials_path = tmp_path / "credentials.json"
    credentials_path.write_text("{}", encoding="utf-8")
    api = SpotifyApi(
        session_type=SessionType.LIBRESPOT,
        librespot_credentials_path=str(credentials_path),
    )
    api.user_profile = premium_profile()

    class RejectedLibrespot:
        def __init__(self, credentials_path):
            raise RuntimeError("status: 403")

    monkeypatch.setattr("dotify.api.librespot.Librespot", RejectedLibrespot)

    with pytest.raises(DotifyLibrespotAuthenticationException) as captured:
        api._initialize_librespot()

    assert "Spotify reports a Premium account" in str(captured.value)
    assert "Free Spotify account" not in str(captured.value)
    assert api.session_type == SessionType.LIBRESPOT
    assert api.librespot is None


def test_librespot_connection_refusal_is_not_reported_as_authentication(
    tmp_path,
    monkeypatch,
):
    credentials_path = tmp_path / "credentials.json"
    credentials_path.write_text("{}", encoding="utf-8")
    api = SpotifyApi(
        session_type=SessionType.LIBRESPOT,
        librespot_credentials_path=str(credentials_path),
    )
    api.user_profile = premium_profile()

    class UnreachableLibrespot:
        def __init__(self, credentials_path):
            raise ConnectionRefusedError(61, "Connection refused")

    monkeypatch.setattr("dotify.api.librespot.Librespot", UnreachableLibrespot)

    with pytest.raises(DotifyLibrespotConnectionException) as captured:
        api._initialize_librespot()

    message = str(captured.value)
    assert "Spotify access point" in message
    assert "credentials were not rejected" in message
    assert "dotify auth librespot" not in message
    assert api.session_type == SessionType.LIBRESPOT
    assert api.librespot is None


def test_auth_librespot_saves_credentials_and_closes_session(tmp_path, monkeypatch):
    credentials_path = tmp_path / "librespot.json"
    state = {"closed": False, "callback_called": False}

    class AuthorizedSession:
        def close(self):
            state["closed"] = True

    def authorize(path: Path, callback):
        assert path == credentials_path
        callback("https://accounts.spotify.test/authorize")
        state["callback_called"] = True
        path.write_text("{}", encoding="utf-8")
        return AuthorizedSession()

    monkeypatch.setattr(Librespot, "authorize", authorize)

    result = CliRunner().invoke(
        cli,
        [
            "auth",
            "librespot",
            "--no-browser",
            "--credentials-path",
            str(credentials_path),
        ],
    )

    assert result.exit_code == 0
    assert "authorization saved" in result.output
    assert credentials_path.is_file()
    assert state == {"closed": True, "callback_called": True}


def test_auth_librespot_does_not_replace_credentials_without_force(
    tmp_path,
    monkeypatch,
):
    credentials_path = tmp_path / "librespot.json"
    credentials_path.write_text("existing", encoding="utf-8")
    authorize_called = False

    def authorize(*_args, **_kwargs):
        nonlocal authorize_called
        authorize_called = True

    monkeypatch.setattr(Librespot, "authorize", authorize)

    result = CliRunner().invoke(
        cli,
        ["auth", "librespot", "--credentials-path", str(credentials_path)],
    )

    assert result.exit_code == 0
    assert "already authorized" in result.output
    assert credentials_path.read_text(encoding="utf-8") == "existing"
    assert not authorize_called


def test_failed_forced_authorization_restores_previous_credentials(
    tmp_path,
    monkeypatch,
):
    credentials_path = tmp_path / "librespot.json"
    credentials_path.write_text("existing", encoding="utf-8")
    credentials_path.chmod(0o600)

    def authorize(path, _callback):
        path.write_text("partial", encoding="utf-8")
        raise RuntimeError("authorization rejected")

    monkeypatch.setattr(Librespot, "authorize", authorize)

    result = CliRunner().invoke(
        cli,
        [
            "auth",
            "librespot",
            "--force",
            "--no-browser",
            "--credentials-path",
            str(credentials_path),
        ],
    )

    assert result.exit_code == 1
    assert "authorization rejected" in result.output
    assert credentials_path.read_text(encoding="utf-8") == "existing"
    assert credentials_path.stat().st_mode & 0o777 == 0o600


def test_auth_web_imports_cookie_from_browser(tmp_path, monkeypatch):
    cookies_path = tmp_path / "cookies.txt"

    def import_cookie(browser, output, profile):
        assert (browser, output, profile) == ("chrome", cookies_path, "Profile 2")
        output.write_text("fixture", encoding="utf-8")
        return "chrome"

    monkeypatch.setattr(auth_commands, "import_spotify_cookie_from_browser", import_cookie)

    result = CliRunner().invoke(
        cli,
        [
            "auth",
            "web",
            "--browser",
            "chrome",
            "--profile",
            "Profile 2",
            "--cookies-path",
            str(cookies_path),
        ],
    )

    assert result.exit_code == 0
    assert "imported from chrome" in result.output


def test_auth_web_requires_force_to_replace_existing_file(tmp_path, monkeypatch):
    cookies_path = tmp_path / "cookies.txt"
    cookies_path.write_text("existing", encoding="utf-8")
    importer = pytest.fail
    monkeypatch.setattr(auth_commands, "import_spotify_cookie_from_browser", importer)

    result = CliRunner().invoke(
        cli,
        ["auth", "web", "--cookies-path", str(cookies_path)],
    )

    assert result.exit_code == 0
    assert "already exist" in result.output
    assert cookies_path.read_text(encoding="utf-8") == "existing"


def test_auth_status_reports_web_and_librespot_state(tmp_path, monkeypatch):
    cookies_path = tmp_path / "cookies.txt"
    credentials_path = tmp_path / "librespot.json"
    credentials_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(auth_commands, "spotify_cookie_file_has_sp_dc", lambda _: True)

    result = CliRunner().invoke(
        cli,
        [
            "auth",
            "status",
            "--cookies-path",
            str(cookies_path),
            "--credentials-path",
            str(credentials_path),
        ],
    )

    assert result.exit_code == 0
    assert "Web: sp_dc available" in result.output
    assert "Librespot: authorized" in result.output
