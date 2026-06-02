<div align="center">

[![GitHub](https://img.shields.io/badge/GitHub-181717.svg?style=for-the-badge&logo=GitHub&logoColor=white)](https://github.com/AsHfIEXE/Dotify)
[![GitHub top language](https://img.shields.io/github/languages/top/AsHfIEXE/dotify?style=for-the-badge)](https://github.com/AsHfIEXE/Dotify)
[![PyPI Downloads](https://img.shields.io/pypi/dm/dotify-cli?style=for-the-badge&color=blue&label=Downloads)](https://pypi.org/project/dotify-cli/)
[![GitHub Downloads](https://img.shields.io/github/downloads/AsHfIEXE/dotify/total?style=for-the-badge&logo=GitHub&logoColor=white)](https://github.com/AsHfIEXE/Dotify)
[![GitHub last commit](https://img.shields.io/github/last-commit/AsHfIEXE/dotify/main?style=for-the-badge)](https://github.com/AsHfIEXE/Dotify)
[![GitHub Repo stars](https://img.shields.io/github/stars/AsHfIEXE/dotify?style=for-the-badge&cacheSeconds=60)](https://github.com/AsHfIEXE/Dotify)
[![PyPI Version](https://img.shields.io/pypi/v/dotify?style=for-the-badge&logo=PyPI&logoColor=white)](https://pypi.org/project/dotify-cli/)
[![Python Version](https://img.shields.io/pypi/pyversions/dotify?style=for-the-badge&logo=Python&logoColor=white)](https://pypi.org/project/dotify-cli/)
[![License](https://img.shields.io/github/license/AsHfIEXE/dotify?style=for-the-badge)](https://github.com/AsHfIEXE/Dotify)

# 🎵 Dotify

**A highly configurable Spotify CLI downloader for tracks, albums, playlists, podcasts, and music videos.**  
Build permanent offline music libraries with lossless FLAC, full metadata, cover art, and synced lyrics.  
Designed for music enthusiasts, Python developers, and automated media library workflows.

[Installation](#-installation) • [Quick Start](#-quick-start) • [Features](#-features) • [Documentation](https://github.com/AsHfIEXE/Dotify/wiki)

</div>

---

## 📦 Installation

**Requires Python 3.10+**

```bash
pip install dotify-cli --upgrade
```

Set up your environment in one command:

```bash
dotify env setup    # creates ~/.dotify/ with all required dirs
dotify env doctor   # verifies dependencies and credentials
```

> **New to Dotify?** See the full [Installation Guide](https://github.com/AsHfIEXE/Dotify/wiki/Installation) for FFmpeg, Aria2c, and Widevine key setup.

---

## 🚀 Quick Start

```bash
# Download a track
dotify "https://open.spotify.com/track/18gqCQzqYb0zvurQPlRkpo"

# Download an album
dotify "https://open.spotify.com/album/0r8D5N674HbTXlR3zNxeU1"

# Download a playlist
dotify "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M"

# Download an artist's full discography
dotify "https://open.spotify.com/artist/..."

# Download in lossless FLAC (Premium required)
dotify --audio-quality flac-flac,aac-high "https://open.spotify.com/track/..."
```

For Premium quality (FLAC / AAC 256kbps), you'll need Spotify cookies and a Widevine key.  
See [Authentication](https://github.com/AsHfIEXE/Dotify/wiki/Authentication) for the full setup walkthrough.

---

## ✨ Features

### 🎧 Content Support

| Type | Formats | Quality | Notes |
|---|---|---|---|
| Songs | Vorbis | 96–320kbps | No extra tools required |
| Songs | AAC | 128–256kbps | Requires `.wvd` + Premium |
| Songs | FLAC / 24-bit FLAC | Lossless | L1-certified `.wvd` + Premium |
| Podcasts | Vorbis / AAC | 96–320kbps | Free + Premium |
| Music Videos | MP4 (H.264), WebM | Up to 1080p | Requires `.wvd` + FFmpeg + Premium |
| Podcast Videos | MP4, WebM | Up to 1080p | Requires FFmpeg / MP4Box |
| Lyrics | LRC (synced) | — | Downloaded automatically |

### 🛠️ Smart Environment Management

- **`dotify env setup`** — One-command environment scaffolding
- **`dotify env doctor`** — Comprehensive health checks with actionable fixes
- **`dotify env paths`** — Inspect all Dotify-related file locations
- **`dotify env check [component]`** — Check a specific dependency (`ffmpeg`, `cookies`, `wvd`, ...)

### 🎨 Advanced Capabilities

- **Flexible templates** — Customize folder and file names with `{artist}`, `{album}`, `{year}`, `{isrc}`, and more
- **Quality fallback chains** — `flac-flac-24,flac-flac,aac-high` tries each in order automatically
- **Multiple download modes** — `ytdlp` (default) or `aria2c` for parallel multi-connection downloads
- **Multiple remux modes** — FFmpeg, MP4Box, or mp4decrypt
- **Preflight validation** — Checks credentials and dependencies before every download
- **Batch downloads** — Pass multiple URLs or a `.txt` file with `-r`

---

## ⚙️ Configuration

Config file is auto-created at `~/.dotify/config.ini` (Linux/macOS) or `%USERPROFILE%\.dotify\config.ini` (Windows).

| Key | Description | Default |
|---|---|---|
| `cookies_path` | Path to Spotify cookies file | `~/.dotify/cookies.txt` |
| `wvd_path` | Path to Widevine `.wvd` key | `~/.dotify/keys/device.wvd` |
| `output_path` | Root output directory | `Spotify` |
| `audio_quality` | Quality priority list | `aac-medium` |
| `wait_interval` | Seconds between downloads | `5` |
| `log_level` | Logging verbosity | `INFO` |

### Audio Quality Options

| String | Format | Bitrate / Depth | Requires Premium |
|---|---|---|---|
| `flac-flac-24` | FLAC | 24-bit lossless | ✅ |
| `flac-flac` | FLAC | 16-bit lossless | ✅ |
| `aac-high` | AAC | 256kbps | ✅ |
| `vorbis-high` | Vorbis | 320kbps | ✅ |
| `aac-medium` | AAC | 128kbps | ❌ |
| `vorbis-medium` | Vorbis | 160kbps | ❌ |
| `vorbis-low` | Vorbis | 96kbps | ❌ |

### Template Variables

| Scope | Variables |
|---|---|
| Album | `{album}`, `{album_artist}`, `{year}`, `{label}` |
| Track | `{title}`, `{track}`, `{disc}`, `{artist}` |
| Metadata | `{isrc}`, `{composer}`, `{copyright}`, `{genre}` |
| Playlist | `{playlist_title}`, `{playlist_artist}`, `{playlist_track}` |

```bash
# Example: organized library structure
dotify "URL" \
  --album-folder-template "{album_artist}/{album} [{year}]" \
  --single-disc-file-template "{track:02d} - {title}"
```

See the full [Configuration Reference](https://github.com/AsHfIEXE/Dotify/wiki/Configuration) for all options.

---

## 🔑 Authentication Setup

To access Premium quality content:

1. **Get Spotify cookies** — Export from [open.spotify.com](https://open.spotify.com) using *"Get cookies.txt LOCALLY"* (Chrome/Edge) or *"Export Cookies"* (Firefox). Save to `~/.dotify/cookies.txt`.

2. **Get a Widevine key** — Use [KeyDive](https://github.com/hyugogirubato/KeyDive) on an Android device to extract `device.wvd`. Place it at `~/.dotify/keys/device.wvd`.

3. **Verify** — Run `dotify env doctor`.

```bash
dotify env setup --create-placeholders  # scaffolds empty files so you know what to fill in
dotify env doctor                       # confirms everything is ready
```

Full walkthrough: [Authentication](https://github.com/AsHfIEXE/Dotify/wiki/Authentication)

---

## 📖 Usage Reference

### Basic

```bash
dotify "https://open.spotify.com/track/..."
dotify "https://open.spotify.com/album/..."
dotify "https://open.spotify.com/playlist/..."
dotify "https://open.spotify.com/artist/..."
```

### Quality & Output

```bash
dotify "URL" --audio-quality flac-flac-24,flac-flac,aac-high
dotify "URL" --output "/path/to/music"
dotify "URL" --synced-lyrics-only
```

### Video Downloads

```bash
dotify "URL" --download-music-videos
dotify "URL" --download-podcast-videos
dotify "URL" --video-format webm
```

### Batch & Automation

```bash
dotify --read-urls-as-txt urls.txt
dotify "URL1" "URL2" "URL3"
dotify "URL" --wait-interval 10 --log-level DEBUG
```

### Download Modes

```bash
dotify "URL" --download-mode ytdlp    # default
dotify "URL" --download-mode aria2c   # faster (requires aria2c)
```

---

## 🔧 Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `403 Forbidden` / `Unauthorized` | Cookies expired | Re-export from incognito, replace `~/.dotify/cookies.txt` |
| Getting 128kbps despite `aac-high` | Free account or missing `.wvd` | Check `dotify env doctor` |
| `ffmpeg not found` | Not in PATH | Install FFmpeg or set `ffmpeg_path` in config |
| `dotify` not found after install | Scripts dir not in PATH | Run `python -m dotify "URL"` or reinstall with `--user` |
| Video download fails | `mp4decrypt`/`MP4Box` missing | Install Bento4 + GPAC, verify with `mp4decrypt --version` |
| Slow downloads | Aria2c not installed | Install aria2c, use `--download-mode aria2c` |

```bash
dotify env doctor --verbose   # full diagnostic
dotify env doctor --json      # machine-readable output
dotify env check ffmpeg       # check a specific component
dotify env paths              # inspect all file paths
```

Full FAQ: [Troubleshooting](https://github.com/AsHfIEXE/Dotify/wiki/Troubleshooting)

---

## 📚 Documentation

Full documentation is available in the [Wiki](https://github.com/AsHfIEXE/Dotify/wiki):

| Page | Description |
|---|---|
| [Installation](https://github.com/AsHfIEXE/Dotify/wiki/Installation) | pip install, FFmpeg, Aria2c, Bento4 setup |
| [Environment Setup](https://github.com/AsHfIEXE/Dotify/wiki/Environment-Setup) | `env setup`, `env doctor`, v1→v2 migration |
| [Authentication](https://github.com/AsHfIEXE/Dotify/wiki/Authentication) | Cookies, KeyDive, Widevine `.wvd` |
| [Basic Usage](https://github.com/AsHfIEXE/Dotify/wiki/Basic-Usage) | Tracks, albums, playlists, artists |
| [Advanced Usage](https://github.com/AsHfIEXE/Dotify/wiki/Advanced-Usage) | Templates, video, lyrics-only, batch |
| [Audio Quality Reference](https://github.com/AsHfIEXE/Dotify/wiki/Audio-Quality-Reference) | All format strings and priority examples |
| [Configuration](https://github.com/AsHfIEXE/Dotify/wiki/Configuration) | Full `config.ini` key reference |
| [Dependencies Explained](https://github.com/AsHfIEXE/Dotify/wiki/Dependencies-Explained) | FFmpeg, Aria2c, mp4decrypt, MP4Box, WVD |
| [Troubleshooting](https://github.com/AsHfIEXE/Dotify/wiki/Troubleshooting) | Error index and fixes |

---

## 🌟 Changelog Highlights

### v2.0.0 — Environment Management Layer
- `dotify env setup` — one-command environment scaffolding
- `dotify env doctor` — comprehensive health checks with actionable errors
- `dotify env paths` / `dotify env check` — granular diagnostics
- Centralized config at `~/.dotify/`, preflight validation before every run

### v1.9.8
- FLAC and 24-bit FLAC audio quality support
- Improved fallback quality chain handling

---

[![Star History Chart](https://api.star-history.com/svg?repos=ashfiexe/dotify&type=Date&theme=dark)](https://star-history.com/#ashfiexe/dotify&Date)

---

## 🤝 Contributing

Contributions are welcome!

1. Fork the repository
2. Create your feature branch: `git checkout -b feature/AmazingFeature`
3. Commit your changes: `git commit -m 'Add AmazingFeature'`
4. Push to the branch: `git push origin feature/AmazingFeature`
5. Open a Pull Request

---

## 🙏 Acknowledgments

- [Spotify](https://spotify.com) — for the platform
- [KeyDive](https://github.com/hyugogirubato/KeyDive) — Widevine key extraction
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — download engine
- [FFmpeg](https://ffmpeg.org) — media processing
- All contributors and users of Dotify

---

## 📝 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

📧 [salahin0ashfi@gmail.com](mailto:salahin0ashfi@gmail.com) · 💬 [Discord](https://discord.gg/YSv62BvCtS) · 🐛 [Issues](https://github.com/AsHfIEXE/Dotify/issues)

**⭐ If Dotify saves you time, a star goes a long way! ⭐**

Made with ❤️ by [@AsHfIEXE](https://github.com/AsHfIEXE)

</div>
