"""TIA Portal versions.

The major version comes from the file suffix (``.zap19`` → V19); ``tiadump probe`` may add the
update level (``Upd3``). Projects newer than the host's TIA Portal are reported, not opened;
older ones are upgraded on the working copy by ``tiadump`` itself.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

_SUFFIX = re.compile(r"\.(z?ap|z?al|als)(\d\d)$", re.IGNORECASE)
_VERSION = re.compile(
    r"^V?(\d{2})(?:\.\d+)?(?:\s*(?:Upd(?:ate)?\s*|Update\s+)(\d+))?$", re.IGNORECASE
)

SourceKind = Literal["project", "library", "local_session"]
MIN_TIA = (20, 4)  # SIMATIC SD export needs TIA Portal V20 Update 4


@dataclass(frozen=True, order=True)
class TiaVersion:
    major: int
    update: int | None = None

    @classmethod
    def parse(cls, text: str) -> TiaVersion:
        """``V19``, ``V20 Upd4``, ``V21 Update 2``, ``21`` …"""
        m = _VERSION.match(text.strip())
        if not m:
            raise ValueError(f"not a TIA Portal version: {text!r}")
        return cls(int(m.group(1)), int(m.group(2)) if m.group(2) else None)

    def __str__(self) -> str:
        return f"V{self.major}" + (f" Upd{self.update}" if self.update is not None else "")


def source_kind(path: Path) -> SourceKind | None:
    """Kind of a TIA source from its suffix, or None for other files."""
    m = _SUFFIX.search(path.name)
    if not m:
        return None
    tag = m.group(1).lower()
    return "local_session" if tag == "als" else "library" if tag.endswith("al") else "project"


def saved_major(path: Path) -> int | None:
    m = _SUFFIX.search(path.name)
    return int(m.group(2)) if m else None


Handling = Literal["open", "upgrade", "newer_than_host", "local_session"]


def handling(path: Path, host: TiaVersion, saved: TiaVersion | None = None) -> Handling:
    """What the extractor does with a source: open as is, upgrade the working
    copy, refuse because the host's TIA Portal is older, or refuse a multiuser local session."""
    if source_kind(path) == "local_session":
        return "local_session"
    major = saved.major if saved else saved_major(path)
    if major is None:
        raise ValueError(f"not a TIA source: {path.name}")
    if major > host.major:
        return "newer_than_host"
    if (
        major == host.major
        and saved is not None
        and saved.update is not None
        and host.update is not None
        and saved.update > host.update
    ):
        return "newer_than_host"
    return "upgrade" if major < host.major else "open"


def unsupported_reason(h: Handling, path: Path, host: TiaVersion) -> str | None:
    if h == "newer_than_host":
        return f"unsupported version: {path.name} is newer than TIA Portal {host} on this host"
    if h == "local_session":
        return "multiuser local session – export the server project"
    return None
