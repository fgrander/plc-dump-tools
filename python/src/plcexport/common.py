"""Platform profile protocol and extract types (contracts/platform-profile.md).

Deviation from the contract text: ``map_changed_paths`` also receives the ``RepoTree`` of the new
revision, because mapping a changed file to its project root needs the tree.
"""

from __future__ import annotations

import posixpath
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Any, Literal, Protocol, runtime_checkable

ContentKind = Literal["native", "common_export"]
UnitKind = Literal["OB", "FB", "FC", "DB", "IDB", "UDT", "TAG_TABLE", "OTHER"]
ParseQuality = Literal["full", "partial", "names_only"]
TextKind = Literal["title", "comment"]
Scope = Literal[
    "global_tag", "db_member", "fb_interface", "fc_interface", "udt_member", "instance_member"
]
Section = Literal["IN", "OUT", "IN_OUT", "STATIC", "TEMP", "CONSTANT", "RETURN"]
IoDirection = Literal["input", "output", "memory"]
Access = Literal["read", "write", "read_write", "call", "unknown_direction", "indirect"]
TargetKind = Literal["variable", "unit"]


# ------------------------------------------------------------------ repository view
@dataclass(frozen=True)
class RepoTree:
    """File list of the repository at one revision (no contents)."""

    revision: str
    paths: tuple[str, ...]

    def under(self, prefix: str) -> list[str]:
        pre = prefix.rstrip("/") + "/"
        return [p for p in self.paths if p.startswith(pre)]

    def dirs_with(self, basename: str) -> list[str]:
        return sorted(
            {posixpath.dirname(p) for p in self.paths if posixpath.basename(p) == basename}
        )


@dataclass(frozen=True)
class ProjectRoot:
    path: str  # repository path of the project root directory
    profile_id: str


class BlobSource(Protocol):
    """What a profile may read: file contents and the file list, both pinned to a revision."""

    def read_text(self, revision: str, path: str) -> str: ...

    def tree_paths(self, revision: str) -> Sequence[str]: ...


# ------------------------------------------------------------------ extract
@dataclass(frozen=True)
class ExtractProject:
    controller: str | None
    platform_version: str | None
    line_or_machine: str | None
    languages: tuple[str, ...] = ()
    platform: str | None = None  # a multi-part export's manifest platform.id
    kind: Literal["project", "library"] = "project"  # manifest kind
    library: bool = False  # a block library, not a controller program


@dataclass(frozen=True)
class ExtractUnit:
    name: str
    kind: UnitKind
    language: str | None
    files: tuple[str, ...]
    parse_quality: ParseQuality = "full"
    number: int | None = None
    instance_of: str | None = None  # FB name for an IDB
    protected: bool = False
    attributes: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ExtractText:
    unit: str
    kind: TextKind
    lang: str
    text: str
    network_no: int | None = None
    element_ref: str | None = None


@dataclass(frozen=True)
class ExtractNetwork:
    unit: str
    no: int
    line_start: int
    line_end: int


@dataclass(frozen=True)
class ExtractVariable:
    declared_in: str  # unit name (tag table, DB, FB, FC or UDT)
    scope: Scope
    symbolic_path: str
    data_type: str
    section: Section | None = None
    io_direction: IoDirection | None = None
    parent_path: str | None = None  # symbolic path of the enclosing struct, if nested
    array_dims: str | None = None
    address: str | None = None
    start_value: str | None = None
    retain: bool | None = None
    ext_accessible: bool | None = None
    ext_visible: bool | None = None
    ext_writable: bool | None = None
    comments: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ExtractXref:
    from_unit: str
    target_kind: TargetKind
    target_text: str  # operand exactly as written; kept even when unresolved
    access: Access
    network_no: int | None = None
    line: int | None = None
    via_param: str | None = None


@dataclass(frozen=True)
class ExtractWarning:
    code: str
    message: str
    unit: str | None = None


@dataclass
class ProjectExtract:
    root: ProjectRoot
    project: ExtractProject
    units: list[ExtractUnit] = field(default_factory=list)
    texts: list[ExtractText] = field(default_factory=list)
    networks: list[ExtractNetwork] = field(default_factory=list)
    variables: list[ExtractVariable] = field(default_factory=list)
    xrefs: list[ExtractXref] = field(default_factory=list)
    warnings: list[ExtractWarning] = field(default_factory=list)
    # connection content of a common export, with its coverage state (None: the export
    # was not checked for connections). Typed loosely: the model lives in plcexport.model
    connections: Any = None
    connections_state: str | None = None
    # hardware of a common export with its coverage state (None: the export has no such
    # category), and the symbolic paths the export lists as safety tags
    hardware: Any = None
    hardware_state: str | None = None
    safety_tags: frozenset[str] = frozenset()
    # line count per file, used to validate network spans
    file_line_counts: dict[str, int] = field(default_factory=dict)
    # the parts of a multi-part project, for project.summary.parts
    parts: list[dict[str, Any]] = field(default_factory=list)
    # ``library.json`` of a library export (kind == "library")
    library: Mapping[str, Any] | None = None
    # ``library_links.json`` of a project export: its rows and ``compared_with``
    library_links: list[Mapping[str, Any]] = field(default_factory=list)
    library_compared: list[Mapping[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class FormatGuide:
    """Agent-facing description of a platform's files, included in the cached prompt prefix."""

    markdown: str
    examples: Mapping[str, str] = field(default_factory=dict)  # file name -> content
    personal_attributes: frozenset[str] = frozenset()  # unit attributes that hold personal data


# ------------------------------------------------------------------ protocol
@runtime_checkable
class PlatformProfile(Protocol):
    id: str
    version: str
    content_kind: ContentKind

    def detect_projects(self, tree: RepoTree) -> Iterable[ProjectRoot]: ...

    def map_changed_paths(self, paths: Iterable[str], tree: RepoTree) -> set[str]: ...

    def extract(
        self, project: ProjectRoot, reader: BlobSource, revision: str
    ) -> ProjectExtract: ...

    def format_guide(self) -> FormatGuide: ...


def merge_extracts(base: ProjectExtract, *parts: tuple[str, ProjectExtract]) -> ProjectExtract:
    """One project from several parts. Lists are
    concatenated; warnings of a part are prefixed with its name. Duplicate unit names or path
    keys are left for ``validate_extract`` to reject."""
    for name, part in parts:
        base.units += part.units
        base.texts += part.texts
        base.networks += part.networks
        base.variables += part.variables
        base.xrefs += part.xrefs
        base.warnings += [
            ExtractWarning(w.code, f"{name}: {w.message}", w.unit) for w in part.warnings
        ]
        base.file_line_counts.update(part.file_line_counts)
        langs = set(base.project.languages) | set(part.project.languages)
        base.project = replace(base.project, languages=tuple(sorted(langs)))
    base.units.sort(key=lambda u: u.name)
    base.texts.sort(key=lambda t: (t.unit, t.network_no or 0, t.kind, t.lang))
    base.networks.sort(key=lambda n: (n.unit, n.no))
    base.variables.sort(key=lambda v: v.symbolic_path)
    base.xrefs.sort(
        key=lambda x: (x.from_unit, x.network_no or 0, x.line or 0, x.target_text, x.access,
                       x.via_param or "")
    )  # fmt: skip
    return base


def normalize_path_key(symbolic_path: str) -> str:
    """Canonical lookup key: quotes removed, lowercase. ``"DB_X".a.b`` -> ``db_x.a.b``."""
    return symbolic_path.replace('"', "").strip().lower()
