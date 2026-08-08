"""Transport-neutral download progress events."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class DownloadProgress:
    status: str
    downloaded_bytes: int = 0
    total_bytes: int | None = None
    speed: float | None = None
    eta: float | None = None
    filename: str | None = None

    @classmethod
    def from_ytdlp(cls, payload: dict[str, Any]) -> "DownloadProgress":
        return cls(
            status=str(payload.get("status", "downloading")),
            downloaded_bytes=int(payload.get("downloaded_bytes") or 0),
            total_bytes=payload.get("total_bytes")
            or payload.get("total_bytes_estimate"),
            speed=payload.get("speed"),
            eta=payload.get("eta"),
            filename=payload.get("filename") or payload.get("tmpfilename"),
        )

