# Setup wizard, terminal UI, and languages

## First-time setup

Run the guided wizard:

```bash
dotify init
```

The wizard asks for language, output directory, audio quality, cookie and WVD
paths, terminal UI preference, and the delay between downloads. It writes the
configuration atomically with user-only file permissions and never overwrites
an existing config without confirmation.

For automated installations:

```bash
dotify init --non-interactive --language tr
dotify init --non-interactive --force --config-path /path/to/config.ini
```

## Terminal UI

Enable the Rich terminal interface for one run:

```bash
dotify --tui "SPOTIFY_URL"
```

For playlists, Dotify first offers `Download all tracks` and `Choose tracks`.
Download-all mode consumes and downloads entries incrementally, avoiding a
full metadata-selection pass. Choose-tracks mode presents a metadata-only
multi-select list backed by stable numeric identifiers. Selected items are
added to a visible queue. Stream URLs, audio keys, and licenses are fetched
lazily only when each selected item is about to download; the configured wait
interval is therefore applied before the next license request. Existing files
and completed persistent-queue entries are checked before stream resolution.
During yt-dlp transfers the UI shows bytes, transfer speed, progress, and ETA;
external aria2c/curl modes show an indeterminate state followed by their final
transferred size. The final summary reports successful, skipped, and failed
items, elapsed time, and bytes written to the library. It also reports the
codec/container actually selected.
When Spotify rate-limits a Widevine request, the active item displays the 429
reason, retry number, and a live seconds-remaining countdown instead of an
indeterminate download spinner.
When Dotify falls back from a rejected Librespot quality to Web/AAC, a second
table shows the requested qualities, downloaded format, and final file path.

Use `--no-tui` to override a config that enables the interface.

## Languages

English and Turkish are currently supported:

```bash
dotify --language tr --tui "SPOTIFY_URL"
dotify --language en "SPOTIFY_URL"
```

Language precedence is:

1. `--language`
2. `language` in `~/.dotify/config.ini`
3. `DOTIFY_LANGUAGE`
4. system locale
5. English fallback

The localization catalog lives in `dotify/i18n.py`; new languages can be
added without changing the downloader or API layers.
