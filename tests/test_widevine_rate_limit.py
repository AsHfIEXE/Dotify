import asyncio
from unittest.mock import AsyncMock

import httpx
import pytest

from dotify.api.api import SpotifyApi
from dotify.api.exceptions import DotifyRequestException


def response(status_code, *, content=b"", retry_after=None):
    headers = {"Retry-After": retry_after} if retry_after is not None else {}
    return httpx.Response(
        status_code,
        content=content,
        headers=headers,
        request=httpx.Request("POST", "https://spotify.test/license"),
    )


def api_with_responses(*responses):
    api = SpotifyApi()
    api.client = AsyncMock()
    api.client.post.side_effect = responses
    api._refresh_authorization_if_needed = AsyncMock()
    return api


@pytest.mark.asyncio
async def test_widevine_429_honors_retry_after(monkeypatch):
    api = api_with_responses(
        response(429, retry_after="2"),
        response(200, content=b"license"),
    )
    sleep = AsyncMock()
    monkeypatch.setattr(asyncio, "sleep", sleep)

    license_bytes = await api.get_widevine_license(b"challenge", "audio")

    assert license_bytes == b"license"
    sleep.assert_awaited_once_with(2.0)
    assert api.client.post.await_count == 2


@pytest.mark.asyncio
async def test_widevine_429_can_delegate_wait_to_tui_callback(monkeypatch):
    api = api_with_responses(
        response(429, retry_after="2"),
        response(200, content=b"license"),
    )
    api.widevine_wait_callback = AsyncMock()
    sleep = AsyncMock()
    monkeypatch.setattr(asyncio, "sleep", sleep)

    license_bytes = await api.get_widevine_license(b"challenge", "audio")

    assert license_bytes == b"license"
    api.widevine_wait_callback.assert_awaited_once_with(2.0, 1, 2)
    sleep.assert_not_awaited()


@pytest.mark.asyncio
async def test_widevine_429_uses_bounded_exponential_backoff(monkeypatch):
    api = api_with_responses(
        response(429),
        response(429),
        response(200, content=b"license"),
    )
    sleep = AsyncMock()
    monkeypatch.setattr(asyncio, "sleep", sleep)

    license_bytes = await api.get_widevine_license(b"challenge", "audio")

    assert license_bytes == b"license"
    assert [call.args[0] for call in sleep.await_args_list] == [60, 120]
    assert api.client.post.await_count == 3


@pytest.mark.asyncio
async def test_persistent_widevine_429_stops_with_actionable_error(monkeypatch):
    api = api_with_responses(response(429), response(429), response(429))
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())

    with pytest.raises(DotifyRequestException) as captured:
        await api.get_widevine_license(b"challenge", "audio")

    message = str(captured.value)
    assert "wait at least 60 seconds" in message
    assert "concurrent Dotify processes" in message
    assert api.client.post.await_count == 3


@pytest.mark.asyncio
async def test_large_retry_after_is_not_retried_early(monkeypatch):
    api = api_with_responses(response(429, retry_after="300"))
    sleep = AsyncMock()
    monkeypatch.setattr(asyncio, "sleep", sleep)

    with pytest.raises(DotifyRequestException) as captured:
        await api.get_widevine_license(b"challenge", "audio")

    assert captured.value.retry_after == 300
    sleep.assert_not_awaited()
    assert api.client.post.await_count == 1


@pytest.mark.asyncio
async def test_widevine_request_interval_paces_license_calls(monkeypatch):
    api = api_with_responses(response(200, content=b"license"))
    api.widevine_request_interval = 5
    api._last_widevine_request_at = 100
    sleep = AsyncMock()
    monkeypatch.setattr(asyncio, "sleep", sleep)
    monkeypatch.setattr("dotify.api.api.time.monotonic", lambda: 101)

    await api.get_widevine_license(b"challenge", "audio")

    sleep.assert_awaited_once_with(4)
