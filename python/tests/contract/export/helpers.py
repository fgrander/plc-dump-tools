"""Shared helpers for the 001 export tests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tests.conftest import FIXTURE_REPO, FIXTURES

GOLDEN_EXPORTS = FIXTURES / "golden" / "export"
# exported_at is run-specific; source.path depends on where the test puts the source
RUN_SPECIFIC = ("exported_at", "source.path")


def fixture_project(rel: str) -> Path:
    return FIXTURE_REPO / rel


def read_tree(root: Path) -> dict[str, bytes]:
    return {
        p.relative_to(root).as_posix(): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def normalize_manifest(files: dict[str, bytes]) -> dict[str, bytes]:
    """Replace the run-specific manifest values so two exports can be compared byte-exactly."""
    out = dict(files)
    m = json.loads(out["manifest.json"])
    m["exported_at"] = "<exported_at>"
    m["source"]["path"] = "<source.path>"
    out["manifest.json"] = (
        json.dumps(m, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    ).encode("utf-8")
    return out


def tree_checksum(root: Path) -> str:
    h = hashlib.sha256()
    for rel, data in read_tree(root).items():
        h.update(rel.encode("utf-8") + b"\0" + data + b"\0")
    return h.hexdigest()
