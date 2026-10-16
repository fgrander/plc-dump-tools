"""Source content checksum: SHA-256 over relative paths and contents (or the archive bytes)."""

from __future__ import annotations

import hashlib
from pathlib import Path

_CHUNK = 1024 * 1024


def _files(path: Path) -> list[Path]:
    """Files below ``path`` in an OS-independent order (by POSIX path, case-sensitive)."""
    if path.is_file():
        return [path]
    return sorted(
        (p for p in path.rglob("*") if p.is_file()), key=lambda p: p.relative_to(path).as_posix()
    )


def source_checksum(path: Path) -> str:
    """``sha256:<hex>`` over relative paths and contents of every file below ``path``.

    A single file (e.g. an archive) is hashed by its content only.
    """
    h = hashlib.sha256()
    for p in _files(path):
        if p is not path:
            h.update(p.relative_to(path).as_posix().encode("utf-8") + b"\0")
        with p.open("rb") as fh:
            while chunk := fh.read(_CHUNK):
                h.update(chunk)
        h.update(b"\0")
    return f"sha256:{h.hexdigest()}"
