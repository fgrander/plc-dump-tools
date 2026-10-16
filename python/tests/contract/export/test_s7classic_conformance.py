"""conformance E1–E5 of ``s7classic-direct`` on recorded s7dump fixtures."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from plcexport.extractors.s7classic.direct import SCHEMA
from plcexport.format.validate import validate_export
from plcexport.one import export_project
from tests.contract.export.helpers import (
    GOLDEN_EXPORTS,
    normalize_manifest,
    read_tree,
    tree_checksum,
)
from tests.contract.export.s7helpers import S7DUMP_FIXTURES, make_project, use_stub

GOLDEN = {
    "s7_press_s7300": "press_s7300",
    "s7_protected": "protected",
    "s7_safety": "safety",
    "s7_connections": "connections",
}


@pytest.fixture(autouse=True)
def _stub(monkeypatch: pytest.MonkeyPatch) -> None:
    use_stub(monkeypatch)


@pytest.mark.parametrize("path", sorted(S7DUMP_FIXTURES.glob("*.json")), ids=lambda p: p.stem)
def test_fixtures_match_the_dump_schema(path: Path) -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    errors = list(Draft202012Validator(schema).iter_errors(json.loads(path.read_text("utf-8"))))
    assert errors == []


@pytest.mark.parametrize("name", sorted(GOLDEN))
def test_golden_export(name: str, tmp_path: Path) -> None:
    src = make_project(tmp_path / "src", "PRESS_1", GOLDEN[name])
    result = export_project(src, tmp_path / "out")
    assert result.extractor == "s7classic-direct"
    assert result.status in ("exported", "partial"), (result.reason, result.violations)
    actual = normalize_manifest(read_tree(tmp_path / "out"))
    golden = GOLDEN_EXPORTS / name
    if os.environ.get("PLCEXPORT_UPDATE_GOLDEN") == "1":
        shutil.rmtree(golden, ignore_errors=True)
        for rel, data in actual.items():
            (golden / rel).parent.mkdir(parents=True, exist_ok=True)
            (golden / rel).write_bytes(data)
    assert actual == read_tree(golden)


def test_export_validates_and_is_deterministic(tmp_path: Path) -> None:
    src = make_project(tmp_path / "src", "PRESS_1", "press_s7300")
    before = tree_checksum(src)
    export_project(src, tmp_path / "a")
    export_project(src, tmp_path / "b")
    assert validate_export(tmp_path / "a") == []
    assert normalize_manifest(read_tree(tmp_path / "a")) == normalize_manifest(
        read_tree(tmp_path / "b")
    )
    assert tree_checksum(src) == before  # E5 read-only


def test_lad_block_is_stl_with_original_language(tmp_path: Path) -> None:
    src = make_project(tmp_path / "src", "PRESS_1", "press_s7300")
    export_project(src, tmp_path / "out")
    main = (tmp_path / "out" / "units" / "OB" / "Main.md").read_text(encoding="utf-8")
    assert "language: stl" in main and "original_language: LAD" in main
    assert '```stl\n      A     "I_Start"' in main
    readme = (tmp_path / "out" / "README.md").read_text(encoding="utf-8")
    assert "## Platform: Siemens STEP 7 classic (V5.x)" in readme
    coverage = json.loads((tmp_path / "out" / "coverage.json").read_text(encoding="utf-8"))
    assert coverage["categories"]["hardware"] == {
        "state": "partial",
        "reason": "other:direct route reads stations, CPUs, CPs and networks only",
    }


def test_unreadable_project_falls_back(tmp_path: Path) -> None:
    """the direct route gives up cleanly; in a single export that is a failure with reason."""
    src = make_project(tmp_path / "src", "PRESS_1", "exit:2")
    result = export_project(src, tmp_path / "out")
    assert result.status == "failed"
    assert "s7dump cannot open the project" in (result.reason or "")
    assert not (tmp_path / "out").exists()
