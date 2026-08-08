from http.cookiejar import Cookie, CookieJar, MozillaCookieJar

import pytest

from dotify.api.browser_cookies import (
    import_spotify_cookie_from_browser,
    spotify_cookie_file_has_sp_dc,
)
from dotify.api.exceptions import DotifyBrowserCookieException


def cookie(name: str, value: str, domain: str) -> Cookie:
    return Cookie(
        version=0,
        name=name,
        value=value,
        port=None,
        port_specified=False,
        domain=domain,
        domain_specified=True,
        domain_initial_dot=domain.startswith("."),
        path="/",
        path_specified=True,
        secure=True,
        expires=None,
        discard=True,
        comment=None,
        comment_url=None,
        rest={},
        rfc2109=False,
    )


def test_browser_import_writes_only_spotify_sp_dc(tmp_path, monkeypatch):
    source = CookieJar()
    source.set_cookie(cookie("sp_dc", "spotify-secret", ".spotify.com"))
    source.set_cookie(cookie("other", "other-spotify-secret", ".spotify.com"))
    source.set_cookie(cookie("session", "unrelated-secret", ".example.com"))
    monkeypatch.setattr(
        "dotify.api.browser_cookies.extract_cookies_from_browser",
        lambda *_args, **_kwargs: source,
    )
    output = tmp_path / "cookies.txt"

    selected = import_spotify_cookie_from_browser("chrome", output)

    saved = MozillaCookieJar(str(output))
    saved.load(ignore_discard=True, ignore_expires=True)
    assert selected == "chrome"
    assert [(entry.name, entry.value) for entry in saved] == [
        ("sp_dc", "spotify-secret")
    ]
    assert output.stat().st_mode & 0o777 == 0o600
    assert "unrelated-secret" not in output.read_text(encoding="utf-8")
    assert spotify_cookie_file_has_sp_dc(output)


def test_failed_browser_import_preserves_existing_cookie_file(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "dotify.api.browser_cookies.extract_cookies_from_browser",
        lambda *_args, **_kwargs: CookieJar(),
    )
    output = tmp_path / "cookies.txt"
    output.write_text("existing", encoding="utf-8")

    with pytest.raises(DotifyBrowserCookieException):
        import_spotify_cookie_from_browser("chrome", output)

    assert output.read_text(encoding="utf-8") == "existing"
