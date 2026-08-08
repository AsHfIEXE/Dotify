"""Import the minimum Spotify cookie required by Dotify from local browsers."""

from __future__ import annotations

import logging
import os
import platform
from http.cookiejar import Cookie, MozillaCookieJar
from pathlib import Path

from yt_dlp.cookies import extract_cookies_from_browser

from .exceptions import DotifyBrowserCookieException

logger = logging.getLogger(__name__)

SUPPORTED_BROWSER_SOURCES = (
    "auto",
    "brave",
    "chrome",
    "chromium",
    "edge",
    "firefox",
    "opera",
    "safari",
    "vivaldi",
    "whale",
)


def spotify_cookie_file_has_sp_dc(path: str | Path) -> bool:
    cookie_path = Path(path).expanduser()
    if not cookie_path.is_file():
        return False
    cookies = MozillaCookieJar(str(cookie_path))
    try:
        cookies.load(ignore_discard=True, ignore_expires=True)
    except (OSError, ValueError):
        return False
    return any(
        cookie.name == "sp_dc" and cookie.domain.lstrip(".") == "spotify.com"
        for cookie in cookies
    )


def _browser_candidates(browser: str) -> tuple[str, ...]:
    if browser != "auto":
        return (browser,)
    if platform.system() == "Darwin":
        return ("chrome", "brave", "edge", "firefox", "safari", "chromium")
    if platform.system() == "Windows":
        return ("chrome", "edge", "brave", "firefox", "vivaldi", "opera")
    return ("chrome", "chromium", "brave", "edge", "firefox", "vivaldi", "opera")


def _spotify_cookie(value: str, expires: int | None) -> Cookie:
    return Cookie(
        version=0,
        name="sp_dc",
        value=value,
        port=None,
        port_specified=False,
        domain=".spotify.com",
        domain_specified=True,
        domain_initial_dot=True,
        path="/",
        path_specified=True,
        secure=True,
        expires=expires,
        discard=expires is None,
        comment=None,
        comment_url=None,
        rest={"HttpOnly": None},
        rfc2109=False,
    )


def import_spotify_cookie_from_browser(
    browser: str,
    output_path: str | Path,
    profile: str | None = None,
) -> str:
    """Extract only ``sp_dc`` and atomically save it as a Netscape cookie file.

    Returns the browser source that contained the cookie. Existing output is
    untouched if extraction fails.
    """

    if browser not in SUPPORTED_BROWSER_SOURCES:
        raise DotifyBrowserCookieException(f"Unsupported browser source: {browser}")

    failures = []
    selected_browser = None
    selected_cookie = None
    for candidate in _browser_candidates(browser):
        try:
            browser_cookies = extract_cookies_from_browser(candidate, profile=profile)
            selected_cookie = next(
                (
                    cookie
                    for cookie in browser_cookies
                    if cookie.name == "sp_dc"
                    and cookie.domain.lstrip(".") == "spotify.com"
                ),
                None,
            )
        except Exception as error:
            failures.append(f"{candidate}: {type(error).__name__}")
            logger.debug(
                "Could not inspect %s browser cookies: %s",
                candidate,
                type(error).__name__,
            )
            continue
        if selected_cookie is not None:
            selected_browser = candidate
            break
        failures.append(f"{candidate}: sp_dc not found")

    if selected_cookie is None or selected_browser is None:
        attempted = ", ".join(failures) or browser
        raise DotifyBrowserCookieException(
            "No logged-in Spotify sp_dc cookie was found in the selected browser(s). "
            f"Attempted: {attempted}"
        )

    path = Path(output_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    cookie_jar = MozillaCookieJar(str(temporary))
    cookie_jar.set_cookie(_spotify_cookie(selected_cookie.value, selected_cookie.expires))
    try:
        cookie_jar.save(ignore_discard=True, ignore_expires=True)
        os.chmod(temporary, 0o600)
        temporary.replace(path)
        os.chmod(path, 0o600)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise

    logger.info("Imported Spotify authentication cookie from %s", selected_browser)
    return selected_browser
