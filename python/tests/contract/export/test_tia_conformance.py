"""Conformance of the ``tia`` extractor on the recorded tiadump fixtures
(contracts/tia-extractor.md E1-E4, T5). The ``tiadump`` stub replays the dumps; goldens are in
``tests/fixtures/golden/export/tia_<fixture>/`` (``PLCEXPORT_UPDATE_GOLDEN=1`` regenerates)."""

from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from plcexport.config import get_settings
from plcexport.extractors.tia.extractor import SCHEMA
from plcexport.format.validate import validate_export
from plcexport.one import export_project
from tests.contract.export.helpers import GOLDEN_EXPORTS, read_tree, tree_checksum
from tests.contract.export.tiahelpers import TIADUMP_FIXTURES, make_project, use_stub

FIXTURES = {
    "step7_v21": "Step7.zap21",
    "tank_v19": "Tank.zap19",
    "pid_v19": "PID.zap19",
    "conn_v21": "myTiaProject1.zap21",  # connections, couplers
}


@pytest.fixture(autouse=True)
def _stub(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    use_stub(monkeypatch)
    monkeypatch.setenv("PLCEXPORT_TIA_WORK_ROOT", str(tmp_path / "tiaw"))
    monkeypatch.setenv("PLCEXPORT_TIA_VERSION", "V21")
    get_settings.cache_clear()


def _normalize(files: dict[str, bytes]) -> dict[str, bytes]:
    """Run-specific manifest values out, in every device's manifest."""
    out = dict(files)
    for rel in [r for r in out if r == "manifest.json" or r.endswith("/manifest.json")]:
        m = json.loads(out[rel])
        m["exported_at"] = "<exported_at>"
        m["source"]["path"] = "<source.path>"
        out[rel] = (json.dumps(m, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode()
    return out


@pytest.mark.parametrize("name", sorted(FIXTURES))
def test_fixtures_match_the_dump_schema(name: str) -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    dump = json.loads((TIADUMP_FIXTURES / name / "dump.json").read_text(encoding="utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(dump)) == []


@pytest.mark.parametrize("name", sorted(FIXTURES))
def test_golden_export(name: str, tmp_path: Path) -> None:
    """E1 golden + E2 validation + T5 completeness."""
    src = make_project(tmp_path / "src", FIXTURES[name], name)
    out = tmp_path / "out"
    result = export_project(src, out)
    assert result.extractor == "tia"
    assert result.status == "exported", (result.reason, result.violations)
    targets = [out / d for d in result.devices] or [out]
    for t in targets:
        assert validate_export(t) == [], t.name
        coverage = json.loads((t / "coverage.json").read_text(encoding="utf-8"))
        assert all(c.get("reason") != "other:completeness mismatch"
                   for c in coverage["categories"].values())  # fmt: skip
    actual = _normalize(read_tree(out))
    golden = GOLDEN_EXPORTS / f"tia_{name}"
    if os.environ.get("PLCEXPORT_UPDATE_GOLDEN") == "1":
        shutil.rmtree(golden, ignore_errors=True)
        for rel, data in actual.items():
            (golden / rel).parent.mkdir(parents=True, exist_ok=True)
            (golden / rel).write_bytes(data)
    assert actual == read_tree(golden)


def test_multi_plc_project_gives_one_export_per_plc(tmp_path: Path) -> None:
    src = make_project(tmp_path / "src", "Step7.zap21", "step7_v21")
    result = export_project(src, tmp_path / "out")
    assert result.devices == ["PLC_1", "PLC_2", "PLC_S120Democase"]
    manifest = json.loads((tmp_path / "out" / "PLC_1" / "manifest.json").read_text("utf-8"))
    assert manifest["device"] == "PLC_1"
    assert [p["kind"] for p in manifest["parts"]] == ["common", "siemens-simatic-sd"]


def test_sd_files_are_byte_exact_except_text_ids(tmp_path: Path) -> None:
    """SD files are written as TIA wrote them; only the text IDs, which TIA makes up again on
    every upgrade, are renumbered in a stable order."""
    src = make_project(tmp_path / "src", "Tank.zap19", "tank_v19")
    export_project(src, tmp_path / "out")
    rel = Path("Programmbausteine") / "FB_2_Filling.s7dcl"
    exported = (tmp_path / "out" / "sd" / rel).read_bytes()
    recorded = (TIADUMP_FIXTURES / "tank_v19" / "sd" / "Tank application" / rel).read_bytes()
    text_id = re.compile(rb"MLC_[0-9A-Za-z]+")
    assert exported != recorded  # the IDs are renumbered …
    assert text_id.sub(b"MLC_x", exported) == text_id.sub(b"MLC_x", recorded)  # … nothing else
    assert exported.startswith(b"\xef\xbb\xbf") and b"\r\n" in exported


def test_export_is_deterministic_and_read_only(tmp_path: Path) -> None:
    """E3 determinism, E5 (stub level): the source is unchanged."""
    src = make_project(tmp_path / "src", "Tank.zap19", "tank_v19")
    before = tree_checksum(src.parent)
    export_project(src, tmp_path / "a")
    export_project(src, tmp_path / "b")
    assert _normalize(read_tree(tmp_path / "a")) == _normalize(read_tree(tmp_path / "b"))
    assert tree_checksum(src.parent) == before


@pytest.mark.parametrize(
    ("fixture", "status", "reason"),
    [
        ("truncated", "failed", "extractor error"),
        ("exit:2", "failed", "cannot open"),
        ("exit:3", "unsupported", "TIA refused upgrade"),
        ("exit:4", "failed", "access denied"),
        ("exit:5", "locked", "locked – retry later"),
        ("exit:139", "failed", "crashed"),
    ],
)
def test_robustness(fixture: str, status: str, reason: str, tmp_path: Path) -> None:
    """every failure is a status with a reason, nothing escapes and nothing is written."""
    src = make_project(tmp_path / "src", "Line3.zap19", fixture)
    result = export_project(src, tmp_path / "out")
    assert result.status == status
    assert reason in (result.reason or "")
    assert not (tmp_path / "out").exists()
    assert not (tmp_path / "tiaw").exists() or not any((tmp_path / "tiaw").iterdir())


def test_newer_project_is_unsupported(tmp_path: Path) -> None:
    src = make_project(tmp_path / "src", "Line3.zap22", "pid_v19")
    result = export_project(src, tmp_path / "out")
    assert result.status == "unsupported"
    assert "newer than TIA Portal V21" in (result.reason or "")
