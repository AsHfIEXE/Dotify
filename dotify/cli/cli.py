import asyncio
import logging
from functools import wraps
from pathlib import Path

import click
import colorama
from dataclass_click import dataclass_click

from .. import __version__
from ..api.api import SpotifyApi
from ..api.enums import SessionType
from ..downloader.audio import SpotifyAudioDownloader
from ..downloader.base import SpotifyBaseDownloader
from ..downloader.downloader import SpotifyDownloader
from ..downloader.exceptions import DotifyDownloaderException
from ..downloader.video import SpotifyVideoDownloader
from ..env.paths import DotifyPaths
from ..env.checks import HealthCheck, CheckStatus
from ..env.errors import DotifyErrorHandler
from ..interface.audio import SpotifyAudioInterface
from ..interface.base import SpotifyBaseInterface
from ..interface.enums import AutoMediaOption
from ..interface.episode import SpotifyEpisodeInterface
from ..interface.episode_video import SpotifyEpisodeVideoInterface
from ..interface.exceptions import DotifyUrlParseException
from ..interface.interface import SpotifyInterface
from ..interface.music_video import SpotifyMusicVideoInterface
from ..interface.song import SpotifySongInterface
from ..interface.video import SpotifyVideoInterface
from .cli_config import CliConfig
from .config_file import ConfigFile
from .database import Database
from .utils import CustomLoggerFormatter, prompt_path
from .env_commands import env

logger = logging.getLogger(__name__)


def _setup_logging(config: CliConfig) -> logging.Logger:
    """Configure root logger with stream and optional file handlers."""
    root_logger = logging.getLogger(__name__.split(".")[0])
    root_logger.setLevel(config.log_level)
    root_logger.propagate = False

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(CustomLoggerFormatter())
    root_logger.addHandler(stream_handler)

    if config.log_file:
        file_handler = logging.FileHandler(config.log_file, encoding="utf-8")
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


def make_sync(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))

    return wrapper


@click.group()
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
    await _run_download(config.skip_preflight, config)


@cli.command()
@dataclass_click(CliConfig)
@ConfigFile.loader
@make_sync
async def main(config: CliConfig):
    """Download content from Spotify (legacy command, same as download)"""
    await _run_download(config.skip_preflight, config)


async def _run_download(skip_preflight: bool, config: CliConfig):
    colorama.just_fix_windows_console()
    _setup_logging(config)

    if not skip_preflight:
        if not _run_preflight_checks(config):
            logger.critical(
                "Preflight checks failed. Run 'dotify env doctor' for details or use --skip-preflight to bypass."
            )
            return

    if config.auto_media_option == AutoMediaOption.LIKED_TRACKS:
        config.urls = ["Liked Tracks"]
    elif not config.urls:
        raise click.exceptions.MissingParameter(
            param_type="argument",
            param_hint="'URLS...'",
        )

    logger.info(f"Starting Dotify {__version__}")

    cookies_path = prompt_path(config.cookies_path)

    if config.wvd_path:
        wvd_path = prompt_path(config.wvd_path)
    else:
        wvd_path = None

    if config.database_path:
        database = Database(config.database_path)
        flat_filter = database.flat_filter
    else:
        database = None
        flat_filter = None

    error_handler = DotifyErrorHandler()

    try:
        api = await SpotifyApi.create_from_netscape_cookies(
            cookies_path,
            session_type=config.session_type,
        )
    except ModuleNotFoundError as e:
        if e.name == "librespot":
            logger.critical(
                "The 'librespot' extra is required to use the librespot session type, "
                "please install the package with `pip install dotify-cli[librespot]` and try again"
            )
            return
        raise e
    except ValueError as e:
        if "sp_dc" in str(e) or "cookies" in str(e).lower():
            logger.critical(error_handler.handle_missing_cookies())
            return
        raise e
    except Exception as e:
        error_handler.log_error_with_fix(e, "Authentication error")
        return

    if api.anonymous_session:
        logger.critical(error_handler.handle_authentication_error())
        return

    base_interface = SpotifyBaseInterface(
        api=api,
        cover_size=config.cover_size,
        skip_stream_info=config.synced_lyrics_only or config.dry_run,
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
    )
    song_interface = SpotifySongInterface(audio_interface)
    episode_interface = SpotifyEpisodeInterface(audio_interface)
    music_video_interface = SpotifyMusicVideoInterface(video_interface)
    episode_video_interface = SpotifyEpisodeVideoInterface(video_interface)
    interface = SpotifyInterface(
        base=audio_interface,
        song=song_interface,
        episode=episode_interface,
        music_video=music_video_interface,
        episode_video=episode_video_interface,
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
    )
    audio_downloader = SpotifyAudioDownloader(
        base=base_downloader,
        download_mode=config.audio_download_mode,
        remux_mode=config.audio_remux_mode,
    )
    video_downloader = SpotifyVideoDownloader(
        base=base_downloader,
        remux_mode=config.video_remux_mode,
    )
    downloader = SpotifyDownloader(
        base=base_downloader,
        audio=audio_downloader,
        video=video_downloader,
        no_synced_lyrics_file=config.no_synced_lyrics_file,
        save_playlist_file=config.save_playlist_file,
        save_cover_file=config.save_cover_file,
        overwrite=config.overwrite,
        synced_lyrics_only=config.synced_lyrics_only,
    )

    urls = _load_urls(config)

    error_count = 0
    for url_index, url in enumerate(urls, 1):
        url_progress = click.style(f"[URL {url_index}/{len(urls)}]", dim=True)
        logger.info(url_progress + f' Processing "{url}"')
        download_queue = downloader.get_download_item(url, config.auto_media_option)
        download_index = 1
        while True:
            item = None
            download_queue_progress = click.style(
                f"[Track {download_index}]",
                dim=True,
            )
            try:
                item = await download_queue.__anext__()
            except StopAsyncIteration:
                break
            except DotifyUrlParseException as e:
                logger.error(url_progress + f" {str(e)}")
                break
            except Exception as e:
                error_count += 1
                logger.error(
                    download_queue_progress + f" Error fetching media: {str(e)}",
                    exc_info=not config.no_exceptions,
                )
                download_index += 1
                continue

            try:
                media_title = item.media.media_metadata.get("name", "Unknown Title")

                if item.media.error:
                    raise item.media.error

                if config.dry_run:
                    logger.info(download_queue_progress + f' Would download "{media_title}"')
                else:
                    logger.info(download_queue_progress + f' Downloading "{media_title}"')
                    await downloader.download(item)
            except DotifyDownloaderException as e:
                logger.warning(
                    download_queue_progress + f' Skipping "{media_title}": {str(e)}'
                )
            except Exception as e:
                error_count += 1
                error_handler.log_error_with_fix(e, f"Error downloading {media_title}")
                logger.error(
                    download_queue_progress + f' Error downloading "{media_title}"',
                    exc_info=not config.no_exceptions,
                )
            finally:
                download_index += 1
                if (
                    database
                    and item
                    and item.media
                    and item.media.media_metadata
                    and item.staged_path
                    and not config.dry_run
                ):
                    media_id = item.media.media_metadata["uri"].split(":")[-1]
                    database.add(media_id, item.final_path)
                await asyncio.sleep(config.wait_interval)

    logger.info(f"Finished with {error_count} error(s)")


def _run_preflight_checks(config: CliConfig) -> bool:
    """Run preflight environment checks before download."""
    logger.info("Running preflight checks...")

    paths = DotifyPaths()
    health_check = HealthCheck(paths)

    results = health_check.check_all(skip_optional=True)

    failed = [r for r in results if r.status == CheckStatus.FAIL]
    warnings = [r for r in results if r.status == CheckStatus.WARN]

    if failed:
        logger.error("Preflight checks failed:")
        for result in failed:
            logger.error(f"  [X] {result.name}: {result.message}")
            if result.fix:
                logger.error(f"    Fix: {result.fix}")
        return False

    if warnings:
        logger.warning("Preflight warnings:")
        for result in warnings:
            logger.warning(f"  [!] {result.name}: {result.message}")
            if result.fix:
                logger.warning(f"    Fix: {result.fix}")

    logger.info("[OK] Preflight checks passed")
    return True


cli.add_command(env)
