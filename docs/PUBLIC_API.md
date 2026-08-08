# Dotify Python API

Dotify's supported Python API is asynchronous and does not import Click or
execute CLI configuration. The public API version is independent from the
package version and is available as `dotify.__api_version__`. This custom build
provides public API version `1.2`.

```python
import asyncio
from pathlib import Path

from dotify import DotifyClient, DotifySettings


async def main():
    settings = DotifySettings(
        output_path="./Music",
        audio_quality=("vorbis-high", "aac-medium"),
        strict_audio_quality=False,
        widevine_retries=2,
        widevine_backoff=60,
        widevine_max_wait=120,
        widevine_request_interval=5,
        queue_state_path=str(Path.home() / ".dotify" / "queue.json"),
        resume=True,
        librespot_credentials_path=str(
            Path.home() / ".dotify" / "librespot_credentials.json"
        ),
    )
    async with await DotifyClient.from_cookies(
        str(Path.home() / ".dotify" / "cookies.txt"),
        settings,
    ) as client:
        result = await client.download(
            "https://open.spotify.com/track/18gqCQzqYb0zvurQPlRkpo"
        )
        print(result.paths)


asyncio.run(main())
```

Applications that provide their own API, media interface, or downloader can
inject those components into `DotifyClient`. This is the recommended approach
for testing and advanced integrations.

The `librespot` session requires a one-time `dotify auth librespot` OAuth step.
Web cookies and the reusable Librespot credential file are separate. If
`librespot_credentials_path` is omitted, the Python API uses
`~/.dotify/librespot_credentials.json`.

Media iteration is metadata-first. Stream URLs, Librespot audio keys, and
Widevine licenses are resolved lazily by `download_item()`, after persistent
queue and existing-output checks. Applications may call
`await media.ensure_stream()` when they explicitly need stream information
without starting a download.

The Widevine retry settings are also available through `DotifySettings`.
Retries honor Spotify's `Retry-After` response and remain bounded by
`widevine_max_wait`; `widevine_request_interval` serializes and spaces license
requests within one client. These controls reduce accidental request bursts
but do not circumvent server-side rate limits.

Set `queue_state_path` to enable atomic persistent queue state in the Python
API. With `resume=True`, a completed entry is skipped only while its recorded
output file still exists.

## Supported surface

The compatibility guarantee covers:

- `DotifyClient`, `DotifySettings`, and `DownloadResult`
- `SpotifyApiPort`, `SpotifyApiAdapter`, and `SpotifyContractError`
- the protocols and entry-point group names in `dotify.plugins`
- `__api_version__` and `PUBLIC_API_VERSION`

Modules not listed here are implementation details until promoted explicitly.

## Versioning policy

The package follows semantic versioning. The Python/plugin API has a separate
`major.minor` version:

- additive public API changes increment the API minor version;
- incompatible changes increment the API major version;
- deprecations remain available for at least two package minor releases;
- deprecated behavior emits `DeprecationWarning` before removal;
- changes to Spotify's upstream response are not public API changes and are
  isolated by `SpotifyApiAdapter` contract validation.
