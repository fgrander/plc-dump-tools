"""``tia``: Siemens TIA Portal projects through ``tiadump`` and TIA Openness (
contracts/tia-extractor.md, contracts/tiadump.md).

Runs where TIA Portal is installed (route ``local``); elsewhere the route is ``worker`` and
``plcexport one`` reports the project as unsupported. ``tiadump``
gets a copy in a short work folder (TIA refuses project paths over 143 characters) with
``TEMP``/``TMP`` pointing into it, writes ``dump.json`` plus SD/SimaticML/xlsx files, and the
dump is validated and mapped to one model per PLC. The work folder is deleted afterwards
.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from functools import cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from plcexport.common import ExtractWarning
from plcexport.config import Settings
from plcexport.extractors.base import (
    DetectionRule,
    ExtractOptions,
    ExtractRefused,
    JobFacts,
    ProbeResult,
    Route,
    VendorRequirement,
    VersionSpec,
)
from plcexport.extractors.tia import needs as tia_needs
from plcexport.extractors.tia.facts import source_facts
from plcexport.extractors.tia.library import load_company_libraries, to_library_model
from plcexport.extractors.tia.mapping import PLATFORM, MappingOptions, to_bundle
from plcexport.extractors.tia.versions import (
    TiaVersion,
    handling,
    source_kind,
    unsupported_reason,
)
from plcexport.model import CATEGORIES, Category, ExportBundle

REPO_ROOT = Path(__file__).resolve().parents[5]
SCHEMA = Path(__file__).with_name("dump_schema.json")
# folders holding a project, library or multiuser local session are one source each; archives
# are single-file sources
MARKERS = ("*.ap[0-9][0-9]", "*.al[0-9][0-9]", "*.als[0-9][0-9]")
FILE_MARKERS = ("*.zap[0-9][0-9]", "*.zal[0-9][0-9]")
EXIT_CANNOT_OPEN, EXIT_UPGRADE_REFUSED, EXIT_ACCESS_DENIED, EXIT_LOCKED, EXIT_USAGE = 2, 3, 4, 5, 64
# TIA reports in its UI language (English or German seen); tiadump's stderr may lose umlauts
_MISSING = re.compile(
    r"(?:without these products|ohne diese Produkte\S*|packages are missing|"
    r"Pakete fehlen)\s*:?\s*(.+)$",
    re.IGNORECASE,
)
_UPGRADE_FAILED = re.compile(r"Hochr\S{1,3}sten ist fehlgeschlagen|upgrad\w* (has )?failed", re.I)
_PROTECTED = re.compile(r"Projekt ist gesch\S{1,3}tzt|project is protected", re.IGNORECASE)
OPENNESS_KEY = r"SOFTWARE\Siemens\Automation\Openness"


@cache
def _validator() -> Draft202012Validator:
    return Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8")))


def default_tiadump_path() -> Path:
    return REPO_ROOT / "tiadump" / "publish" / "tiadump.exe"


def installed_tia_versions() -> list[TiaVersion]:
    """TIA Portal versions with Openness on this host (``HKLM\\...\\Openness\\<NN>.0``)."""
    if sys.platform != "win32":
        return []
    import winreg

    found = []
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, OPENNESS_KEY) as key:
            for i in range(winreg.QueryInfoKey(key)[0]):
                name = winreg.EnumKey(key, i)
                try:
                    found.append(TiaVersion.parse(name))
                except ValueError:
                    continue  # AllowList and other subkeys
    except OSError:
        return []
    return sorted(found)


def host_version(setting: str) -> TiaVersion | None:
    """``auto``: newest installed; ``none``: this host has no TIA Portal; else e.g. ``V21``."""
    if setting.strip().lower() == "none":
        return None
    if setting.strip().lower() != "auto":
        return TiaVersion.parse(setting)
    versions = installed_tia_versions()
    return versions[-1] if versions else None


def source_file(project_dir: Path) -> Path:
    """The TIA file of a source: the file itself (``.zapNN``, ``.zalNN``) or the project or
    library file inside a folder (``.apNN``, ``.alNN``)."""
    if project_dir.is_file():
        return project_dir
    files = sorted(p for p in project_dir.iterdir() if p.is_file() and source_kind(p))
    if not files:
        raise FileNotFoundError(f"no TIA project or library file in {project_dir}")
    return files[0]


def _tail(text: str, n: int = 400) -> str:
    return " ".join(text.strip().split())[-n:]


def tiadump_for(settings: Settings, major: int | None) -> Path:
    """The ``tiadump`` build for a TIA major: ``tiadump_paths["V21"]``, else
    ``tiadump_path``, else ``publish/V21/tiadump.exe`` if built, else the default build."""
    if major is not None and (path := settings.tiadump_paths.get(f"V{major}")) is not None:
        return path
    if settings.tiadump_path is not None:
        return settings.tiadump_path
    default = default_tiadump_path()
    per_major = default.parent / f"V{major}" / default.name
    return per_major if major is not None and per_major.is_file() else default


class TiaExtractor:
    id: str = "tia"
    version: str = "1.1.0"  # connections; a new version exports every TIA project again
    platform: str = PLATFORM
    detection = DetectionRule(markers=MARKERS, archive_kinds=(), file_markers=FILE_MARKERS)
    supported_versions = VersionSpec()  # the host's TIA Portal decides
    requires: VendorRequirement | None = VendorRequirement("TIA Portal", ">=20.4")
    categories: frozenset[Category] = frozenset(CATEGORIES)
    fallback: str | None = None

    @property
    def route(self) -> Route:
        """``local`` where TIA Portal is installed, else ``worker``."""
        return "local" if host_version(Settings().tia_version) is not None else "worker"

    def facts(self, source: Path) -> JobFacts | None:
        """saved version and used products, read without TIA Portal."""
        try:
            f = source_facts(source_file(source))
        except OSError:
            return None
        if f is None:
            return None
        return JobFacts(str(f.saved), tuple(tia_needs.needs_from(f.used_products)))

    @property
    def job_timeout_s(self) -> float:
        """The runner's limit for one job: tiadump's timeout plus copying and cleanup."""
        return Settings().tia_timeout_s + 300

    # -------------------------------------------------------------- tiadump
    def _command(self, settings: Settings, *args: str, major: int | None = None) -> list[str]:
        exe = tiadump_for(settings, major)
        if exe.suffix == ".py":  # test stub
            return [sys.executable, str(exe), *args]
        if not exe.is_file():
            raise FileNotFoundError(f"tiadump not found at {exe} (build tools/tiadump first)")
        return [str(exe), *args]

    def _run(self, settings: Settings, args: list[str], tmp: Path, timeout: float,
             major: int | None = None) -> subprocess.CompletedProcess[str]:  # fmt: skip
        tmp.mkdir(parents=True, exist_ok=True)
        env = dict(os.environ, TEMP=str(tmp), TMP=str(tmp))
        return subprocess.run(
            self._command(settings, *args, major=major),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            env=env,
        )

    def probe(self, project_dir: Path) -> ProbeResult:
        settings = Settings()
        try:
            src = source_file(project_dir)
            self._command(settings)
        except FileNotFoundError as exc:
            return ProbeResult(False, reason=str(exc))
        kind = source_kind(src)
        if kind is None:
            return ProbeResult(False, reason=f"not a TIA source: {src.name}")
        work = settings.tia_work_root / f"p{uuid.uuid4().hex[:8]}"
        try:
            out = work / "probe.json"
            proc = self._run(settings, ["probe", str(src), "--out", str(out)], work / "tmp", 120)
            if proc.returncode != 0 or not out.is_file():
                return ProbeResult(False, reason=f"tiadump probe failed: {_tail(proc.stderr)}")
            info: dict[str, Any] = json.loads(out.read_text(encoding="utf-8"))
        finally:
            shutil.rmtree(work, ignore_errors=True)
        saved = info.get("saved_version")
        if saved and info.get("saved_update"):
            saved = f"{saved} {info['saved_update']}"
        # a local session is "readable": extract() reports it unsupported
        return ProbeResult(True, platform_version=saved, details=info)

    # -------------------------------------------------------------- extract
    def extract(self, project_dir: Path, work_dir: Path, options: ExtractOptions) -> ExportBundle:
        settings = Settings()
        src = source_file(project_dir)
        kind = source_kind(src)
        # options may name the TIA installation to use; else this host's setting
        chosen = str(options.extra.get("tia_version") or "").strip()
        host = TiaVersion.parse(chosen) if chosen else host_version(settings.tia_version)
        if host is None:
            raise ExtractRefused("no_capable_worker", "TIA Portal not installed on this host")
        h = handling(src, host)
        if (reason := unsupported_reason(h, src, host)) is not None:
            raise ExtractRefused("unsupported", reason)
        work = settings.tia_work_root / uuid.uuid4().hex[:8]
        try:
            # tiadump only opens a copy inside its --work folder (short path, deleted after the
            # job). .apNN/.alNN folders are opened in place, archives are retrieved below it.
            tia_work = work / "w"
            if project_dir.is_dir():
                copy = tia_work / "s" / project_dir.name
                shutil.copytree(project_dir, copy)
                src = copy / src.name
            else:
                tia_work.mkdir(parents=True, exist_ok=True)
                src = Path(shutil.copy2(src, tia_work / src.name))
            out = work / "o"
            command = "library" if kind == "library" else "project"
            args = [command, str(src), "--work", str(tia_work), "--out", str(out)]
            if chosen or settings.tia_version.strip().lower() not in ("auto", "none"):
                args += ["--tia", f"V{host.major}"]  # tiadump takes the major only
            proc = self._run(settings, args, work / "tmp", settings.tia_timeout_s, host.major)
            self._check_exit(proc)
            dump = json.loads((out / "dump.json").read_text(encoding="utf-8"))
            errors = sorted(_validator().iter_errors(dump), key=lambda e: list(e.absolute_path))
            if errors:
                where = "/".join(str(p) for p in errors[0].absolute_path)
                raise RuntimeError(f"invalid tiadump output at {where}: {errors[0].message}")
            if (dump.get("multiuser") or {}).get("kind") == "local_session":
                raise ExtractRefused("unsupported", unsupported_reason("local_session", src, host)
                                     or "multiuser local session")  # fmt: skip
            vendor = f"TIA Portal {dump['tia']['version']}"
            if dump["tia"].get("update"):
                vendor += f" {dump['tia']['update']}"
            if dump.get("library") is not None:  # a global library is one export
                source = options.extra.get("source_path")
                bundle = ExportBundle(
                    [
                        to_library_model(
                            dump, out, self.id, self.version, vendor,
                            str(source) if source else None,
                            load_company_libraries(settings.tia_libraries_file),
                        )
                    ]
                )  # fmt: skip
            else:
                bundle = to_bundle(dump, out, MappingOptions(self.id, self.version, vendor))
            leftovers = [
                str(p) for p in (dump.get("cleanup") or {}).get("outside_work") or []
                if Path(str(p)).resolve() != work.resolve()
            ]  # fmt: skip
            if leftovers:
                for m in bundle.models:
                    m.warnings.append(
                        ExtractWarning(
                            "cleanup_incomplete",
                            f"TIA left files outside the work folder: {', '.join(leftovers[:5])}",
                        )
                    )
            return bundle
        finally:
            shutil.rmtree(work, ignore_errors=True)

    @staticmethod
    def _check_exit(proc: subprocess.CompletedProcess[str]) -> None:
        code, err = proc.returncode, _tail(proc.stderr)
        if code == 0:
            return
        full = " ".join(proc.stderr.split())
        if code == EXIT_LOCKED:
            raise ExtractRefused("locked", f"locked – retry later: {err}")
        if code == EXIT_UPGRADE_REFUSED:
            raise ExtractRefused("unsupported", f"TIA refused upgrade: {err}")
        if code == EXIT_CANNOT_OPEN and (missing := _MISSING.search(full)):
            # the host lacks a TIA product the project needs (Startdrive, an HSP, ...); the
            # project itself is fine
            listed = missing.group(1).strip()
            raise ExtractRefused(
                "no_capable_worker",
                f"missing TIA products: {listed[:300]}",
                tia_needs.needs_from(x for x in re.split(r",\s*", listed) if x),
            )
        if code == EXIT_CANNOT_OPEN and _UPGRADE_FAILED.search(full):
            raise ExtractRefused("unsupported", f"TIA refused upgrade: {err}")
        if code == EXIT_CANNOT_OPEN and _PROTECTED.search(full):
            raise ExtractRefused(
                "unsupported", "protected project – credentials (UMAC) are needed to open it"
            )
        if code == EXIT_CANNOT_OPEN:
            raise RuntimeError(f"TIA Portal cannot open the project: {err}")
        if code == EXIT_ACCESS_DENIED:
            raise RuntimeError(f"TIA Openness access denied: {err}")
        if code == EXIT_USAGE:
            raise RuntimeError(f"tiadump usage error (bug): {err}")
        raise RuntimeError(f"tiadump crashed (exit {code}): {err}")
