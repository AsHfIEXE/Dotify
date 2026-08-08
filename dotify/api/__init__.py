"""Spotify transport package.

``SpotifyApi`` is loaded lazily so lightweight public modules (plugins,
contracts, version inspection) do not initialize protobuf or networking code.
"""

from .adapter import (
    RESPONSE_CONTRACTS,
    SpotifyApiAdapter,
    SpotifyApiPort,
    SpotifyContractError,
    validate_response_contract,
)
from .enums import SessionType

__all__ = [
    "SpotifyApi",
    "SpotifyApiAdapter",
    "SpotifyApiPort",
    "SpotifyContractError",
    "validate_response_contract",
    "RESPONSE_CONTRACTS",
    "SessionType",
    "DotifyApiException",
    "DotifyAuthenticationException",
    "DotifyLibrespotAuthenticationException",
    "DotifyLibrespotConnectionException",
    "DotifyPremiumRequiredException",
    "DotifyRequestException",
]


def __getattr__(name: str):
    if name == "SpotifyApi":
        from .api import SpotifyApi

        return SpotifyApi
    if name in {
        "DotifyApiException",
        "DotifyAuthenticationException",
        "DotifyLibrespotAuthenticationException",
        "DotifyLibrespotConnectionException",
        "DotifyPremiumRequiredException",
        "DotifyRequestException",
    }:
        from . import exceptions

        return getattr(exceptions, name)
    raise AttributeError(name)
