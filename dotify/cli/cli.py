import asyncio
import logging
import time
from functools import wraps
from http.cookiejar import LoadError
from pathlib import Path

import click
import colorama
import httpx
from dataclass_click import dataclass_click

from .. import __version__
from ..api.adapter import SpotifyApiAdapter
from ..api.api import SpotifyApi
from ..api.browser_cookies import import_spotify_cookie_from_browser
from ..api.enums import SessionType
from ..api.exceptions import (
    DotifyAuthenticationException,
    DotifyLibrespotAuthenticationException,
    DotifyLibrespotConnectionException,
    DotifyRequestException,
)
from ..downloader.audio import SpotifyAudioDownloader
from ..downloader.base import SpotifyBaseDownloader
from ..downloader.downloader import SpotifyDownloader
from ..downloader.exceptions import DotifyMediaFileExists, DotifySyncedLyricsOnly
from ..downloader.video import SpotifyVideoDownloader
from ..env.paths import DotifyPaths
from ..env.checks import CheckResult, HealthCheck, CheckStatus
from ..env.errors import DotifyErrorHandler
from ..interface.audio import SpotifyAudioInterface
from ..interface.base import SpotifyBaseInterface
from ..interface.enums import AutoMediaOption
from ..interface.episode import SpotifyEpisodeInterface
from ..interface.episode_video import SpotifyEpisodeVideoInterface
from ..interface.exceptions import DotifyUrlParseException
from ..interface.exceptions import DotifyMediaFlatFilterException
from ..interface.interface import SpotifyInterface
from ..interface.music_video import SpotifyMusicVideoInterface
from ..interface.song import SpotifySongInterface
from ..interface.video import SpotifyVideoInterface
from ..client import DotifyClient
from ..i18n import Translator
from ..plugins import PluginManager
from ..queue import PersistentDownloadQueue
from ..tui import TerminalUI, format_duration
from .cli_config import CliConfig
from .config_file import ConfigFile
from .database import Database
from .utils import CustomLoggerFormatter
from .env_commands import env
from .init_command import init_command
from .auth_commands import auth

logger = logging.getLogger(__name__)


def _setup_logging(config: CliConfig) -> logging.Logger:
    """Configure root logger with stream and optional file handlers."""
    root_logger = logging.getLogger(__name__.split(".")[0])
    root_logger.setLevel(config.log_level)
    root_logger.propagate = False

    for handler in list(root_logger.handlers):
        if getattr(handler, "_dotify_cli_handler", False):
            root_logger.removeHandler(handler)
            handler.close()

    stream_handler = logging.StreamHandler()
    stream_handler._dotify_cli_handler = True
    stream_handler.setFormatter(CustomLoggerFormatter())
    if config.tui:
        stream_handler.setLevel(logging.WARNING)
    root_logger.addHandler(stream_handler)

    if config.log_file:
        file_handler = logging.FileHandler(config.log_file, encoding="utf-8")
        file_handler._dotify_cli_handler = True
        file_handler.setFormatter(CustomLoggerFormatter(use_colors=False))
        root_logger.addHandler(file_handler)

    return root_logger


def _load_urls(config: CliConfig) -> list[str]:
    """Load URLs from config, expanding text files if --read-urls-as-txt is set."""
    if config.read_urls_as_txt:
        urls = []
        for url in config.urls:
            path = Path(url)
            if path.is_file():
                urls.extend(
                    line.strip()
                    for line in path.read_text(encoding="utf-8").splitlines()
                    if line.strip()
                )
            else:
                urls.append(url)
        return urls
    return list(config.urls)


async def _iter_items(items):
    for item in items:
        yield item


def make_sync(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))

    return wrapper


class DefaultGroup(click.Group):
    def parse_args(self, ctx, args):
        if args and args[0] not in self.commands and args[0] not in ('-h', '--help', '-v', '--version'):
            args.insert(0, 'download')
        return super().parse_args(ctx, args)


@click.group(cls=DefaultGroup)
@click.help_option("-h", "--help")
@click.version_option(__version__, "-v", "--version")
def cli():
    """Dotify - Spotify Music Downloader"""
    pass


@cli.command()
@dataclass_click(CliConfig)
@ConfigFile.loader
@make_sync
async def download(config: CliConfig):
    """Download content from Spotify (default command)"""
    await _execute_download(config)


@cli.command()
@dataclass_click(CliConfig)
@ConfigFile.loader
@make_sync
async def main(config: CliConfig):
    """Download content from Spotify (legacy command, same as download)"""
    await _execute_download(config)


async def _execute_download(config: CliConfig) -> None:
    """Render unexpected failures cleanly unless tracebacks were requested."""

    try:
        await _run_download(config.skip_preflight, config)
    except (click.ClickException, click.exceptions.Exit):
        raise
    except Exception as error:
        if not config.no_exceptions:
            raise
        details = str(error).strip() or type(error).__name__
        raise click.ClickException(
            f"Unexpected error: {details}\n\n"
            "Run 'dotify env doctor --verbose' for diagnostics or rerun with "
            "--exceptions for a traceback."
        ) from error


def _raise_cli_error(config: CliConfig, error: Exception, message: str) -> None:
    """Raise a readable CLI failure, preserving opt-in traceback behavior."""

    if not config.no_exceptions:
        raise error
    raise click.ClickException(message) from error


async def _run_download(skip_preflight: bool, config: CliConfig):
    colorama.just_fix_windows_console()
    _setup_logging(config)
    translator = Translator(config.language)
    started_at = time.monotonic()

    if config.auto_media_option == AutoMediaOption.LIKED_TRACKS:
        config.urls = ["Liked Tracks"]
    elif not config.urls:
        raise click.exceptions.MissingParameter(
            param_type="argument",
            param_hint="'URLS...'",
        )

    if config.cookies_from_browser:
        try:
            source = await asyncio.to_thread(
                import_spotify_cookie_from_browser,
                config.cookies_from_browser,
                config.cookies_path,
                config.browser_profile,
            )
            logger.info(translator("cookies_refreshed", browser=source))
        except Exception as error:
            handler = DotifyErrorHandler(language=translator.language)
            _raise_cli_error(
                config,
                error,
                handler.handle_download_error(error),
            )

    if not skip_preflight:
        if not _run_preflight_checks(config, translator):
            raise click.ClickException(
                "Preflight checks failed. Run 'dotify env doctor' for details or use --skip-preflight to bypass."
            )

    logger.info(translator("starting", version=__version__))

    cookies_path = config.cookies_path
    configured_wvd_path = Path(config.wvd_path) if config.wvd_path else None
    wvd_path = (
        str(configured_wvd_path)
        if configured_wvd_path and configured_wvd_path.is_file()
        else None
    )
    if skip_preflight and configured_wvd_path and not configured_wvd_path.is_file():
        logger.warning(
            f"Widevine key file not found at {configured_wvd_path}; continuing "
            "without WVD. Protected streams will not be available."
        )

    if config.database_path:
        database = Database(config.database_path)
        flat_filter = database.flat_filter
    else:
        database = None
        flat_filter = None

    error_handler = DotifyErrorHandler(language=translator.language)
    api = None
    client = None
    terminal_ui = None
    processing_started = False
    error_count = 0
    success_count = 0
    skipped_count = 0
    try:
        try:
            raw_api = await SpotifyApi.create_from_netscape_cookies(
                cookies_path,
                session_type=config.session_type,
                librespot_credentials_path=config.librespot_credentials_path,
                widevine_retries=config.widevine_retries,
                widevine_backoff=config.widevine_backoff,
                widevine_max_wait=config.widevine_max_wait,
                widevine_request_interval=config.widevine_request_interval,
            )
        except ModuleNotFoundError as error:
            if error.name == "pyfreedom":
                _raise_cli_error(
                    config,
                    error,
                    "The 'librespot' extra is required for the librespot session. "
                    "Install it with `pip install dotify-cli[librespot]` or select "
                    "another supported --session-type.",
                )
            raise
        except (FileNotFoundError, LoadError) as error:
            _raise_cli_error(
                config,
                error,
                error_handler.handle_missing_cookies(),
            )
        except ValueError as error:
            if "sp_dc" in str(error) or "cookies" in str(error).lower():
                _raise_cli_error(
                    config,
                    error,
                    error_handler.handle_missing_cookies(),
                )
            _raise_cli_error(
                config,
                error,
                translator("initialization_error")
                + "\n"
                + error_handler.handle_download_error(error),
            )
        except httpx.TimeoutException as error:
            _raise_cli_error(
                config,
                error,
                translator("network_error")
                + "\n"
                + translator("network_timeout")
                + "\n\n"
                + translator("network_fix"),
            )
        except httpx.RequestError as error:
            details = str(error).strip() or type(error).__name__
            _raise_cli_error(
                config,
                error,
                translator("network_error")
                + "\n"
                + translator("network_failed", details=details)
                + "\n\n"
                + translator("network_fix"),
            )
        except DotifyLibrespotConnectionException as error:
            _raise_cli_error(
                config,
                error,
                translator("network_error")
                + "\n"
                + error_handler.handle_download_error(error),
            )
        except (
            DotifyAuthenticationException,
            DotifyLibrespotAuthenticationException,
        ) as error:
            _raise_cli_error(
                config,
                error,
                translator("authentication_error")
                + "\n"
                + error_handler.handle_download_error(error),
            )
        except DotifyRequestException as error:
            _raise_cli_error(
                config,
                error,
                translator("spotify_request_error")
                + "\n"
                + error_handler.handle_download_error(error),
            )
        except Exception as error:
            _raise_cli_error(
                config,
                error,
                translator("initialization_error")
                + "\n"
                + error_handler.handle_download_error(error),
            )

        api = SpotifyApiAdapter(raw_api)
        if api.anonymous_session:
            raise click.ClickException(error_handler.handle_authentication_error())

        terminal_ui = TerminalUI(translator) if config.tui else None
        if terminal_ui:
            raw_api.widevine_wait_callback = terminal_ui.wait_for_widevine_retry
        base_interface = SpotifyBaseInterface(
            api=api,
            cover_size=config.cover_size,
            skip_stream_info=config.synced_lyrics_only or config.dry_run,
            defer_stream_info=True,
            wvd_path=wvd_path,
            spotify_dll_path=config.spotify_dll_path,
        )
        video_interface = SpotifyVideoInterface(
            base=base_interface,
            video_format=config.video_format,
            resolution=config.video_resolution,
        )
        audio_interface = SpotifyAudioInterface(
            base=base_interface,
            audio_quality_priority=config.audio_quality,
            strict_audio_quality=config.strict_audio_quality,
        )
        interface = SpotifyInterface(
            base=audio_interface,
            song=SpotifySongInterface(audio_interface),
            episode=SpotifyEpisodeInterface(audio_interface),
            music_video=SpotifyMusicVideoInterface(video_interface),
            episode_video=SpotifyEpisodeVideoInterface(video_interface),
            prefer_video=config.prefer_video,
            flat_filter=flat_filter if not config.overwrite else None,
        )

        base_downloader = SpotifyBaseDownloader(
            interface=interface,
            output_path=config.output,
            temp_path=config.temp,
            aria2c_path=config.aria2c_path,
            curl_path=config.curl_path,
            ffmpeg_path=config.ffmpeg_path,
            mp4box_path=config.mp4box_path,
            mp4decrypt_path=config.mp4decrypt_path,
            shaka_packager_path=config.shaka_packager_path,
            album_folder_template=config.album_folder_template,
            compilation_folder_template=config.compilation_folder_template,
            podcast_folder_template=config.podcast_folder_template,
            no_album_folder_template=config.no_album_folder_template,
            single_disc_file_template=config.single_disc_file_template,
            multi_disc_file_template=config.multi_disc_file_template,
            podcast_file_template=config.podcast_file_template,
            no_album_file_template=config.no_album_file_template,
            playlist_file_template=config.playlist_file_template,
            date_tag_template=config.date_tag_template,
            exclude_tags=config.exclude_tags,
            truncate=config.truncate,
            silent=config.tui,
            progress_callback=terminal_ui.on_progress if terminal_ui else None,
        )
        downloader = SpotifyDownloader(
            base=base_downloader,
            audio=SpotifyAudioDownloader(
                base=base_downloader,
                download_mode=config.audio_download_mode,
                remux_mode=config.audio_remux_mode,
            ),
            video=SpotifyVideoDownloader(
                base=base_downloader,
                remux_mode=config.video_remux_mode,
            ),
            no_synced_lyrics_file=config.no_synced_lyrics_file,
            save_playlist_file=config.save_playlist_file,
            save_cover_file=config.save_cover_file,
            overwrite=config.overwrite,
            synced_lyrics_only=config.synced_lyrics_only,
        )
        plugins = PluginManager.discover()
        for plugin_error in plugins.load_errors:
            logger.warning(str(plugin_error))
        client = DotifyClient(
            api=api,
            interface=interface,
            downloader=downloader,
            plugins=plugins,
            close_api=True,
            queue=PersistentDownloadQueue(config.queue_state_path, config.output),
            resume=config.resume,
        )

        urls = _load_urls(config)
        processing_started = True
        for url_index, url in enumerate(urls, 1):
            url_progress = click.style(f"[URL {url_index}/{len(urls)}]", dim=True)
            logger.info(url_progress + " " + translator("processing_url", url=url))
            download_queue = client.iter_items(url, config.auto_media_option)
            stream_tui_items = False

            if terminal_ui:
                try:
                    is_playlist = (
                        base_interface.parse_url_info(url).media_type == "playlist"
                    )
                except DotifyUrlParseException:
                    is_playlist = False

                if is_playlist:
                    stream_tui_items = (
                        await terminal_ui.select_playlist_mode() == "all"
                    )

                if stream_tui_items:
                    terminal_ui.show_streaming_queue()
                else:
                    queued_items = []
                    while True:
                        try:
                            queued_items.append(await download_queue.__anext__())
                        except StopAsyncIteration:
                            break
                        except DotifyUrlParseException as error:
                            error_count += 1
                            logger.error(
                                url_progress
                                + " "
                                + error_handler.handle_download_error(error)
                            )
                            break
                        except Exception as error:
                            error_count += 1
                            logger.error(
                                translator("fetch_error", error=str(error)),
                                exc_info=not config.no_exceptions,
                            )
                    queued_items = await terminal_ui.select_items(queued_items)
                    terminal_ui.show_queue(queued_items)
                    terminal_ui.add_items(queued_items)
                    terminal_ui.start()
                    download_queue = _iter_items(queued_items)

            download_index = 1
            while True:
                item = None
                item_status = "failed"
                download_queue_progress = click.style(
                    f"[Track {download_index}]",
                    dim=True,
                )
                try:
                    item = await download_queue.__anext__()
                except StopAsyncIteration:
                    break
                except DotifyUrlParseException as error:
                    error_count += 1
                    logger.error(
                        url_progress + " " + error_handler.handle_download_error(error)
                    )
                    break
                except Exception as error:
                    error_count += 1
                    logger.error(
                        download_queue_progress
                        + " "
                        + translator("fetch_error", error=str(error)),
                        exc_info=not config.no_exceptions,
                    )
                    download_index += 1
                    continue

                if terminal_ui and stream_tui_items:
                    terminal_ui.add_item(item, download_index)
                    terminal_ui.start()

                if download_index > 1 and config.wait_interval > 0:
                    await asyncio.sleep(config.wait_interval)

                media_title = translator("unknown_title")
                try:
                    media_metadata = getattr(item.media, "media_metadata", {}) or {}
                    media_title = media_metadata.get("name", media_title)
                    if terminal_ui:
                        terminal_ui.start_item(item)

                    if item.media.error:
                        raise item.media.error

                    if config.dry_run:
                        skipped_count += 1
                        item_status = "skipped"
                        logger.info(
                            download_queue_progress
                            + " "
                            + translator("would_download", title=media_title)
                        )
                    else:
                        logger.info(
                            download_queue_progress
                            + " "
                            + translator("downloading", title=media_title)
                        )
                        await client.download_item(item)
                        actual_quality = getattr(item, "audio_description", None)
                        requested_quality = getattr(
                            item,
                            "fallback_audio_description",
                            None,
                        )
                        if actual_quality and requested_quality:
                            logger.warning(
                                translator(
                                    "fallback_downloaded",
                                    requested=requested_quality,
                                    actual=actual_quality,
                                    path=item.final_path,
                                )
                            )
                        elif actual_quality:
                            logger.info(
                                translator(
                                    "downloaded_format",
                                    actual=actual_quality,
                                    path=item.final_path,
                                )
                            )
                        success_count += 1
                        item_status = "success"
                except (
                    DotifyMediaFileExists,
                    DotifySyncedLyricsOnly,
                    DotifyMediaFlatFilterException,
                ) as error:
                    skipped_count += 1
                    item_status = "skipped"
                    logger.warning(
                        download_queue_progress
                        + " "
                        + translator(
                            "skipping",
                            title=media_title,
                            error=error_handler.handle_download_error(error),
                        )
                    )
                except Exception as error:
                    error_count += 1
                    logger.error(
                        download_queue_progress
                        + " "
                        + translator("download_error", title=media_title)
                        + "\n"
                        + error_handler.handle_download_error(error),
                        exc_info=not config.no_exceptions,
                    )
                finally:
                    if terminal_ui and item:
                        terminal_ui.finish_item(item, item_status)
                    download_index += 1
                    if (
                        database
                        and item
                        and item.media
                        and item.media.media_metadata
                        and item.staged_path
                        and item_status == "success"
                        and not config.dry_run
                    ):
                        media_id = item.media.media_metadata["uri"].split(":")[-1]
                        database.add(media_id, item.final_path)

        duration = format_duration(time.monotonic() - started_at)
        logger.info(
            translator(
                "finished",
                success=success_count,
                skipped=skipped_count,
                errors=error_count,
                duration=duration,
            )
        )
        if error_count:
            raise click.exceptions.Exit(1)
    finally:
        try:
            if terminal_ui and processing_started:
                terminal_ui.close()
        finally:
            if client is not None:
                await client.aclose()
            elif api is not None:
                await api.aclose()


def _run_preflight_checks(
    config: CliConfig,
    translator: Translator | None = None,
) -> bool:
    """Run preflight environment checks before download."""
    translator = translator or Translator(config.language)
    logger.info(translator("preflight_running"))

    paths = DotifyPaths()
    health_check = HealthCheck(paths)

    cookies_path = Path(config.cookies_path) if config.cookies_path else None
    wvd_path = Path(config.wvd_path) if config.wvd_path else None
    results = health_check.check_all(
        skip_optional=True,
        cookies_path=cookies_path,
        wvd_path=wvd_path,
    )
    results = [result for result in results if result.name != "Librespot Credentials"]

    librespot_credentials_path = Path(config.librespot_credentials_path)
    if config.session_type == SessionType.LIBRESPOT and not librespot_credentials_path.is_file():
        results.append(
            CheckResult(
                name="Librespot Credentials",
                status=CheckStatus.FAIL,
                message="The librespot session requires separate OAuth credentials",
                fix="Run 'dotify auth librespot' and retry",
                path=librespot_credentials_path,
            )
        )

    web_download_requires_wvd = (
        config.session_type == SessionType.WEB
        and not config.dry_run
        and not config.synced_lyrics_only
    )
    if web_download_requires_wvd and (wvd_path is None or not wvd_path.is_file()):
        results.append(
            CheckResult(
                name="Widevine Key (web session)",
                status=CheckStatus.FAIL,
                message="The web session requires WVD for protected audio/video streams",
                fix=(
                    "Provide --wvd-path, or use --session-type librespot "
                    "--audio-quality vorbis-medium"
                ),
                path=wvd_path,
            )
        )

    failed = [r for r in results if r.status == CheckStatus.FAIL]
    warnings = [r for r in results if r.status == CheckStatus.WARN]

    if failed:
        logger.error(translator("preflight_failed"))
        for result in failed:
            logger.error(f"  [X] {result.name}: {result.message}")
            if result.fix:
                logger.error("    " + translator("fix", fix=result.fix))
        return False

    if warnings:
        logger.warning(translator("preflight_warnings"))
        for result in warnings:
            logger.warning(f"  [!] {result.name}: {result.message}")
            if result.fix:
                logger.warning("    " + translator("fix", fix=result.fix))

    logger.info(translator("preflight_passed"))
    return True


cli.add_command(env)
cli.add_command(init_command)
cli.add_command(auth)
