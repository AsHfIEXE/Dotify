<div align="center">

[![PyPI](https://img.shields.io/pypi/v/dotify-cli?style=for-the-badge&logo=pypi&logoColor=white)](https://pypi.org/project/dotify-cli/)
[![Python](https://img.shields.io/pypi/pyversions/dotify-cli?style=for-the-badge&logo=python&logoColor=white)](https://pypi.org/project/dotify-cli/)
[![License](https://img.shields.io/badge/license-MIT-blue?style=for-the-badge)](LICENSE)

# 🎵 Dotify

An asynchronous Python application and CLI for downloading playable tracks,
albums, playlists, podcast episodes, shows, and video content directly from
Spotify.

[Installation](#installation) • [Quick start](#quick-start) •
[Configuration](#configuration) • [Development](#development)

</div>

> [!IMPORTANT]
> Dotify is an independent project and is not affiliated with Spotify. Use it
> only for content you are authorized to access and download, and comply with
> the laws and service terms that apply to you.

This checkout is release version `3.0.4`.

## What Dotify downloads from

Dotify obtains metadata, stream URLs, manifests, cover art, and lyrics from
Spotify. It does **not** search YouTube or substitute YouTube audio.

The `yt-dlp` dependency is used only as a mature HTTP/fragment transfer engine:

```text
Spotify URL
  -> Dotify Spotify API and media interfaces
  -> Spotify CDN URL or Spotify media segments
  -> yt-dlp HTTP/fragment downloader (or aria2c/curl for audio)
  -> decrypt/remux, tag, and save
```

This is why `yt-dlp` is present even though Spotify remains the media source.

## Features

- Spotify track, album, playlist, artist, show, and episode URLs
- Songs, podcast audio, music videos, and video podcast episodes when available
- Vorbis, AAC, FLAC, MP4-FLAC, MP4, and WebM support
- Ordered audio-quality fallbacks
- Metadata, cover art embedding, and synced LRC lyrics when Spotify provides them
- Configurable output folders, filenames, tags, remux tools, and download modes
- Multiple URLs and URL lists from text files
- Interactive terminal queue with item selection, progress, speed, ETA, and summary
- Metadata-only TUI selection; streams and licenses are resolved only for chosen items
- Persistent download state with safe `--resume` and `--no-resume` controls
- Configurable Widevine request pacing and bounded `429` retries
- English and Turkish terminal text
- Guided first-time setup with `dotify init`
- Environment diagnostics with `dotify env doctor`
- Secure `sp_dc` import from Chrome, Firefox, Safari, Edge, Brave, and related browsers
- Async, CLI-independent Python API and entry-point based plugins

## Requirements

- Python 3.10 or newer
- A Netscape-format Spotify `cookies.txt` containing the logged-in account's
  `sp_dc` cookie
- FFmpeg for the default remux workflow and video output
- The `librespot` optional dependency (powered by the protobuf 6 compatible
  `pyfreedom` package) for the default `librespot` session

The `web` session downloads protected AAC/MP4 media and therefore requires a
compatible Widevine `device.wvd` (except for dry-run and lyrics-only use).
Alternative modes may require `aria2c`, `curl`, MP4Box, `mp4decrypt`, or Shaka
Packager. Run `dotify env doctor --verbose` to see the current environment
status.

Availability and maximum quality depend on the Spotify account, selected
session type, market, media item, and supplied decryption material. A requested
format is not guaranteed to exist for every item.

## Installation

### From PyPI

The default session type is `librespot`, so the recommended installation is:

```bash
python -m pip install --upgrade "dotify-cli[librespot]"
```

The base package can instead be installed without that optional dependency,
but the `web` session and a valid WVD must then be selected explicitly:

```bash
python -m pip install --upgrade dotify-cli
dotify --session-type web "SPOTIFY_URL"
```

Run the guided setup and diagnostics:

```bash
dotify init
dotify auth librespot
dotify env doctor --verbose
```

Spotify web cookies and Librespot authorization are separate. The first
`dotify auth librespot` run opens Spotify OAuth in the browser, waits for the
local callback at `127.0.0.1:5588`, and saves reusable credentials to
`~/.dotify/librespot_credentials.json`. The file is created with user-only
permissions. Dotify does not silently switch to the `web` session if this
authorization is missing or rejected.

Instead of exporting `cookies.txt` manually, Dotify can import only Spotify's
required `sp_dc` cookie from a browser where you are already signed in:

```bash
dotify auth web --browser auto
dotify auth web --browser chrome --profile "Profile 2" --force
```

`auto` checks supported local browsers in order. The importer does not copy
cookies belonging to other sites, writes the Netscape file atomically with
user-only permissions, and leaves an existing file untouched when extraction
fails. macOS may request Keychain access; Safari extraction may additionally
require Full Disk Access for the terminal application.

To refresh the cookie immediately before one download, use:

```bash
dotify --cookies-from-browser auto "SPOTIFY_URL"
dotify --cookies-from-browser chrome --browser-profile "Profile 2" "SPOTIFY_URL"
```

The same behavior can be made persistent with `cookies_from_browser` in the
configuration file. Because this reads the browser cookie store on every run,
leave it as `null` if you prefer explicit refreshes through `dotify auth web`.

`dotify init` asks for the language, output directory, audio-quality profile,
cookie and optional WVD paths, TUI preference, and delay between downloads. It
writes `~/.dotify/config.ini` and does not replace an existing configuration
without confirmation or `--force`.

For unattended setup:

```bash
dotify init --non-interactive --language tr
dotify init --non-interactive --force --config-path /path/to/config.ini
```

### From this repository

This checkout is the source of truth. Install it in editable mode so commands
inside the virtual environment import the `dotify/*.py` files from this working
tree directly:

```bash
git clone https://github.com/ashfiexe/dotify.git
cd dotify
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev,librespot]"
```

If `uv` is installed, the equivalent setup is:

```bash
uv sync --extra dev --extra librespot
source .venv/bin/activate
```

Then run either form:

```bash
dotify --help
python -m dotify --help
```

The `dotify` executable in `.venv/bin/` is only the command entry point for
this editable project. It is not a second copy of the application. Changes to
the repository's Python files are used on the next run; reinstalling is usually
needed only after dependency or packaging metadata changes.

## Quick start

The `download` subcommand is optional. `dotify URL` and
`dotify download URL` are equivalent.

Authorize the default Librespot session once before the first download:

```bash
dotify auth librespot
dotify auth status
```

```bash
# Track
dotify "https://open.spotify.com/track/18gqCQzqYb0zvurQPlRkpo"

# Album
dotify "https://open.spotify.com/album/0r8D5N674HbTXlR3zNxeU1"

# Playlist
dotify "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M"

# Show or individual podcast episode
dotify "https://open.spotify.com/show/SPOTIFY_ID"
dotify "https://open.spotify.com/episode/SPOTIFY_ID"

# Explicit subcommand form
dotify download "https://open.spotify.com/track/SPOTIFY_ID"
```

An artist URL asks which category to process. For non-interactive use, select
the category explicitly:

```bash
dotify --auto-media-option artist-top-tracks "https://open.spotify.com/artist/SPOTIFY_ID"
dotify --auto-media-option artist-albums "https://open.spotify.com/artist/SPOTIFY_ID"
dotify --auto-media-option artist-singles "https://open.spotify.com/artist/SPOTIFY_ID"
dotify --auto-media-option artist-compilations "https://open.spotify.com/artist/SPOTIFY_ID"
dotify --auto-media-option artist-videos "https://open.spotify.com/artist/SPOTIFY_ID"
```

`artist-albums`, `artist-singles`, and `artist-compilations` are separate
categories; an artist URL does not automatically mean "the full discography."

## Terminal UI and languages

Use `--tui` to select items from multi-item URLs and display a live queue:

```bash
dotify --tui --language tr "SPOTIFY_URL"
dotify --no-tui "SPOTIFY_URL"
```

For playlist URLs the TUI first offers `Download all tracks` and `Choose
tracks`. Download-all mode streams playlist entries directly instead of
preparing the full track-selection list. Choose-tracks mode fetches metadata
only and uses stable numeric selections. Stream URLs, audio keys, and Widevine
licenses are resolved only when an item is about to download. Existing output
and persistent-queue checks run first, so unselected or already completed
items do not consume a license request. The TUI displays byte progress, speed,
and ETA when the selected transfer backend reports them. `aria2c` and `curl`
currently report an indeterminate state followed by the final transferred
size.

Supported languages are `en` and `tr`. `auto` checks `DOTIFY_LANGUAGE`, then
the system locale, and falls back to English:

```bash
dotify --language en "SPOTIFY_URL"
DOTIFY_LANGUAGE=tr dotify "SPOTIFY_URL"
```

See [TUI and localization](docs/TUI_AND_LOCALIZATION.md) for more detail.

## Common commands

### Quality and output

Audio quality is a comma-separated priority list. Dotify tries entries in
order until it finds one that the current session can play.

By default, Dotify may use an implicit Web/AAC fallback after a Librespot audio
key rejection. Add `--strict-audio-quality` to restrict resolution to the
explicit comma-separated list. The TUI completion line and summary report the
actual codec/container; when fallback occurs, a separate table reports the
requested qualities, actual format, and final file path.

```bash
dotify --audio-quality vorbis-high,aac-medium "SPOTIFY_URL"
dotify --audio-quality flac-flac-24,flac-flac,aac-high "SPOTIFY_URL"
dotify --strict-audio-quality --audio-quality vorbis-high,vorbis-medium "SPOTIFY_URL"
dotify --output "/path/to/music" "SPOTIFY_URL"
dotify --synced-lyrics-only "SPOTIFY_URL"
dotify --dry-run "SPOTIFY_URL"
```

Supported audio-quality identifiers:

| Identifier | Container/output | Nominal quality | Premium |
|---|---|---:|:---:|
| `vorbis-low` | Ogg Vorbis | 96 kbps | No |
| `vorbis-medium` | Ogg Vorbis | 160 kbps | No |
| `vorbis-high` | Ogg Vorbis | 320 kbps | Yes |
| `aac-medium` | M4A/AAC | 128 kbps | No |
| `aac-high` | M4A/AAC | 256 kbps | Yes |
| `flac-flac` | FLAC | Lossless | Yes |
| `flac-mp4` | MP4-FLAC to FLAC | Lossless | Yes |
| `flac-flac-24` | FLAC | 24-bit lossless | Yes |
| `flac-mp4-24` | MP4-FLAC to FLAC | 24-bit lossless | Yes |

### Video

Use `--prefer-video` to choose an associated music video or a video podcast
episode when Spotify reports one. Without it, Dotify prefers audio unless the
track itself is video media.

```bash
dotify --prefer-video "SPOTIFY_URL"
dotify --prefer-video --video-format webm --video-resolution 1080p "SPOTIFY_URL"
dotify --auto-media-option artist-videos "https://open.spotify.com/artist/SPOTIFY_ID"
```

Valid resolutions are `144p`, `240p`, `360p`, `480p`, `576p`, `720p`, and
`1080p`. Valid video formats are `mp4`, `webm`, and `ask`.

### Batch and automation

```bash
# Multiple URLs
dotify "URL1" "URL2" "URL3"

# One URL per line
dotify --read-urls-as-txt urls.txt
dotify -r urls.txt

# Non-interactive artist or liked-tracks selection
dotify --auto-media-option artist-albums "ARTIST_URL"
dotify --auto-media-option liked-tracks

# Skip already registered media with a persistent database
dotify --database-path ~/.dotify/downloads.db "SPOTIFY_URL"
```

### Audio transfer and remux modes

```bash
dotify --audio-download-mode ytdlp "SPOTIFY_URL"  # default
dotify --audio-download-mode aria2c "SPOTIFY_URL" # requires aria2c
dotify --audio-download-mode curl "SPOTIFY_URL"   # requires curl

dotify --audio-remux-mode ffmpeg "SPOTIFY_URL"   # default
dotify --audio-remux-mode mp4box "SPOTIFY_URL"
dotify --audio-remux-mode mp4decrypt "SPOTIFY_URL"
```

`--audio-download-mode` changes only how an already resolved Spotify stream is
transferred. It does not change the media provider.

### Output templates

```bash
dotify \
  --album-folder-template "{album_artist}/{album} [{date:%Y}]" \
  --single-disc-file-template "{track:02d} - {title}" \
  "SPOTIFY_URL"
```

Available values include:

- Media: `{title}`, `{artist}`, `{album}`, `{album_artist}`, `{track}`,
  `{track_total}`, `{disc}`, `{disc_total}`, `{date}`, `{label}`, `{isrc}`,
  `{media_id}`, `{media_type}`, `{rating}`
- Credits: `{composer}`, `{producer}`, `{publisher}`
- Playlist: `{playlist_title}`, `{playlist_artist}`, `{playlist_track}`,
  `{playlist_id}`

Templates use Python format syntax, so compatible values can include format
specifiers such as `{track:02d}` and `{date:%Y}`.

## Configuration

The default configuration file is `~/.dotify/config.ini` on all supported
platforms. CLI options take precedence over values in that file. Use
`--config-path` for another file or `--no-config-file` for one run without it.

The file uses a single `[dotify]` section and option names without leading
dashes:

```ini
[dotify]
language = auto
tui = false
cookies_path = /home/user/.dotify/cookies.txt
cookies_from_browser = null
browser_profile = null
librespot_credentials_path = /home/user/.dotify/librespot_credentials.json
wvd_path = /home/user/.dotify/keys/device.wvd
output = ./Spotify
temp = .
session_type = librespot
audio_quality = vorbis-medium
strict_audio_quality = false
audio_download_mode = ytdlp
audio_remux_mode = ffmpeg
video_format = mp4
video_resolution = 1080p
wait_interval = 10
widevine_retries = 2
widevine_backoff = 60
widevine_max_wait = 120
widevine_request_interval = 0
queue_state_path = /home/user/.dotify/queue.json
resume = true
log_level = INFO
```

The shown values are CLI defaults. The guided initializer intentionally uses
a more convenient first-run profile: the current directory's `Spotify`
folder, `~/.dotify/temp`, balanced `vorbis-high,aac-medium` quality, TUI
enabled, and a one-second wait.

Use `dotify download --help` as the authoritative list of configurable
options.

## Environment commands

```bash
dotify env setup
dotify env setup --create-placeholders
dotify env doctor
dotify env doctor --verbose
dotify env doctor --json
dotify env check config
dotify env check cookies
dotify env check wvd
dotify env check librespot
dotify env check ffmpeg
dotify env check python
dotify env paths
```

`env doctor --verbose` also reports optional `aria2c`, `mp4box`,
`mp4decrypt`, and `packager` binaries. Preflight checks run before downloads by
default; `--skip-preflight` bypasses them for debugging but does not make a
missing runtime dependency usable.

Download commands return exit code `0` when all items succeed or are
intentionally skipped, `1` when setup, authentication, URL, API, dependency,
or download errors occur, and `2` for invalid command usage. User-facing error
messages hide tracebacks by default; add `--exceptions` when debugging.

## Troubleshooting

| Symptom | Check |
|---|---|
| `dotify` is not found | Activate `.venv`, use `.venv/bin/dotify`, or run `python -m dotify` |
| Cookies or `sp_dc` error | Export a current Netscape-format cookie file from a logged-in Spotify session and check `--cookies-path` |
| Browser cookie import cannot find `sp_dc` | Sign in at `open.spotify.com` in the selected browser, close private/incognito mode, then run `dotify auth web --browser chrome --force`; on macOS approve Keychain access if requested |
| Librespot credentials are missing | Run `dotify auth librespot`; Spotify web cookies do not replace this OAuth step |
| Librespot returns `403` for a Premium account | Run `dotify auth librespot --force` to replace the stored authorization; Dotify will report the error instead of switching to Web |
| Librespot reports `Audio key error, code: 1` | This Spotify-side rejection can affect individual OAuth/Premium sessions. When a valid WVD is configured, Dotify retries that item with Spotify's protected AAC/Web stream; otherwise use `--session-type web --wvd-path /path/to/device.wvd` |
| Widevine license returns `429` | Dotify honors `Retry-After`, serializes license calls, and applies bounded retries. Avoid parallel commands. Tune conservatively with `--widevine-retries`, `--widevine-backoff`, `--widevine-max-wait`, and `--widevine-request-interval`; these controls reduce request pressure but cannot bypass Spotify's limit |
| `pyfreedom` module is missing | Install `dotify-cli[librespot]` or select another supported `--session-type` |
| FFmpeg error | Install FFmpeg, add it to `PATH`, or set `--ffmpeg-path` |
| Requested quality is unavailable | Check account tier, session type, WVD path, market availability, and the fallback list |
| Video decrypt/remux fails | Run `dotify env doctor --verbose` and verify FFmpeg plus the selected MP4/WebM decryption tools |
| Need diagnostic detail | Run with `--exceptions --log-level DEBUG --log-file dotify.log` |

## Python API and plugins

Dotify exposes a reusable async API that does not depend on Click configuration:

```python
import asyncio
from pathlib import Path

from dotify import DotifyClient, DotifySettings


async def main() -> None:
    settings = DotifySettings(
        output_path="./Music",
        audio_quality=("vorbis-high", "aac-medium"),
        widevine_retries=2,
        widevine_request_interval=5,
        queue_state_path=str(Path.home() / ".dotify" / "queue.json"),
        resume=True,
    )
    cookies = Path.home() / ".dotify" / "cookies.txt"

    async with await DotifyClient.from_cookies(str(cookies), settings) as client:
        result = await client.download("https://open.spotify.com/track/SPOTIFY_ID")
        print(result.paths)


asyncio.run(main())
```

See [Python API](docs/PUBLIC_API.md) and [plugins](docs/PLUGINS.md) for the
supported surface and extension protocols.

## Development

After installing the checkout in editable mode:

```bash
pytest -m "not performance"
pytest -m performance
ruff check dotify tests
python -m build
```

Architecture and contribution guidance is in [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Dotify is distributed under the [MIT License](LICENSE).
