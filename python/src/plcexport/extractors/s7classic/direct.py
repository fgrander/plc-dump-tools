"""``s7classic-direct``: STEP 7 V5.x without STEP 7.

Runs ``s7dump`` (DotNetSiemensPLCToolBoxLibrary) on the project copy, validates its JSON,
checks plausibility and maps it to ``ExportModel``. Anything that makes the result unreliable
raises ``NeedsFallback`` (the export then fails with the reasons).
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Mapping
from functools import cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from plcexport.config import Settings
from plcexport.extractors.base import (
    DetectionRule,
    ExtractOptions,
    NeedsFallback,
    ProbeResult,
    Route,
    VendorRequirement,
    VersionSpec,
)
from plcexport.extractors.s7classic.mapping import (
    CODE_KINDS,
    PLATFORM,
    MappingOptions,
    to_model,
)
from plcexport.extractors.s7classic.policy import disabled_types
from plcexport.model import CATEGORIES, Category, ExportModel

REPO_ROOT = Path(__file__).resolve().parents[5]
SCHEMA = Path(__file__).with_name("dump_schema.json")
EMPTY_BLOCK_MC7 = 2  # an empty block is just BE (2 bytes MC7) and has no networks
STL_CHARS_PER_MC7_BYTE = 50  # a 2-4 byte instruction is about 20-40 STL characters


@cache
def _validator() -> Draft202012Validator:
    return Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8")))


def default_s7dump_path() -> Path:
    rid = "win-x64" if sys.platform == "win32" else "linux-x64"
    exe = "s7dump.exe" if sys.platform == "win32" else "s7dump"
    return REPO_ROOT / "s7dump" / "publish" / rid / exe


def plausibility(dump: Mapping[str, Any], fallback_for: set[str]) -> list[str]:
    """Reasons why the dump is not reliable; empty = fine."""
    problems: list[str] = []
    for e in dump.get("errors") or []:
        problems.append(f"decoding error at {e['where']}: {e['message']}")
    for prog in dump["programs"]:
        name, cat = prog["name"], prog["catalog"]
        if cat["blocks"] != len(prog["blocks"]):
            problems.append(f"{name}: {len(prog['blocks'])} of {cat['blocks']} blocks decoded")
        if cat["symbols"] != len(prog["symbols"]):
            problems.append(f"{name}: {len(prog['symbols'])} of {cat['symbols']} symbols read")
        for b in prog["blocks"]:
            where = f"{name}/{b['type']}{b['number']}"
            if b.get("errors"):
                problems.append(f"{where}: {'; '.join(b['errors'])}")
                continue
            if b["type"] not in CODE_KINDS or b.get("know_how_protected"):
                continue
            size = int(b.get("mc7_size") or 0)
            if size > EMPTY_BLOCK_MC7 and not b["networks"]:
                problems.append(f"{where}: MC7 code of {size} bytes but no networks")
            # code only: STEP 7 keeps commented-out statements as text, also in a block
            # whose MC7 is nothing but BE
            stl_chars = sum(
                len(line.split("//", 1)[0].strip()) for nw in b["networks"] for line in nw["stl"]
            )
            if size > 0 and stl_chars > STL_CHARS_PER_MC7_BYTE * size:
                problems.append(f"{where}: STL text implausibly large for {size} bytes MC7")
        for s in prog["sources"]:
            if s.get("errors"):
                problems.append(f"{name}/source {s['name']}: {'; '.join(s['errors'])}")
    langs = dump["project"]["languages"]
    extra = [x for x in langs.get("maintained") or [] if x != langs["stored"]]
    if extra and "languages" in fallback_for:
        problems.append(f"comment languages {', '.join(extra)} are not stored in the project files")
    return problems


BLOCK_KINDS = frozenset({"OB", "FB", "FC", "DB", "IDB", "UDT"})


def content_types(model: ExportModel) -> set[str]:
    """The content types of the route policy that the project has."""
    present = set()
    if any(u.kind in BLOCK_KINDS for u in model.units):
        present.add("blocks")
    if any(v.scope == "global_tag" for v in model.variables):
        present.add("symbols")
    if (
        model.texts
        or any(v.comments for v in model.variables)
        or any(n.title or n.comment for b in model.unit_bodies.values() for n in b.networks)
    ):
        present.add("comments")
    if model.hardware.item_count():
        present.add("hardware")
    return present


class S7ClassicDirectExtractor:
    id: str = "s7classic-direct"
    version: str = "1.0.0"
    platform: str = PLATFORM
    detection = DetectionRule(markers=("*.s7p", "*.s7l"))
    supported_versions = VersionSpec()
    route: Route = "local"
    requires: VendorRequirement | None = None
    categories: frozenset[Category] = frozenset(CATEGORIES)
    fallback: str | None = "s7classic-worker"

    def probe(self, project_dir: Path) -> ProbeResult:
        files = [p for p in project_dir.iterdir() if p.suffix.lower() in (".s7p", ".s7l")]
        if not files:
            return ProbeResult(False, reason="no .s7p or .s7l project file")
        return ProbeResult(True, details={"project_file": sorted(p.name for p in files)[0]})

    def _command(self, settings: Settings, project_dir: Path, out: Path) -> list[str]:
        exe = settings.s7dump_path or default_s7dump_path()
        args = [str(project_dir), "--out", str(out), "--mnemonic", settings.s7_mnemonic]
        if exe.suffix == ".py":  # test stub
            return [sys.executable, str(exe), *args]
        if not exe.is_file():
            raise FileNotFoundError(f"s7dump not found at {exe} (build tools/s7dump first)")
        return [str(exe), *args]

    def extract(self, project_dir: Path, work_dir: Path, options: ExtractOptions) -> ExportModel:
        settings = Settings()
        work_dir.mkdir(parents=True, exist_ok=True)
        out = work_dir / "s7dump.json"
        proc = subprocess.run(
            self._command(settings, project_dir, out),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=settings.s7dump_timeout_s,
        )
        if proc.returncode == 2:
            raise NeedsFallback(f"s7dump cannot open the project: {proc.stderr.strip()[:300]}")
        if proc.returncode != 0 or not out.is_file():
            raise RuntimeError(f"s7dump failed (exit {proc.returncode}): {proc.stderr[-300:]}")
        dump = json.loads(out.read_text(encoding="utf-8"))
        errors = sorted(_validator().iter_errors(dump), key=lambda e: list(e.absolute_path))
        if errors:
            first = errors[0]
            where = "/".join(str(p) for p in first.absolute_path)
            raise NeedsFallback(f"invalid s7dump output at {where}: {first.message}")
        fallback_for = {x.strip() for x in settings.s7_fallback_for.split(",") if x.strip()}
        problems = plausibility(dump, fallback_for)
        if problems:
            raise NeedsFallback("; ".join(problems[:5]))
        model = to_model(
            dump, MappingOptions(self.id, self.version, text_language=settings.s7_text_language)
        )
        present = content_types(model)
        for content_type in disabled_types(settings.s7_policy_file):
            if content_type in present:  # the comparison found a difference
                raise NeedsFallback(f"policy: {content_type} disabled for the direct route")
        return model


class S7ClassicMultiproject:
    """Marks STEP 7 multiproject folders (``*.s7f``) as containers.

    Discovery does not export the container itself; it descends and exports every member
    project (``.s7p``) as its own ``multiproject_member``. ``extract`` is never called.
    """

    id: str = "s7classic-multiproject"
    version: str = "1.0.0"
    platform: str = PLATFORM
    detection = DetectionRule(markers=("*.s7f",), multiproject_container=True)
    supported_versions = VersionSpec()
    route: Route = "local"
    requires: VendorRequirement | None = None
    categories: frozenset[Category] = frozenset()
    fallback: str | None = None

    def probe(self, project_dir: Path) -> ProbeResult:
        return ProbeResult(False, reason="a multiproject is a container, not a project")

    def extract(self, project_dir: Path, work_dir: Path, options: ExtractOptions) -> ExportModel:
        raise NotImplementedError("multiproject containers are not exported themselves")
