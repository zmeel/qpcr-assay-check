"""Content-addressed on-disk cache with per-kind expiry.

BLAST results are only reused within a run (resume) and for a short time, because the database
changes: a naive cache would serve last year's answer to this year's identical question. Sequence
windows by accession.version never change and can be kept indefinitely (``ttl_days=None``).
"""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from platformdirs import user_cache_dir

APP = "qpcr-assay-check"


def default_cache_dir() -> Path:
    """Per-user cache directory."""
    return Path(user_cache_dir(APP))


def content_key(payload: Any) -> str:
    """SHA-256 over the canonical JSON of ``payload``."""
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


class Cache:
    """Stores text payloads (gzip-compressed) with a creation time."""

    def __init__(
        self,
        root: Path | str | None = None,
        *,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.root = Path(root) if root else default_cache_dir()
        self._now = now

    def _path(self, kind: str, key: str) -> Path:
        return self.root / kind / key[:2] / f"{key}.json.gz"

    def get(self, kind: str, key: str, *, ttl_days: float | None) -> str | None:
        """Return the cached text, or None if absent, expired or unreadable."""
        path = self._path(kind, key)
        try:
            with gzip.open(path, "rt", encoding="utf-8") as fh:
                record = json.load(fh)
            created = datetime.fromisoformat(record["created"])
        except (OSError, ValueError, KeyError, EOFError):
            return None
        if ttl_days is not None and self._now() - created > timedelta(days=ttl_days):
            return None
        text = record.get("text")
        return text if isinstance(text, str) else None

    def put(self, kind: str, key: str, text: str) -> Path:
        """Store text atomically (write to a temporary file, then rename)."""
        path = self._path(kind, key)
        path.parent.mkdir(parents=True, exist_ok=True)
        record = {"created": self._now().isoformat(), "text": text}
        fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "wb") as raw, gzip.open(raw, "wt", encoding="utf-8") as fh:
                json.dump(record, fh)
            os.replace(tmp, path)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise
        return path
