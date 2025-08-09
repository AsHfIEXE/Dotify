  
![](https://img.shields.io/badge/GitHub-181717.svg?style=for-the-badge&logo=GitHub&logoColor=white)![GitHub top language](https://img.shields.io/github/languages/top/AsHfIEXE/dotify?style=for-the-badge)
 ![GitHub Downloads )](https://img.shields.io/github/downloads/ashfiexe/dotify/total?style=for-the-badge&logo=GitHub&logoColor=white) ![](https://img.shields.io/github/last-commit/AsHfIEXE/dotify/main?display_timestamp=author&style=for-the-badge) ![GitHub Repo stars](https://img.shields.io/github/stars/ashfiexe/dotify?style=for-the-badge)![GitHub Discussions](https://img.shields.io/github/discussions/AsHfIEXE/dotify?style=for-the-badge)![PyPI Version](https://img.shields.io/pypi/v/dotify?style=for-the-badge&logo=GitHub&logoColor=white)
![Python Version](https://img.shields.io/pypi/pyversions/dotify?style=for-the-badge&logo=GitHub&logoColor=white)
![License](https://img.shields.io/github/license/AsHfIEXE/Dotify?style=for-the-badge&logo=GitHub&logoColor=white)
![GitHub stars](https://img.shields.io/github/stars/AsHfIEXE/Dotify?style=for-the-badge&logo=GitHub&logoColor=white)


# Dotify - Spotify Music Downloader 🎵

A powerful, command-line tool for downloading your favorite content—including songs, podcasts, and music videos—directly from Spotify.

## Features

*   **Songs**: Download songs in AAC 128kbps or in AAC 256kbps with an active premium subscription.
*   **Podcasts**: Download podcasts in Vorbis or AAC.
*   **Videos**: Download podcast videos and music videos with an active premium subscription.
*   **Synced Lyrics**: Download synced lyrics in `.lrc` format.
*   **Artist Support**: Download an entire discography by providing the artist's URL.
*   **Highly Customizable**: Extensive configuration options for advanced users.

## Prerequisites

*   **Python 3.10** or higher installed on your system.
*   The **cookies file** of your Spotify browser session in Netscape format.
    *   **Firefox**: Use the [Export Cookies](https://addons.mozilla.org/en-US/firefox/addon/export-cookies-txt/) extension.
    *   **Chromium-based Browsers**: Use the [Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc) extension.
*   **FFmpeg** on your system `PATH`.
    *   **Windows**: Download from [AnimMouse's FFmpeg Builds](https://www.animemusic.info/2024/02/ffmpeg-builds-static-shared.html).
    *   **Linux**: Download from [John Van Sickle's FFmpeg Builds](https://johnvansickle.com/ffmpeg/).
*   A **`.wvd` file**.
    *   A `.wvd` file contains Widevine keys from a device and is required to decrypt music videos and songs in AAC. The easiest method to obtain one is using [KeyDive](https://github.com/hyugogirubato/KeyDive), which extracts it from an Android device. `.wvd` files from emulated devices may not work.

### Notes

*   **Warning**: Some users have reported that Spotify suspended their accounts after using similar tools. Use it at your own risk.
*   The `.wvd` file is not required if you only plan on downloading podcasts. You can skip this prerequisite by using the `--disable-wvd` option.
*   FFmpeg is not required for downloading podcasts in Vorbis, but it is necessary for downloading podcasts in AAC.

### Optional Dependencies

The following tools are optional but required for specific features. Add them to your system's `PATH` or specify their paths using command-line arguments or the config file.

*   **MP4Box**: Required when setting `mp4box` as the remux mode.
*   **Shaka Packager**: Required when setting `webm` as the video format.
*   **mp4decrypt**: Required when setting `mp4box` or `mp4decrypt` as the remux mode for audio.
*   **aria2c**: Required when setting `aria2c` as the download mode.

## Installation

1.  Install the package `dotify` using pip:
    ```bash
    pip install dotify-cli
    ```
2.  Set up the cookies file.
    *   Move the cookies file to the directory where you'll run Dotify and rename it to `cookies.txt`.
    *   Alternatively, specify the path using the `--cookies-path` argument.
3.  Set up the `.wvd` file.
    *   Move the `.wvd` file to the directory where you'll run Dotify and rename it to `device.wvd`.
    *   Alternatively, specify the path using the `--wvd-path` argument.

## Usage

Run Dotify with the following command:

```bash
dotify [OPTIONS] URLS...
```

### Supported URL Types

*   Song
*   Album
*   Playlist
*   Podcast Episode
*   Podcast Show
*   Artist

### Examples

**Download a song**
```bash
dotify "https://open.spotify.com/track/18gqCQzqYb0zvurQPlRkpo"
```

**Download an album**
```bash
dotify "https://open.spotify.com/album/0r8D5N674HbTXlR3zNxeU1"
```

**List and select a related music video to download from a song**
```bash
dotify "https://open.spotify.com/track/0a0n6u6j3t6m0p4k0t0k0u0" --download-music-videos
```

**Download a podcast video**
```bash
dotify "https://open.spotify.com/episode/3kwxWnzGH8T6UY2Nq582zx" --download-podcast-videos
```

**Choose which albums to download from an artist**
```bash
dotify "https://open.spotify.com/artist/0gxyHStUsqpMadRV0Di1Qt"
```
*Interactive prompt controls:*
*   **Arrow keys**: Move selection
*   **Space**: Toggle selection
*   **Ctrl + A**: Select all
*   **Enter**: Confirm selection

## Configuration

Dotify can be configured using command-line arguments or a config file.

The config file is created automatically when you run Dotify for the first time at `~/.dotify/config.json` on Linux and `%USERPROFILE%\.dotify\config.json` on Windows.

Config file values can be overridden using command-line arguments.

| Command-line argument / Config file key | Description                                                   | Default value             |
| --------------------------------------- | ------------------------------------------------------------- | ------------------------- |
| `--wait-interval`, `-w` / `wait_interval` | Wait interval between downloads in seconds.                   | `5`                       |
| `--disable-wvd` / `disable_wvd`         | Disable Widevine decryption.                                  | `false`                   |
| `--download-music-videos` / `download_music_videos` | List and select a related music video to download from songs. | `false`                   |
| `--download-podcast-videos` / `download_podcast_videos` | Attempt to download the video version of podcasts.            | `false`                   |
| `--force-premium`, `-f` / `force_premium` | Force to detect the account as premium.                       | `false`                   |
| `--read-urls-as-txt`, `-r` / -          | Interpret URLs as paths to text files containing URLs.        | `false`                   |
| `--config-path` / -                     | Path to config file.                                          | `<home>/.dotify/config.json` |
| `--log-level` / `log_level`             | Log level.                                                    | `INFO`                    |
| `--no-exceptions` / `no_exceptions`     | Don't print exceptions.                                       | `false`                   |
| `--cookies-path` / `cookies_path`       | Path to cookies file.                                         | `cookies.txt`             |
| `--output-path`, `-o` / `output_path`   | Path to output directory.                                     | `Spotify`                 |
| `--temp-path` / `temp_path`             | Path to temporary directory.                                  | `temp`                    |
| `--wvd-path` / `wvd_path`               | Path to .wvd file.                                            | `device.wvd`              |
| `--aria2c-path` / `aria2c_path`         | Path to aria2c binary.                                        | `aria2c`                  |
| `--ffmpeg-path` / `ffmpeg_path`         | Path to ffmpeg binary.                                        | `ffmpeg`                  |
| `--mp4box-path` / `mp4box_path`         | Path to MP4Box binary.                                        | `mp4box`                  |
| `--mp4decrypt-path` / `mp4decrypt_path` | Path to mp4decrypt binary.                                    | `mp4decrypt`              |
| `--packager-path` / `packager_path`     | Path to Shaka Packager binary.                                | `packager`                |
| `--template-folder-album` / `template_folder_album` | Template folder for tracks that are part of an album.       | `{album_artist}/{album}`  |
| `--template-folder-compilation` / `template_folder_compilation` | Template folder for tracks that are part of a compilation album. | `Compilations/{album}`    |
| `--template-file-single-disc` / `template_file_single_disc` | Template file for tracks on a single-disc album.        | `{track:02d} {title}`     |
| `--template-file-multi-disc` / `template_file_multi_disc` | Template file for tracks on a multi-disc album.         | `{disc}-{track:02d} {title}` |
| `--template-folder-episode` / `template_folder_episode` | Template folder for podcast episodes.                     | `Podcasts/{album}`        |
| `--template-file-episode` / `template_file_episode` | Template file for music videos.                               | `{track:02d} {title}`     |
| `--template-folder-music-video` / `template_folder_music_video` | Template folder for music videos.                         | `{artist}/Unknown Album`  |
| `--template-file-music-video` / `template_file_music_video` | Template file for tracks not part of an album.            | `{title}`                 |
| `--template-file-playlist` / `template_file_playlist` | Template file for the M3U8 playlist.                        | `Playlists/{playlist_artist}/{playlist_title}` |
| `--date-tag-template` / `date_tag_template` | Date tag template.                                          | `%Y-%m-%dT%H:%M:%SZ`      |
| `--cover-size` / `cover_size`           | Cover size.                                                   | `extra-large`             |
| `--save-cover` / `save_cover`           | Save cover as a separate file.                                | `false`                   |
| `--save-playlist` / `save_playlist`     | Save a M3U8 playlist file when downloading a playlist.        | `false`                   |
| `--overwrite` / `overwrite`             | Overwrite existing files.                                     | `false`                   |
| `--exclude-tags` / `exclude_tags`       | Comma-separated tags to exclude.                              | `null`                    |
| `--truncate` / `truncate`               | Maximum length of the file/folder names.                      | `null`                    |
| `--audio-quality`, `-a` / `audio_quality` | Audio quality for songs and podcasts.                         | `aac-medium`              |
| `--download-mode`, `-d` / `download_mode` | Download mode for songs and podcasts.                         | `ytdlp`                   |
| `--remux-mode-audio` / `remux_mode_audio` | Remux mode for songs and podcasts.                            | `ffmpeg`                  |
| `--lrc-only`, `-l` / `lrc_only`         | Download only the synced lyrics.                              | `false`                   |
| `--no-lrc` / `no_lrc`                   | Don't download the synced lyrics.                             | `false`                   |
| `--video-format` / `video_format`       | Video format.                                                 | `mp4`                     |
| `--remux-mode-video` / `remux_mode_video` | Remux mode for videos.                                      | `ffmpeg`                  |
| `--no-config-file`, `-n` / -            | Do not use a config file.                                     | `false`                   |

### Tag Variables
The following variables can be used in the template folder/file and/or in the `exclude_tags` list:

`album`, `album_artist`, `artist`, `compilation`, `composer`, `copyright`, `cover`, `disc`, `disc_total`, `isrc`, `label`, `lyrics`, `media_type`, `playlist_artist`, `playlist_title`, `playlist_track`, `publisher`, `producer`, `rating`, `release_date`, `release_year`, `title`, `track`, `track_total`, `url`

### Reference
*   **Cover Sizes**: `small` (64px), `medium` (300px), `large` (640px), `extra-large` (2000px)
*   **Audio Qualities**: `aac-medium` (128kbps), `aac-high` (256kbps), `vorbis-high` (320kbps), `vorbis-medium` (160kbps), `vorbis-low` (96kbps)
*   **Video Formats**: `mp4`, `webm`, `ask`
*   **Download Modes**: `ytdlp`, `aria2c`
*   **Remux Modes**: `ffmpeg`, `mp4box`, `mp4decrypt`

## 🐛 Issues and Feedback
Encountered a bug or have some feedback? Please [open an issue on GitHub](https://github.com/AsHfIEXE/Dotify/issues). We'd love to hear from you!



## Support
For support, email me at `salahin0ashfi@gmail.com

## License
This project is licensed under the [MIT License](LICENSE).

## Authors
*   **@AsHfIEXE**

## License

MADE WITH [MIT License](https://choosealicense.com/licenses/mit/)



