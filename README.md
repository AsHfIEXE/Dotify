<div align="center">

  ![GitHub](https://img.shields.io/badge/GitHub-181717.svg?style=for-the-badge&logo=GitHub&logoColor=white)
  ![GitHub top language](https://img.shields.io/github/languages/top/AsHfIEXE/dotify?style=for-the-badge)
  ![GitHub Downloads](https://img.shields.io/github/downloads/ashfiexe/dotify/total?style=for-the-badge&logo=GitHub&logoColor=white)
  ![GitHub last commit](https://img.shields.io/github/last-commit/AsHfIEXE/dotify/main?style=for-the-badge)
  ![GitHub Repo stars](https://img.shields.io/github/stars/AsHfIEXE/dotify?style=for-the-badge)
  ![PyPI Version](https://img.shields.io/pypi/v/dotify?style=for-the-badge&logo=PyPI&logoColor=white)
  ![Python Version](https://img.shields.io/pypi/pyversions/dotify?style=for-the-badge&logo=Python&logoColor=white)
  ![License](https://img.shields.io/github/license/AsHfIEXE/Dotify?style=for-the-badge)

  # 🎵 Dotify - Spotify Music Downloader

  **A highly configurable Spotify CLI downloader for tracks, playlists, podcasts, and music videos.**  
  **Build and manage your offline music libraries with synced lyrics, cover art, and full metadata control.**  
  **Designed for music enthusiasts, Python developers, and automated media library workflows.**

  [Installation](#-installation) • [Quick Start](#-quick-start) • [Features](#-features) • [Documentation](#-documentation)

</div>

---

## ✨ Features

### 🎧 Content Support
- **🎵 Songs** - Download in AAC 128kbps or AAC 256kbps (Premium)
- **📻 Podcasts** - Download in Vorbis or AAC format
- **🎬 Videos** - Download music videos and podcast videos (Premium)
- **📝 Lyrics** - Download synced lyrics in `.lrc` format
- **👨‍🎤 Artists** - Download entire discographies
- **📚 Playlists** - Download complete playlists with metadata

### 🛠️ Smart Environment Management
- **🔧 Auto Setup** - One-command environment preparation
- **🩺 Health Checks** - Comprehensive system diagnostics
- **🔍 Error Detection** - Clear, actionable error messages
- **📋 Configuration** - Automated config file management
- **🎯 Preflight Validation** - Checks before every operation

### 🎨 Advanced Features
- **🏷️ Metadata** - Complete tag preservation and customization
- **📁 Organization** - Flexible folder/file naming templates
- **⚡ Performance** - Multiple download modes (ytdlp, aria2c)
- **🔄 Remuxing** - Support for FFmpeg, MP4Box, mp4decrypt
- **📊 Quality Control** - Multiple audio quality options

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+** installed
- **FFmpeg** in system PATH
- **Spotify cookies** (Netscape format)
- **Widevine key** (`.wvd` file) for AAC decryption

### Installation

```bash
# Install Dotify
pip install dotify-cli

# Run automatic setup
dotify env setup

# Verify your environment
dotify env doctor
```

### First-Time Setup

```bash
# 1. Create placeholder files for reference
dotify env setup --create-placeholders

# 2. Get your Spotify cookies
#    - Install "Get cookies.txt LOCALLY" extension
#    - Go to open.spotify.com and log in
#    - Export cookies to ~/.dotify/cookies.txt

# 3. Get your Widevine key (for AAC decryption)
#    - Use KeyDive on an Android device
#    - Extract device.wvd
#    - Place it in ~/.dotify/keys/device.wvd

# 4. Verify everything is ready
dotify env doctor
```

### Download Your First Track

```bash
# Download a single track
dotify "https://open.spotify.com/track/18gqCQzqYb0zvurQPlRkpo"

# Download an entire album
dotify "https://open.spotify.com/album/0r8D5N674HbTXlR3zNxeU1"

# Download a playlist
dotify "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M"
```

---

## 📚 Environment Commands

Dotify includes powerful environment management tools:

### 🔧 Setup

```bash
dotify env setup
```

Automatically creates:
- Configuration directory (`~/.dotify/`)
- Keys directory (`~/.dotify/keys/`)
- Temp directory (`~/.dotify/temp/`)
- Logs directory (`~/.dotify/logs/`)
- Default configuration file

**Options:**
- `--create-placeholders` - Create example files for cookies and WVD

### 🩺 Doctor

```bash
dotify env doctor
```

Comprehensive health check that verifies:
- ✅ Configuration directory
- ✅ Cookies file
- ✅ Widevine key
- ✅ FFmpeg installation
- ✅ Python version
- ✅ Optional dependencies

**Options:**
- `--verbose` - Show detailed output including optional checks
- `--json` - Output results in JSON format

### 📁 Paths

```bash
dotify env paths
```

Displays all Dotify-related paths:
- Config directory and file
- Keys directory
- Default cookies and WVD paths
- Temp and logs directories
- Database file location

### 🔍 Check

```bash
dotify env check [check_name]
```

Run specific health checks:
- `config` - Configuration directory
- `cookies` - Cookies file
- `wvd` - Widevine key
- `ffmpeg` - FFmpeg installation
- `python` - Python version

---

## 🎯 Usage Examples

### Basic Downloads

```bash
# Download a song
dotify "https://open.spotify.com/track/..."

# Download an album
dotify "https://open.spotify.com/album/..."

# Download a playlist
dotify "https://open.spotify.com/playlist/..."

# Download an artist's discography
dotify "https://open.spotify.com/artist/..."
```

### Advanced Options

```bash
# Download with custom quality
dotify "URL" --audio-quality aac-high

# Download to specific directory
dotify "URL" --output "/path/to/music"

# Download with custom template
dotify "URL" --album-folder-template "{artist}/{album} - {year}"

# Download only lyrics
dotify "URL" --synced-lyrics-only

# Download with verbose logging
dotify "URL" --log-level DEBUG
```

### Video Downloads

```bash
# Download music video
dotify "URL" --download-music-videos

# Download podcast video
dotify "URL" --download-podcast-videos

# Choose video format
dotify "URL" --video-format webm
```

### Batch Operations

```bash
# Download from text file
dotify --read-urls-as-txt urls.txt

# Download multiple URLs
dotify "URL1" "URL2" "URL3"

# Download with custom wait interval
dotify "URL" --wait-interval 10
```

---

## ⚙️ Configuration

### Config File Location

- **Linux/macOS**: `~/.dotify/config.ini`
- **Windows**: `%USERPROFILE%\.dotify\config.ini`

### Common Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `cookies_path` | Path to cookies file | `~/.dotify/cookies.txt` |
| `wvd_path` | Path to Widevine key | `~/.dotify/keys/device.wvd` |
| `output_path` | Output directory | `Spotify` |
| `audio_quality` | Audio quality priority | `aac-medium` |
| `wait_interval` | Wait between downloads (seconds) | `5` |
| `log_level` | Logging level | `INFO` |

### Template Variables

Customize your file organization with these variables:

- **Album**: `{album}`, `{album_artist}`, `{year}`, `{label}`
- **Track**: `{title}`, `{track}`, `{disc}`, `{artist}`
- **Metadata**: `{isrc}`, `{composer}`, `{copyright}`, `{genre}`
- **Playlist**: `{playlist_title}`, `{playlist_artist}`, `{playlist_track}`

### Example Templates

```ini
# Album organization
album_folder_template = {album_artist}/{album} [{year}]
single_disc_file_template = {track:02d} - {title}
multi_disc_file_template = {disc}-{track:02d} - {title}

# Podcast organization
podcast_folder_template = Podcasts/{album}
podcast_file_template = {track:02d} - {title}

# Playlist organization
playlist_file_template = Playlists/{playlist_artist}/{playlist_title}
```

---

## 🔧 Troubleshooting

### Common Issues

#### ❌ "Cookies file not found"

**Solution:**
```bash
# Check where Dotify expects cookies
dotify env paths

# Verify cookies file exists
ls ~/.dotify/cookies.txt

# Run diagnostics
dotify env doctor
```

#### ❌ "Widevine key not found"

**Solution:**
```bash
# Check WVD location
dotify env check wvd

# For Vorbis downloads (no WVD needed)
dotify "URL" --disable-wvd
```

#### ❌ "FFmpeg not found"

**Solution:**
```bash
# Check FFmpeg installation
dotify env check ffmpeg

# Install FFmpeg:
# Windows: https://www.animemusic.info/2024/02/ffmpeg-builds-static-shared.html
# Linux: https://johnvansickle.com/ffmpeg/
```

#### ❌ "Authentication failed"

**Solution:**
```bash
# Export fresh cookies from open.spotify.com
# Replace old cookies.txt
dotify env doctor
```

### Getting Help

```bash
# Full diagnostic
dotify env doctor --verbose

# JSON output for automation
dotify env doctor --json

# Check specific component
dotify env check ffmpeg

# View all paths
dotify env paths
```

---

## 📖 Advanced Usage

### Preflight Checks

Dotify automatically runs preflight checks before downloads:

```bash
# Automatic checks (default)
dotify "URL"

# Skip preflight checks (advanced users)
dotify "URL" --skip-preflight
```

### Error Handling

Dotify provides helpful error messages with fix suggestions:

```bash
# Example error output:
# [X] Cookies File: Cookies file not found
#   Fix: Place cookies.txt in ~/.dotify or use --cookies-path
#
# Run 'dotify env doctor' for details
```

### Quality Options

```bash
# AAC qualities (Premium)
--audio-quality aac-medium    # 128kbps
--audio-quality aac-high      # 256kbps

# Vorbis qualities
--audio-quality vorbis-high   # 320kbps
--audio-quality vorbis-medium # 160kbps
--audio-quality vorbis-low    # 96kbps
```

### Download Modes

```bash
# ytdlp (default)
--download-mode ytdlp

# aria2c (faster, requires aria2c)
--download-mode aria2c
```

### Remux Modes

```bash
# FFmpeg (default)
--audio-remux-mode ffmpeg
--video-remux-mode ffmpeg

# MP4Box
--audio-remux-mode mp4box

# mp4decrypt
--audio-remux-mode mp4decrypt
```

---

## 🌟 What's New

### Environment Layer (v1.9.8+)

- **🔧 Auto Setup** - One-command environment preparation
- **🩺 Health Checks** - Comprehensive system diagnostics
- **📋 Smart Configuration** - Automated config management
- **🎯 Preflight Validation** - Checks before every operation
- **💡 Better Errors** - Clear, actionable error messages
- **📁 Path Management** - Centralized path handling

### Key Improvements

- **Self-Aware** - Dotify knows its own structure and requirements
- **User-Friendly** - Clear guidance for setup and troubleshooting
- **Professional** - Production-ready error handling and diagnostics
- **Maintainable** - Clean separation of concerns

---

## 📊 Supported Content

| Type | Formats | Quality | Notes |
|------|---------|---------|-------|
| **Songs** | AAC, Vorbis | 96-320kbps | AAC requires Premium + WVD |
| **Podcasts** | AAC, Vorbis | 96-320kbps | Vorbis works without Premium |
| **Music Videos** | MP4, WebM | Up to 1080p | Requires Premium |
| **Podcast Videos** | MP4, WebM | Up to 1080p | Requires Premium |
| **Lyrics** | LRC | Synced | Automatic with tracks |

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Spotify** for the amazing music platform
- **KeyDive** for Widevine key extraction
- **yt-dlp** for download functionality
- **FFmpeg** for media processing
- All contributors and users of Dotify

---

## 📞 Support

- **Email**: salahin0ashfi@gmail.com
- **Discord**: [Join our Discord](https://discord.gg/YSv62BvCtS)
- **Issues**: [Report bugs on GitHub](https://github.com/AsHfIEXE/Dotify/issues)

---

<div align="center">

  **⭐ If you find this project helpful, consider giving it a star! ⭐**

  Made with ❤️ by [@AsHfIEXE](https://github.com/AsHfIEXE)

</div>