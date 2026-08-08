"""Atomic persistent download state used for safe queue resume."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit


class PersistentDownloadQueue:
    def __init__(self, path: str | Path, scope: str = "") -> None:
        self.path = Path(path).expanduser()
        self.scope = str(Path(scope).expanduser().absolute()) if scope else ""
        self._state = self._load()

    def _load(self) -> dict[str, Any]:
        if not self.path.is_file():
            return {"version": 1, "items": {}}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {"version": 1, "items": {}}
        return data if isinstance(data.get("items"), dict) else {"version": 1, "items": {}}

    def _key(self, item: Any) -> str:
        media = item.media
        source = self._normalize_source(getattr(item, "source_url", "") or "")
        identity = f"{source}\0{media.media_id}\0{self.scope}"
        return hashlib.sha256(identity.encode("utf-8")).hexdigest()

    @staticmethod
    def _normalize_source(source: str) -> str:
        """Ignore transient Spotify share parameters when identifying work."""

        parts = urlsplit(source)
        return urlunsplit((parts.scheme, parts.netloc, parts.path.rstrip("/"), "", ""))

    def completed_path(self, item: Any) -> str | None:
        entry = self._state["items"].get(self._key(item), {})
        path = entry.get("final_path")
        if entry.get("status") not in {"success", "skipped"} or not path:
            return None
        return path if Path(path).is_file() else None

    def mark(self, item: Any, status: str, error: str | None = None) -> None:
        key = self._key(item)
        self._state["items"][key] = {
            "media_id": item.media.media_id,
            "source_url": getattr(item, "source_url", None),
            "final_path": item.final_path,
            "status": status,
            "error": error,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._save()

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(self._state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.path)
