"""``PlatformExtractor`` protocol (contracts/extractor-contract.md)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Protocol, runtime_checkable

from plcexport.model import Category, ExportBundle, ExportModel

Route = Literal["local", "worker"]
ArchiveKind = Literal["zip"]


@dataclass(frozen=True)
class DetectionRule:
    """How discovery recognizes a project of this platform.

    ``markers`` are glob patterns relative to a candidate folder (``*.s7p``,
    ``plcproject.testfixture.yaml``). A folder that contains a match is a project root, unless
    ``content_probe`` (a callable path -> bool) rejects it. ``multiproject_container`` allows
    discovery to descend into the project folder to find member projects.
    ``file_markers`` match files that are a project each, independent of their folder
    (TIA archives ``*.zap19``): discovery makes one ``archive`` source per file, not unpacked.
    """

    markers: tuple[str, ...]
    archive_kinds: tuple[ArchiveKind, ...] = ("zip",)
    multiproject_container: bool = False
    file_markers: tuple[str, ...] = ()
    content_probe: Any = None  # Callable[[Path], bool] | None; Any keeps the dataclass hashable


@dataclass(frozen=True)
class VersionSpec:
    """Supported platform versions; an empty tuple means "any"."""

    versions: tuple[str, ...] = ()

    def accepts(self, version: str | None) -> bool:
        return not self.versions or version in self.versions


@dataclass(frozen=True)
class VendorRequirement:
    software: str
    versions: str  # e.g. ">=5.6"


@dataclass(frozen=True)
class ExtractOptions:
    unit_split_bytes: int = 40 * 1024
    extra: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProbeResult:
    readable: bool
    platform_version: str | None = None
    controller: str | None = None
    reason: str | None = None  # why it is not readable
    details: Mapping[str, Any] = field(default_factory=dict)


class NeedsFallback(Exception):
    """Raised by an extractor whose result would be unreliable; the core routes to ``fallback``."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


RefusedStatus = Literal["unsupported", "locked", "no_capable_worker"]


class ExtractRefused(Exception):
    """the source cannot be exported here for a known reason; the job gets ``status``
    (``unsupported``: e.g. newer than the host's vendor software; ``locked``: retry later;
    ``no_capable_worker``: the vendor software is not installed here)."""

    def __init__(self, status: RefusedStatus, reason: str, missing: Sequence[str] = ()) -> None:
        super().__init__(reason)
        self.status: RefusedStatus = status
        self.reason = reason
        # products this installation lacks, by name
        self.missing: list[str] = list(missing)


@dataclass(frozen=True)
class JobFacts:
    """What is known of a source before vendor software opens it."""

    platform_version: str | None = None
    needs: tuple[str, ...] = ()  # products it uses
    requires: tuple[str, ...] = ()  # products TIA refused to open it without


# Optional extractor hooks, not part of the protocol so that existing extractors stay valid:
#   facts(source: Path) -> JobFacts | None
#       read without vendor software (TIA: version, used products)


@runtime_checkable
class PlatformExtractor(Protocol):
    id: str
    version: str
    platform: str
    detection: DetectionRule
    supported_versions: VersionSpec
    requires: VendorRequirement | None
    categories: frozenset[Category]
    fallback: str | None

    @property
    def route(self) -> Route:
        """``local`` or ``worker``; a class attribute in most extractors, a property in ``tia``
        (it depends on whether TIA Portal is installed here)."""
        ...

    def probe(self, project_dir: Path) -> ProbeResult: ...

    def extract(
        self, project_dir: Path, work_dir: Path, options: ExtractOptions
    ) -> ExportModel | ExportBundle:
        """Read a copy of the project and return the model (or one model per device).
        Must not write outside work_dir and must not raise on unknown content (degrade and
        record gaps instead)."""
        ...
