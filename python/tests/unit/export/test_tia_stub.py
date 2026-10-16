"""the tiadump stub and the dump schema used by every Python TIA test."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

from tests.contract.export.tiahelpers import STUB, make_project

SCHEMA = Path(__file__).resolve().parents[3] / "src/plcexport/extractors/tia/dump_schema.json"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(STUB), *args], capture_output=True, text=True)


def test_dump_schema_is_valid_draft_2020_12() -> None:
    Draft202012Validator.check_schema(json.loads(SCHEMA.read_text(encoding="utf-8")))


def test_minimal_dump_validates() -> None:
    dump = {
        "dump_version": 1,
        "tool": {"name": "tiadump", "version": "1.0.0"},
        "source": {"file": "Line3.zap19", "kind": "project", "saved_version": "V19"},
        "tia": {"version": "V21", "upgrade": {"from": "V19", "to": "V21", "messages": []}},
        "languages": {"project": ["en-US"]},
        "multiuser": {"kind": "none"},
        "missing_packages": [],
        "counts": {"PLC_1": {"units": 1}},
        "cleanup": {"outside_work": []},
        "devices": [
            {
                "name": "PLC_1",
                "kind": "plc",
                "family": "S7-1500",
                "units": [
                    {
                        "name": "Main",
                        "kind": "OB",
                        "number": 1,
                        "language": "LAD",
                        "folder": "Program blocks",
                        "protected": False,
                        "safety": False,
                        "consistent": False,
                        "part": "sd",
                        "files": ["sd/PLC_1/Main.s7dcl"],
                    }
                ],
                "tag_tables": [],
            }
        ],
        "hardware": {"devices": [], "subnets": []},
        "errors": [],
    }
    validator = Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8")))
    assert [e.message for e in validator.iter_errors(dump)] == []


def test_stub_probe_and_exit_codes(tmp_path: Path) -> None:
    out = tmp_path / "probe.json"
    assert (
        _run("probe", str(make_project(tmp_path, "Line3.zap19", "x")), "--out", str(out)).returncode
        == 0
    )
    assert json.loads(out.read_text(encoding="utf-8"))["saved_version"] == "V19"
    # like the real tiadump, the stub only opens a copy inside --work
    src = make_project(tmp_path / "w" / "a", "Line3.zap21", "exit:5")
    r = _run("project", str(src), "--work", str(tmp_path / "w"), "--out", str(tmp_path / "o"))
    assert r.returncode == 5
    missing = make_project(tmp_path / "w" / "b", "Line3.zap21", "no_such_fixture")
    r = _run("project", str(missing), "--work", str(tmp_path / "w"), "--out", str(tmp_path / "o"))
    assert r.returncode == 2


def test_stub_refuses_a_source_outside_work(tmp_path: Path) -> None:
    outside = make_project(tmp_path / "a", "Line3.zap21", "tank_v19")
    r = _run("project", str(outside), "--work", str(tmp_path / "w"), "--out", str(tmp_path / "o"))
    assert r.returncode == 64 and "inside --work" in r.stderr
