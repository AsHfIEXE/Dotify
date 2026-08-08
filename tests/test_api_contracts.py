import json
from pathlib import Path

import pytest

from dotify.api.adapter import (
    SpotifyApiAdapter,
    SpotifyContractError,
    validate_response_contract,
)


FIXTURES = Path(__file__).parent / "fixtures" / "api"


@pytest.mark.parametrize(
    ("operation", "fixture"),
    [
        ("track", "track.json"),
        ("album", "album.json"),
        ("playlist", "playlist.json"),
        ("episode", "episode.json"),
        ("show", "show.json"),
        ("artist_overview", "artist.json"),
        ("artist_albums", "artist.json"),
        ("artist_singles", "artist.json"),
        ("artist_compilations", "artist.json"),
        ("artist_videos", "artist.json"),
        ("library_tracks", "library_tracks.json"),
    ],
)
def test_recorded_response_contracts(operation, fixture):
    response = json.loads((FIXTURES / fixture).read_text(encoding="utf-8"))
    assert validate_response_contract(operation, response) is response


def test_contract_error_identifies_operation_and_missing_path():
    with pytest.raises(SpotifyContractError) as caught:
        validate_response_contract("track", {"data": {}})

    assert caught.value.operation == "track"
    assert caught.value.missing_path == "data.trackUnion"


@pytest.mark.asyncio
async def test_adapter_delegates_and_validates():
    class FakeClient:
        async def get_track(self, track_id):
            return {"data": {"trackUnion": {"uri": f"spotify:track:{track_id}"}}}

    response = await SpotifyApiAdapter(FakeClient()).get_track("abc")
    assert response["data"]["trackUnion"]["uri"] == "spotify:track:abc"


@pytest.mark.asyncio
async def test_adapter_can_disable_validation_for_emergency_compatibility():
    class FakeClient:
        async def get_track(self, track_id):
            return {"upstream": "changed"}

    response = await SpotifyApiAdapter(
        FakeClient(), validate_contracts=False
    ).get_track("abc")
    assert response == {"upstream": "changed"}
