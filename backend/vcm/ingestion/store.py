"""Content-addressed object store for raw source documents (plan/02 §Ingestion).

Phase 0 backs onto the local filesystem under ``config.storage_dir`` (MinIO/S3 is a
later swap behind this same interface). Files are keyed by SHA-256, so re-ingesting an
identical document is idempotent and the ``documents.sha256`` column dedupes naturally.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from vcm.config import get_settings


@dataclass(frozen=True)
class StoredObject:
    key: str  # storage key relative to the base dir (also `documents.storage_path`)
    path: Path
    sha256: str
    size: int


def _normalize_suffix(suffix: str) -> str:
    suffix = suffix.strip().lower()
    if not suffix:
        return ""
    if not suffix.startswith("."):
        suffix = f".{suffix}"
    # keep only a sane extension (alnum), else drop it
    return suffix if suffix[1:].isalnum() else ""


class ObjectStore:
    def __init__(self, base_dir: str | Path | None = None) -> None:
        self._base = Path(base_dir) if base_dir is not None else Path(get_settings().storage_dir)

    @property
    def base_dir(self) -> Path:
        return self._base

    def save(self, data: bytes, *, suffix: str = "") -> StoredObject:
        """Write ``data`` under its SHA-256 key; a no-op if that content already exists."""
        digest = hashlib.sha256(data).hexdigest()
        name = f"{digest}{_normalize_suffix(suffix)}"
        rel = Path(digest[:2]) / name  # shard by first 2 hex chars to avoid huge dirs
        path = self._base / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_bytes(data)
        return StoredObject(key=str(rel), path=path, sha256=digest, size=len(data))

    def resolve(self, key: str) -> Path:
        return self._base / key
