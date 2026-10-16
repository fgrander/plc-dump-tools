"""real TIA Portal runs on the sample projects (TIA host only, marker
``tiareference``): the source is never changed (Story 1 scenario 7), and an
older project is upgraded on the copy only, with the upgrade in the manifest.

Each project takes a minute or more in TIA Portal. ``PLCEXPORT_TIA_REFERENCE_LIMIT`` (default 3)
caps how many samples a test opens; ``0`` means all.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from plcexport.extractors.tia.extractor import host_version
from plcexport.format.validate import validate_export
from plcexport.one import export_project
from tests.conftest import TIA_SAMPLES
from tests.tiareference import reference_projects, tia_major

pytestmark = pytest.mark.tiareference
LIMIT = int(os.environ.get("PLCEXPORT_TIA_REFERENCE_LIMIT", "3"))


def _source(project_file: Path) -> Path:
    """What is exported: the archive itself, or the folder of a ``.apNN`` project."""
    return project_file if project_file.suffix.lower().startswith(".z") else project_file.parent


def _digest(path: Path) -> str:
    h = hashlib.sha256()
    files = [path] if path.is_file() else sorted(p for p in path.rglob("*") if p.is_file())
    for f in files:
        h.update(f.relative_to(path.parent).as_posix().encode() + b"\0" + f.read_bytes())
    return h.hexdigest()


def _pick(projects: list[Path], *, older: bool | None = None) -> list[Path]:
    host = host_version("auto")
    if host is None:
        pytest.skip("TIA Portal is not installed on this host")
    if older is not None:
        projects = [p for p in projects if ((tia_major(p) or 0) < host.major) == older]
    archives = sorted((p for p in projects if p.suffix.lower().startswith(".z")),
                      key=lambda p: p.stat().st_size)  # fmt: skip
    picked = archives or projects
    return picked if LIMIT == 0 else picked[:LIMIT]


def test_export_leaves_the_source_unchanged(tmp_path: Path) -> None:
    projects = _pick(reference_projects())
    if not projects:
        pytest.skip("no TIA Portal sample projects in samples/tia-portal")
    for i, project in enumerate(projects):
        source = _source(project)
        before = _digest(source)
        result = export_project(source, tmp_path / f"out{i}")
        assert _digest(source) == before, f"{project.name}: the source changed"
        ok = ("exported", "partial", "unsupported", "locked", "no_capable_worker")
        assert result.status in ok, (
            project.name, result.status, result.reason,
        )  # fmt: skip
        if result.status in ("exported", "partial"):
            targets = [tmp_path / f"out{i}" / d for d in result.devices] or [tmp_path / f"out{i}"]
            for t in targets:
                assert validate_export(t) == [], (project.name, t.name)


def test_older_project_is_upgraded_on_the_copy_only(tmp_path: Path) -> None:
    projects = _pick(reference_projects(), older=True)
    if not projects:
        pytest.skip("no sample project older than the installed TIA Portal")
    project = projects[0]
    source = _source(project)
    before = _digest(source)
    result = export_project(source, tmp_path / "out")
    assert _digest(source) == before  # the archive is untouched
    assert result.status in ("exported", "partial"), (project.name, result.reason)
    out = tmp_path / "out"
    manifests = sorted(out.rglob("manifest.json"))
    assert manifests
    host = host_version("auto")
    assert host is not None
    for m in manifests:
        upgrade = json.loads(m.read_text(encoding="utf-8")).get("upgrade")
        assert upgrade, m
        assert upgrade["from"] == f"V{tia_major(project)}" and upgrade["to"] == f"V{host.major}"
        assert isinstance(upgrade.get("messages", []), list)  # omitted when TIA reported none


def test_reference_sample_with_connections(tmp_path: Path) -> None:
    """the owner's sample ``myTiaProject1`` stays unchanged, and the
    export of PLC_1 lists the three connections of the reference table."""

    project = TIA_SAMPLES / "myTiaProject1" / "myTiaProject1"
    if not (project / "myTiaProject1.ap21").is_file():
        pytest.skip("reference sample myTiaProject1 not present")
    if host_version("auto") is None:
        pytest.skip("TIA Portal is not installed on this host")
    before = _digest(project)
    result = export_project(project, tmp_path / "out")
    assert _digest(project) == before
    assert result.status in ("exported", "partial"), result.reason
    doc = json.loads(next((tmp_path / "out").rglob("PLC_1/connections.json")).read_text("utf-8"))
    got = {
        c["local"]["id"]: (c["partner"]["address"], c["local"]["tsap"], c["partner"]["tsap"])
        for c in doc["connections"]
    }
    assert got == {
        "0x0100": ("192.168.1.50", "14.01", "15.02"),
        "0x0101": ("192.168.1.70", "10.01", "11.01"),
        "0x0102": ("192.168.1.5", "SIMATIC-ACC10201", "SIMATIC-ACC11001"),
    }
