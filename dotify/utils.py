import string
from json import JSONDecodeError
from typing import Any

import httpx


def raise_for_status(response: httpx.Response):
    try:
        response.raise_for_status()
    except httpx.HTTPError as e:
        raise Exception(
            f"Request failed with status code {response.status_code}: {response.text}"
        )


def safe_json(response: httpx.Response) -> dict | None:
    try:
        return response.json()
    except JSONDecodeError:
        return None


class DotifyException(Exception):
    pass


class CustomStringFormatter(string.Formatter):
    def format_field(self, value: Any, format_spec: str) -> str:
        if isinstance(value, tuple) and len(value) == 2:
            actual_value, fallback_value = value
            if actual_value is None:
                return fallback_value

            try:
                return super().format_field(actual_value, format_spec)
            except Exception:
                return fallback_value

        return super().format_field(value, format_spec)
