from __future__ import annotations

import errno
import os
import webbrowser
from pathlib import Path

import click

from ..api.browser_cookies import (
    SUPPORTED_BROWSER_SOURCES,
    import_spotify_cookie_from_browser,
    spotify_cookie_file_has_sp_dc,
)
from ..api.exceptions import DotifyBrowserCookieException
from ..env.paths import DotifyPaths


@click.group()
def auth():
    """Manage authentication used by optional Spotify sessions."""


@auth.command("web")
@click.option(
    "--browser",
    "browser_name",
    type=click.Choice(SUPPORTED_BROWSER_SOURCES),
    default="auto",
    show_default=True,
    help="Browser cookie store to inspect.",
)
@click.option(
    "--profile",
    default=None,
    help="Optional browser profile name or directory.",
)
@click.option(
    "--cookies-path",
    type=click.Path(path_type=Path, file_okay=True, dir_okay=False),
    default=None,
    help="Where the Netscape cookie file is stored.",
)
@click.option("--force", is_flag=True, help="Replace an existing cookie file.")
def authorize_web(
    browser_name: str,
    profile: str | None,
    cookies_path: Path | None,
    force: bool,
) -> None:
    """Import Spotify web authentication from a local browser."""

    path = (cookies_path or DotifyPaths().default_cookies_path).expanduser()
    if path.exists() and not force:
        click.echo(f"Spotify web cookies already exist: {path}")
        click.echo("Use --force to refresh them from the browser.")
        return

    try:
        source = import_spotify_cookie_from_browser(browser_name, path, profile)
    except DotifyBrowserCookieException as error:
        raise click.ClickException(str(error)) from error
    except Exception as error:
        raise click.ClickException(
            f"Browser cookie import failed: {type(error).__name__}: {error}"
        ) from error

    click.echo(f"Spotify web cookie imported from {source}: {path}")


@auth.command("librespot")
@click.option(
    "--credentials-path",
    type=click.Path(path_type=Path, file_okay=True, dir_okay=False),
    default=None,
    help="Where reusable Librespot credentials are stored.",
)
@click.option(
    "--browser/--no-browser",
    default=True,
    help="Open the Spotify authorization page in the default browser.",
)
@click.option(
    "--force",
    is_flag=True,
    help="Replace existing Librespot credentials.",
)
def authorize_librespot(
    credentials_path: Path | None,
    browser: bool,
    force: bool,
) -> None:
    """Authorize Librespot once and save reusable credentials."""

    path = (credentials_path or DotifyPaths().librespot_credentials_path).expanduser()
    if path.exists() and not force:
        click.echo(f"Librespot is already authorized: {path}")
        click.echo("Use --force to replace the stored credentials.")
        return

    previous_credentials = None
    previous_mode = None
    if path.exists():
        previous_credentials = path.read_bytes()
        previous_mode = path.stat().st_mode & 0o777
        path.unlink()

    def restore_previous_credentials() -> None:
        if path.exists():
            path.unlink()
        if previous_credentials is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(previous_credentials)
            os.chmod(path, previous_mode or 0o600)

    def show_authorization_url(url: str) -> None:
        click.echo("Open this Spotify authorization URL:")
        click.echo(url)
        click.echo("Waiting for the browser callback on http://127.0.0.1:5588/login ...")
        if browser and not webbrowser.open(url):
            click.echo("The browser could not be opened automatically; use the URL above.")

    session = None
    try:
        from ..api.librespot import Librespot

        session = Librespot.authorize(path, show_authorization_url)
    except ModuleNotFoundError as error:
        restore_previous_credentials()
        if error.name == "pyfreedom":
            raise click.ClickException(
                "The 'librespot' extra is required. Install it with "
                "`pip install dotify-cli[librespot]`."
            ) from error
        raise
    except OSError as error:
        if getattr(error, "errno", None) == errno.EADDRINUSE:
            message = (
                "OAuth callback port 5588 is already in use. Close the other process and retry."
            )
        else:
            message = f"Librespot OAuth failed: {error}"
        restore_previous_credentials()
        raise click.ClickException(message) from error
    except Exception as error:
        restore_previous_credentials()
        raise click.ClickException(f"Librespot OAuth failed: {error}") from error
    finally:
        if session is not None:
            session.close()

    click.echo(f"Librespot authorization saved: {path}")


@auth.command("status")
@click.option(
    "--cookies-path",
    type=click.Path(path_type=Path, file_okay=True, dir_okay=False),
    default=None,
    help="Web cookie file to inspect.",
)
@click.option(
    "--credentials-path",
    type=click.Path(path_type=Path, file_okay=True, dir_okay=False),
    default=None,
    help="Credential file to inspect.",
)
def auth_status(cookies_path: Path | None, credentials_path: Path | None) -> None:
    """Show whether reusable Web and Librespot authentication exist."""

    paths = DotifyPaths()
    web_path = (cookies_path or paths.default_cookies_path).expanduser()
    librespot_path = (credentials_path or paths.librespot_credentials_path).expanduser()
    if spotify_cookie_file_has_sp_dc(web_path):
        click.echo(f"Web: sp_dc available ({web_path})")
    else:
        click.echo("Web: sp_dc not available")
        click.echo("Run 'dotify auth web'.")
    if librespot_path.is_file():
        click.echo(f"Librespot: authorized ({librespot_path})")
    else:
        click.echo("Librespot: not authorized")
        click.echo("Run 'dotify auth librespot'.")


@auth.command("logout")
@click.option("--yes", is_flag=True, help="Remove credentials without confirmation.")
@click.option(
    "--credentials-path",
    type=click.Path(path_type=Path, file_okay=True, dir_okay=False),
    default=None,
    help="Credential file to remove.",
)
def auth_logout(yes: bool, credentials_path: Path | None) -> None:
    """Remove stored Librespot credentials."""

    path = (credentials_path or DotifyPaths().librespot_credentials_path).expanduser()
    if not path.exists():
        click.echo("Librespot is not authorized.")
        return
    if not yes and not click.confirm(f"Remove Librespot credentials at {path}?"):
        click.echo("Cancelled.")
        return
    path.unlink()
    click.echo("Librespot credentials removed.")
