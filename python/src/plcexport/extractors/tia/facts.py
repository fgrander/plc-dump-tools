"""What the central batch knows of a TIA source without TIA Portal.

A port of ``tiadump probe`` (``tools/tiadump/Dump/Probe.cs``), which is ``net48`` and does not run
on the Linux batch. The major version comes from the file suffix (``.zap21`` → V21); TIA V21 writes
``ProjectInfo.txt`` (archive root, or next to the ``.apNN``/``.alNN``) with the update level and
the products and support packages the project uses. Older sources have none of it.
"""

from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from plcexport.extractors.tia.versions import TiaVersion, saved_major, source_kind

INFO = "ProjectInfo.txt"
_HEADER_UPDATE = re.compile(
    r"V(\d\d)(?:\.\d+)?\s*(?:SP\s*\d+\s*)?(?:Upd(?:ate)?\s*(\d+))", re.IGNORECASE
)


@dataclass
class ProjectInfo:
    last_used_version: str | None = None
    last_used_technical_version: str | None = None
    products: list[tuple[str, str]] = field(default_factory=list)
    support_packages: list[tuple[str, str]] = field(default_factory=list)

    @property
    def update(self) -> int | None:
        """``21.00.04.00`` → 4; no update part → None."""
        parts = (self.last_used_technical_version or "").split(".")
        if len(parts) >= 3 and parts[2].isdigit() and int(parts[2]) > 0:
            return int(parts[2])
        return None


@dataclass(frozen=True)
class SourceFacts:
    saved: TiaVersion
    kind: str  # project | library | local_session
    used_products: tuple[tuple[str, str], ...] = ()
    used_support_packages: tuple[tuple[str, str], ...] = ()


def parse_project_info(text: str) -> ProjectInfo:
    """The YAML subset TIA writes: sections, ``- Key: value`` items (Probe.ParseProjectInfo)."""
    info = ProjectInfo()
    section = sub = ""
    items: list[tuple[str, str]] | None = None
    name: str | None = None
    for raw in text.replace("\r", "").split("\n"):
        if not raw.strip():
            continue
        indent = len(raw) - len(raw.lstrip())
        line = raw.strip()
        if indent == 0 and not line.startswith("-") and line.endswith(":"):
            section, sub, name = line[:-1], "", None
            items = (
                info.products if section == "UsedProducts"
                else info.support_packages if section == "UsedSupportPackages"
                else None
            )  # fmt: skip
            continue
        if not line.startswith("-") and line.endswith(":"):
            sub = line[:-1]
            continue
        item = line.lstrip("- ")
        if ":" not in item:
            continue
        key, value = (x.strip() for x in item.split(":", 1))
        if section == "TiaPortal" and sub == "LastUsed":
            if key == "Version":
                info.last_used_version = value
            elif key == "TechnicalVersion":
                info.last_used_technical_version = value
        elif items is not None:
            if key == "Name":
                name = value
            elif key == "Version" and name is not None:
                items.append((name, value))
                name = None
    return info


def read_project_info(file: Path) -> ProjectInfo | None:
    """``ProjectInfo.txt`` of an archive (root entry) or next to the file; None if absent."""
    try:
        if _is_archive(file):
            if not zipfile.is_zipfile(file):
                return None
            with zipfile.ZipFile(file) as z:
                entry = next((n for n in z.namelist() if n.lower() == INFO.lower()), None)
                if entry is None:
                    return None
                return parse_project_info(z.read(entry).decode("utf-8", errors="replace"))
        path = file.parent / INFO
        if not path.is_file():
            return None
        return parse_project_info(path.read_text(encoding="utf-8-sig", errors="replace"))
    except (OSError, zipfile.BadZipFile):
        return None


def _is_archive(file: Path) -> bool:
    return bool(re.search(r"\.z(ap|al)\d\d$", file.name, re.IGNORECASE))


def _header_update(file: Path, major: int) -> int | None:
    """Update level from the first 64 KiB of a project or library file (Probe.ReadUpdate)."""
    try:
        with file.open("rb") as f:
            text = f.read(64 * 1024).decode("utf-8", errors="replace")
    except OSError:
        return None
    for m in _HEADER_UPDATE.finditer(text):
        if int(m.group(1)) == major:
            return int(m.group(2))
    return None


def source_facts(file: Path) -> SourceFacts | None:
    """Facts of the TIA file of a source (``source_file`` of the extractor); None if the file is
    no TIA source."""
    kind = source_kind(file)
    major = saved_major(file)
    if kind is None or major is None:
        return None
    info = read_project_info(file)
    update = info.update if info is not None else None
    if update is None and info is None and not _is_archive(file):
        update = _header_update(file, major)
    return SourceFacts(
        saved=TiaVersion(major, update),
        kind=kind,
        used_products=tuple(info.products) if info else (),
        used_support_packages=tuple(info.support_packages) if info else (),
    )
