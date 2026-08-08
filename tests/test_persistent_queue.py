from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from dotify.client import DotifyClient
from dotify.downloader.exceptions import DotifyQueueItemCompleted
from dotify.downloader.types import DownloadItem
from dotify.interface.types import SpotifyMedia
from dotify.queue import PersistentDownloadQueue


def item(path, source_url="spotify:test"):
    return DownloadItem(
        media=SpotifyMedia("media-id", {"name": "Fixture"}),
        final_path=str(path),
        source_url=source_url,
    )


def test_queue_state_survives_process_restart(tmp_path):
    output = tmp_path / "track.ogg"
    output.write_bytes(b"audio")
    state_path = tmp_path / "queue.json"
    queue = PersistentDownloadQueue(state_path, tmp_path)
    queued_item = item(output)
    queue.mark(queued_item, "success")

    reloaded = PersistentDownloadQueue(state_path, tmp_path)

    assert reloaded.completed_path(queued_item) == str(output)


def test_queue_ignores_transient_spotify_share_parameters(tmp_path):
    output = tmp_path / "track.ogg"
    output.write_bytes(b"audio")
    queue = PersistentDownloadQueue(tmp_path / "queue.json", tmp_path)
    original = item(
        output,
        "https://open.spotify.com/track/media-id?si=first",
    )
    queue.mark(original, "success")

    shared_again = item(
        output,
        "https://open.spotify.com/track/media-id?si=second",
    )

    assert queue.completed_path(shared_again) == str(output)


@pytest.mark.asyncio
async def test_client_resume_skips_before_prepare(tmp_path):
    output = tmp_path / "track.ogg"
    output.write_bytes(b"audio")
    queue = PersistentDownloadQueue(tmp_path / "queue.json", tmp_path)
    queued_item = item(output)
    queue.mark(queued_item, "success")
    downloader = SimpleNamespace(prepare=AsyncMock(), download=AsyncMock())
    client = DotifyClient(
        SimpleNamespace(),
        SimpleNamespace(),
        downloader,
        queue=queue,
        resume=True,
    )

    with pytest.raises(DotifyQueueItemCompleted):
        await client.download_item(queued_item)

    downloader.prepare.assert_not_awaited()
