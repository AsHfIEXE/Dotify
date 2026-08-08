# Dotify plugins

Dotify supports metadata providers, custom downloaders, and post-processors.
Plugins can be registered directly or discovered from Python entry points.

## Metadata provider

```python
class GenreProvider:
    async def enrich(self, media):
        media.media_metadata["custom_genre"] = "Example"
        return media
```

Metadata providers run in registration order. Returning `None` keeps the
current media object; returning a media object replaces it for later plugins.

## Downloader

```python
class MyDownloader:
    def supports(self, item):
        return item.media.tags.media_type.name == "SONG"

    async def download(self, item):
        ...
```

The first downloader whose `supports()` method returns true replaces the
built-in downloader for that item.

## Post-processor

```python
class Notify:
    async def process(self, item):
        print(f"Finished: {item.final_path}")
```

Post-processors run in order after a successful built-in or custom download.

## Package entry points

Declare exactly one protocol per plugin object:

```toml
[project.entry-points."dotify.metadata"]
genre = "my_package:GenreProvider"

[project.entry-points."dotify.downloaders"]
custom = "my_package:MyDownloader"

[project.entry-points."dotify.postprocessors"]
notify = "my_package:Notify"
```

Entry-point values may be instances or zero-argument classes. Discovery
errors are collected in `PluginManager.load_errors`; `discover(strict=True)`
raises immediately instead.
