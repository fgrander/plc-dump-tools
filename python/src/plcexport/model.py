"""``ExportModel``: what every platform extractor returns.

A superset of 002's ``ProjectExtract``. The 002 types are reused; the export adds hardware,
safety, HMI, structure, coverage, rendered unit bodies and a free-form ``platform`` part. Only the
core serializes this model, so the format stays identical for every platform.

``ExportUnit.language`` is the language in the engineering tool (``original_language`` in the
unit front matter). The language of the rendered body is ``UnitBody.language``.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from typing import Any, Literal, get_args

from plcexport.common import (
    ExtractText,
    ExtractUnit,
    ExtractVariable,
    ExtractWarning,
    ExtractXref,
    Scope,
)

FORMAT_VERSION = 1

# ------------------------------------------------------------------ coverage vocabulary
Category = Literal[
    "program_units", "symbols", "datatypes", "hardware", "safety", "hmi", "structure"
]
CATEGORIES: tuple[Category, ...] = get_args(Category)
# additive in format version 1. An export without it is valid (older exports, and
# extractors that do not read connections).
CONNECTIONS = "connections"
OPTIONAL_CATEGORIES: tuple[str, ...] = (CONNECTIONS,)
CoverageState = Literal["delivered", "partial", "unavailable"]
COVERAGE_STATES: tuple[CoverageState, ...] = get_args(CoverageState)
FIXED_REASONS = (
    "protected",
    "corrupt",
    "unsupported",
    "not_exported_cfc_sfc",
    "not_in_project",
)
BodyLanguage = Literal["scl", "stl", "st", "ntn", "il", "none"]
BODY_LANGUAGES: tuple[BodyLanguage, ...] = get_args(BodyLanguage)


def is_valid_reason(reason: str) -> bool:
    """True for a fixed reason or ``other:<text>`` (contract §4)."""
    if reason in FIXED_REASONS:
        return True
    return reason.startswith("other:") and len(reason) > len("other:")


Texts = Mapping[str, str]  # BCP 47 language -> text


# ------------------------------------------------------------------ project
@dataclass(frozen=True)
class Upgrade:
    """The extractor had to upgrade the working copy before reading it."""

    from_version: str
    to_version: str
    tool: str
    messages: tuple[str, ...] = ()  # what the vendor tool reported while upgrading


ProjectKind = Literal["project", "library"]


@dataclass(frozen=True)
class ExportProject:
    platform_id: str
    platform_version: str | None
    controller: str | None
    line_or_machine: str | None
    extractor_id: str
    extractor_version: str
    languages: tuple[str, ...] = ()
    upgrade: Upgrade | None = None
    kind: ProjectKind = "project"  # a library is an export of its own
    device: str | None = None  # the PLC (or "_project") a model of a bundle is for


# ------------------------------------------------------------------ program content
@dataclass(frozen=True)
class ExportUnit(ExtractUnit):
    safety: bool = False
    folder: str | None = None
    # Prefix of the symbolic paths of the unit's declarations (e.g. ``"FB_Heating"``) and the
    # 002 scope they get. Both are platform-specific, so the extractor states them.
    path_prefix: str | None = None
    variable_scope: Scope | None = None


@dataclass(frozen=True)
class ExportVariable(ExtractVariable):
    safety: bool = False
    # "byte.bit" in its data block or from the start of its data type (fixed
    # layouts only)
    offset: str | None = None
    # declaration order among its siblings, for a member without an offset.
    # It decides the order in the unit file and is not written to any file, so it does
    # not count when two variables are compared.
    position: int | None = field(default=None, compare=False)


@dataclass(frozen=True)
class ExportXref(ExtractXref):
    """``line`` is the 1-based line within the network's ``BodyNetwork.code`` (or None); the
    writer turns it into the line of the export file."""

    channel_ref: str | None = None  # I/O tag -> hardware channel ref
    hmi_ref: str | None = None  # HMI object -> PLC tag


# the cross-reference lists global targets only
_STACK_ADDRESS = re.compile(r"^L\s*\d+\.\d$|^L[BWD]\s*\d+$", re.IGNORECASE)  # L 0.1, LW 2
_CPU_REGISTERS = frozenset(
    {"AR1", "AR2", "DBNO", "DBLG", "DINO", "DILG", "STW", "BR", "OV", "OS", "RLO", "ACCU1", "ACCU2"}
)


def is_local_xref_target(target: str, access: str) -> bool:
    """True for targets left out of ``xref.json``.

    Block-local variables (``#name``), temporary stack addresses, CPU registers and
    register-indirect operands carry no information about where a signal is used.
    """
    t = target.strip()
    return (
        access == "indirect"
        or t.startswith("#")
        or bool(_STACK_ADDRESS.match(t))
        or t.upper() in _CPU_REGISTERS
        or "[AR" in t.upper().replace(" ", "")
    )


@dataclass(frozen=True)
class BodyNetwork:
    no: int
    code: str  # rendered statements, no trailing newline
    title: Texts = field(default_factory=dict)
    comment: Texts = field(default_factory=dict)


@dataclass(frozen=True)
class UnitBody:
    language: BodyLanguage
    networks: tuple[BodyNetwork, ...] = ()
    code: str | None = None  # whole-unit source for textual units without networks


# ------------------------------------------------------------------ hardware
@dataclass(frozen=True)
class HwController:
    ref: str
    name: str
    type: str | None = None
    order_no: str | None = None
    firmware: str | None = None


@dataclass(frozen=True)
class HwRack:
    ref: str
    name: str


@dataclass(frozen=True)
class HwModule:
    ref: str
    type: str
    rack: str | None = None
    slot: int | None = None
    order_no: str | None = None
    firmware: str | None = None
    address_ranges: tuple[str, ...] = ()


@dataclass(frozen=True)
class HwChannel:
    ref: str
    module_ref: str
    address: str
    symbol: str | None = None


@dataclass(frozen=True)
class HwNetwork:
    ref: str
    interface: str
    address: str | None = None
    device_name: str | None = None
    subnet: str | None = None


@dataclass(frozen=True)
class HardwareModel:
    controllers: tuple[HwController, ...] = ()
    racks: tuple[HwRack, ...] = ()
    modules: tuple[HwModule, ...] = ()
    channels: tuple[HwChannel, ...] = ()
    networks: tuple[HwNetwork, ...] = ()

    def item_count(self) -> int:
        return len(self.controllers) + len(self.modules) + len(self.channels) + len(self.networks)


# ------------------------------------------------------------------ safety
@dataclass(frozen=True)
class SafetyParameter:
    scope: str
    name: str
    value: str


@dataclass(frozen=True)
class SafetySignature:
    scope: str
    value: str
    kind: str


@dataclass(frozen=True)
class SafetyModel:
    units: tuple[str, ...] = ()  # names of units with safety=True
    tags: tuple[str, ...] = ()  # symbolic paths of variables with safety=True
    parameters: tuple[SafetyParameter, ...] = ()
    signatures: tuple[SafetySignature, ...] = ()

    def item_count(self) -> int:
        return len(self.units) + len(self.tags) + len(self.parameters) + len(self.signatures)


# ------------------------------------------------------------------ HMI
@dataclass(frozen=True)
class HmiDevice:
    name: str
    type: str | None = None


@dataclass(frozen=True)
class HmiObject:
    name: str
    type: str
    tag_bindings: tuple[str, ...] = ()


@dataclass(frozen=True)
class HmiScreen:
    name: str
    device: str
    objects: tuple[HmiObject, ...] = ()
    texts: Texts = field(default_factory=dict)


@dataclass(frozen=True)
class HmiAlarm:
    id: str
    alarm_class: str | None = None
    texts: Texts = field(default_factory=dict)
    trigger_tag: str | None = None


@dataclass(frozen=True)
class HmiTag:
    name: str
    device: str
    plc_tag: str | None = None


@dataclass(frozen=True)
class HmiRecipe:
    name: str
    device: str
    elements: tuple[str, ...] = ()


@dataclass(frozen=True)
class HmiModel:
    devices: tuple[HmiDevice, ...] = ()
    screens: tuple[HmiScreen, ...] = ()
    alarms: tuple[HmiAlarm, ...] = ()
    hmi_tags: tuple[HmiTag, ...] = ()
    recipes: tuple[HmiRecipe, ...] = ()

    def item_count(self) -> int:
        return (
            len(self.devices)
            + len(self.screens)
            + len(self.alarms)
            + len(self.hmi_tags)
            + len(self.recipes)
        )


# ------------------------------------------------------------------ structure
@dataclass(frozen=True)
class StructDevice:
    name: str
    type: str | None = None


@dataclass(frozen=True)
class StructTask:
    name: str
    kind: str
    interval: str | None = None
    units: tuple[str, ...] = ()


@dataclass(frozen=True)
class StructFolder:
    path: str
    units: tuple[str, ...] = ()


@dataclass(frozen=True)
class StructureModel:
    devices: tuple[StructDevice, ...] = ()
    tasks: tuple[StructTask, ...] = ()
    folders: tuple[StructFolder, ...] = ()

    def item_count(self) -> int:
        return len(self.devices) + len(self.tasks) + len(self.folders)


# ------------------------------------------------------------------ connections
ConnectionKind = Literal["s7", "other"]
CONNECTION_KINDS: tuple[ConnectionKind, ...] = get_args(ConnectionKind)
CommBlock = Literal["GET", "PUT", "BSEND", "BRCV", "USEND", "URCV"]
COMM_BLOCKS: tuple[CommBlock, ...] = get_args(CommBlock)
CouplerKind = Literal["pn_pn", "dp_dp"]
COUPLER_KINDS: tuple[CouplerKind, ...] = get_args(CouplerKind)
AreaRole = Literal["send", "receive", "remote"]
ValueSource = Literal["tables", "compiled", "both"]


@dataclass(frozen=True)
class ConnectionEnd:
    """The local end of a configured connection."""

    id: str  # "0x0010": hex, as the engineering tool shows it
    module: str | None = None  # module ref of hardware.json
    interface: str | None = None  # network ref of hardware.json
    address: str | None = None
    tsap: str | None = None  # "11.02"


@dataclass(frozen=True)
class ConnectionPartner:
    specified: bool = False  # True: a station inside the project
    name: str | None = None
    module: str | None = None  # only for a specified partner
    address: str | None = None
    rack: int | None = None
    slot: int | None = None
    tsap: str | None = None


@dataclass(frozen=True)
class ValueDifference:
    """A value the connection tables and the compiled data hold differently."""

    field: str
    tables: str
    compiled: str


@dataclass(frozen=True)
class Connection:
    ref: str
    name: str
    kind: ConnectionKind
    local: ConnectionEnd
    partner: ConnectionPartner = ConnectionPartner()
    details: Literal["read", "not_read"] = "read"
    type_id: int | None = None  # only for kind "other": the type number as stored
    active: bool | None = None  # the local side sets the connection up
    one_way: bool | None = None  # the tool's one-way flag, as found
    sources: Mapping[str, ValueSource] = field(default_factory=dict)
    differences: tuple[ValueDifference, ...] = ()
    safety: bool = False


@dataclass(frozen=True)
class CallValue:
    """A parameter of a communication call, as written: exactly one of the three is set."""

    value: str | None = None
    unresolved: str | None = None  # the operand that feeds it at run time
    unassigned: bool = False


@dataclass(frozen=True)
class DataArea:
    param: str  # "SD_1"
    role: AreaRole
    pointer: str | None = None  # "P#DB4.DBX0.0 INT 1"
    db: str | None = None  # unit name of the data block, when it is in the export
    start: str | None = None  # "byte.bit"
    length_bytes: int | None = None
    members: tuple[str, ...] = ()
    unresolved: str | None = None
    unassigned: bool = False


@dataclass(frozen=True)
class InterfaceFinding:
    code: str
    connection: str | None = None  # connection ref
    unit: str | None = None
    network_no: int | None = None
    coupler: str | None = None  # coupler side (rack ref) a coupler finding is about


@dataclass(frozen=True)
class ConnectionUse:
    unit: str
    block: CommBlock
    called: str  # "FB 12 #WritePLC3"
    network_no: int | None = None
    line: int | None = None
    id: CallValue = CallValue(unassigned=True)
    r_id: CallValue | None = None  # None: the block has no R_ID
    areas: tuple[DataArea, ...] = ()
    len: CallValue | None = None
    connection: str | None = None  # ref of the connection the ID names
    findings: tuple[InterfaceFinding, ...] = ()
    safety: bool = False


@dataclass(frozen=True)
class TransferArea:
    module: str  # module ref of hardware.json
    direction: Literal["in", "out"]
    range: str  # "%I2.0-%I13.7"
    length_bytes: int
    symbols: tuple[str, ...] = ()


@dataclass(frozen=True)
class Coupler:
    ref: str  # rack ref of the device in hardware.json
    kind: CouplerKind
    order_no: str | None = None
    address: str | None = None
    transfer_areas: tuple[TransferArea, ...] = ()
    safety: bool = False


@dataclass(frozen=True)
class ConnectionsModel:
    connections: tuple[Connection, ...] = ()
    uses: tuple[ConnectionUse, ...] = ()
    couplers: tuple[Coupler, ...] = ()
    findings: tuple[InterfaceFinding, ...] = ()

    def item_count(self) -> int:
        return len(self.connections) + len(self.uses) + len(self.couplers)

    def sorted(self) -> ConnectionsModel:
        return ConnectionsModel(
            connections=tuple(sorted(self.connections, key=lambda c: c.ref)),
            uses=tuple(
                sorted(self.uses, key=lambda u: (u.unit, u.network_no or 0, u.line or 0, u.block))
            ),
            couplers=tuple(sorted(self.couplers, key=lambda c: c.ref)),
            findings=tuple(
                sorted(
                    self.findings,
                    key=lambda f: (f.code, f.connection or "", f.unit or "", f.network_no or 0),
                )
            ),
        )


# ------------------------------------------------------------------ coverage
@dataclass(frozen=True)
class CategoryCoverage:
    state: CoverageState
    reason: str | None = None


@dataclass(frozen=True)
class Gap:
    # one of CATEGORIES or OPTIONAL_CATEGORIES (checked by the validator; the model codec
    # rejects a value outside a Literal, and `connections` is not in `Category`)
    category: str
    item: str
    reason: str


@dataclass(frozen=True)
class Coverage:
    categories: Mapping[str, CategoryCoverage] = field(default_factory=dict)
    gaps: tuple[Gap, ...] = ()


# ------------------------------------------------------------------ native parts
@dataclass(frozen=True)
class NativePart:
    """Vendor files written unchanged next to the common format, e.g. SIMATIC SD in ``sd/``.

    ``files`` maps POSIX paths below ``root`` to their bytes. The manifest lists the part.
    """

    kind: str  # "siemens-simatic-sd"
    root: str  # "sd"
    files: Mapping[str, bytes] = field(default_factory=dict)

    def sorted(self) -> NativePart:
        return replace(self, files=dict(sorted(self.files.items())))


# ------------------------------------------------------------------ libraries
LibraryKind = Literal["global", "project"]
LibraryTypeKind = Literal["plc_block", "plc_type", "hmi_type", "faceplate", "other"]
HMI_TYPE_KINDS = ("hmi_type", "faceplate")
TypeVersionStatus = Literal["released", "in_work"]
ContentPart = Literal["sd", "common", "none"]

_VERSION_PART = re.compile(r"(\d+)|([^\d.]+)")


def version_key(version: str) -> tuple[tuple[int, int | str], ...]:
    """Sort key for library version strings: numeric parts compare as numbers
    (``1.10.0`` after ``1.9.0``); text parts compare as text after numbers."""
    key: list[tuple[int, int | str]] = []
    for number, text in _VERSION_PART.findall(version):
        key.append((0, int(number)) if number else (1, text.lower()))
    return tuple(key)


@dataclass(frozen=True)
class TypeVersion:
    version: str
    status: TypeVersionStatus
    author: str | None
    date: str | None  # ISO date
    comment: Texts = field(default_factory=dict)
    content_part: ContentPart = "none"
    content_path: str | None = None
    gap_reason: str | None = None


@dataclass(frozen=True)
class LibraryType:
    name: str
    folder: str
    kind: LibraryTypeKind
    versions: tuple[TypeVersion, ...] = ()


@dataclass(frozen=True)
class MasterCopy:
    name: str
    folder: str
    objects: tuple[str, ...] = ()  # "<name> (<type>)" of the contained objects
    content_path: str | None = None


@dataclass(frozen=True)
class LibraryModel:
    name: str
    version: str | None
    kind: LibraryKind
    company: bool = False
    duplicate_of: str | None = None
    types: tuple[LibraryType, ...] = ()
    master_copies: tuple[MasterCopy, ...] = ()

    def sorted(self) -> LibraryModel:
        return replace(
            self,
            types=tuple(
                replace(t, versions=tuple(sorted(t.versions, key=lambda v: version_key(v.version))))
                for t in sorted(self.types, key=lambda t: (t.folder, t.name))
            ),
            master_copies=tuple(sorted(self.master_copies, key=lambda c: (c.folder, c.name))),
        )

    def item_count(self) -> int:
        return sum(len(t.versions) for t in self.types) + len(self.master_copies)


class LibraryValidationError(ValueError):
    pass


def validate_library(lib: LibraryModel) -> None:
    """Rules of data-model §1 (LibraryModel)."""
    problems: list[str] = []
    if lib.company and lib.kind != "global":
        problems.append('company only on kind="global" libraries')
    for t in lib.types:
        versions = [v.version for v in t.versions]
        if len(versions) != len(set(versions)):
            problems.append(f"{t.folder}/{t.name}: version strings unique per type")
        for v in t.versions:
            if v.status == "released" and v.content_part == "none" and not v.gap_reason:
                problems.append(
                    f"{t.name}@{v.version}: released versions must have content or a gap reason"
                )
            if v.gap_reason and not is_valid_reason(v.gap_reason):
                problems.append(f"{t.name}@{v.version}: invalid gap reason {v.gap_reason!r}")
    if problems:
        raise LibraryValidationError("; ".join(problems))


LinkObjectKind = Literal["unit", "hmi_object"]


@dataclass(frozen=True)
class LibraryLink:
    """A link fact from the vendor tool: ``object`` is an instance of a library type version
    . Never inferred from names or content."""

    object: str  # unit name or "hmi:<device>/<screen>/<object>"
    object_kind: LinkObjectKind
    type_name: str
    type_folder: str
    version: str
    status: TypeVersionStatus
    original_library: str | None


# ------------------------------------------------------------------ the model
PROGRAM_UNIT_KINDS = frozenset({"OB", "FB", "FC", "DB", "IDB", "OTHER"})


@dataclass
class ExportModel:
    project: ExportProject
    units: list[ExportUnit] = field(default_factory=list)
    unit_bodies: dict[str, UnitBody] = field(default_factory=dict)  # unit name -> body
    texts: list[ExtractText] = field(default_factory=list)  # block-level titles/comments
    variables: list[ExportVariable] = field(default_factory=list)
    xrefs: list[ExportXref] = field(default_factory=list)
    hardware: HardwareModel = field(default_factory=HardwareModel)
    safety: SafetyModel = field(default_factory=SafetyModel)
    hmi: HmiModel = field(default_factory=HmiModel)
    structure: StructureModel = field(default_factory=StructureModel)
    coverage: Coverage = field(default_factory=Coverage)
    connections: ConnectionsModel = field(default_factory=ConnectionsModel)
    platform: dict[str, Any] = field(default_factory=dict)
    warnings: list[ExtractWarning] = field(default_factory=list)
    # SIMATIC SD (and other native) files, library content and library link facts
    native_parts: list[NativePart] = field(default_factory=list)
    library: LibraryModel | None = None
    library_links: list[LibraryLink] = field(default_factory=list)
    # further JSON files of the platform part: name -> content (``platform/<id>/<name>``),
    # e.g. TIA library type GUIDs, which 001 allows only below platform/
    platform_files: dict[str, Any] = field(default_factory=dict)

    # -------------------------------------------------------------- helpers
    def is_damaged(self) -> bool:
        """True if the *project* could not be read completely (job status ``partial``).

        Limits of an extractor (e.g. hardware only partly readable) are not damage: they are
        visible in ``coverage.json`` but leave the job ``exported``.
        """
        return any(
            c.state == "partial" and c.reason == "corrupt"
            for c in self.coverage.categories.values()
        ) or any(g.reason == "corrupt" for g in self.coverage.gaps)

    def item_counts(self) -> dict[str, int]:
        """Number of items per coverage category (used by validation and the manifest)."""
        counts = {
            "program_units": sum(1 for u in self.units if u.kind in PROGRAM_UNIT_KINDS),
            "symbols": sum(1 for v in self.variables if v.scope == "global_tag"),
            "datatypes": sum(1 for u in self.units if u.kind == "UDT"),
            "hardware": self.hardware.item_count(),
            "safety": self.safety.item_count(),
            "hmi": self.hmi.item_count(),
            "structure": self.structure.item_count(),
            CONNECTIONS: self.connections.item_count(),
        }
        if self.project.kind == "library" and self.library is not None:
            # 005 contract §3: HMI types are the library's hmi items; folders and master copies
            # its structure
            lib = self.library
            counts["hmi"] += sum(len(t.versions) for t in lib.types if t.kind in HMI_TYPE_KINDS)
            counts["structure"] += len(lib.master_copies) + len({t.folder for t in lib.types})
        return counts

    def sorted(self) -> ExportModel:
        """Return a copy with every list in its canonical order."""
        hw, sf, hmi, st = self.hardware, self.safety, self.hmi, self.structure
        return replace(
            self,
            units=sorted(self.units, key=lambda u: (u.kind, u.name)),
            unit_bodies=dict(sorted(self.unit_bodies.items())),
            texts=sorted(self.texts, key=lambda t: (t.unit, t.network_no or 0, t.kind, t.lang)),
            variables=sorted(self.variables, key=lambda v: (v.declared_in, v.symbolic_path)),
            xrefs=sorted(self.xrefs, key=xref_key),
            hardware=HardwareModel(
                controllers=tuple(sorted(hw.controllers, key=lambda c: c.ref)),
                racks=tuple(sorted(hw.racks, key=lambda r: r.ref)),
                modules=tuple(sorted(hw.modules, key=lambda m: m.ref)),
                channels=tuple(sorted(hw.channels, key=lambda c: c.ref)),
                networks=tuple(sorted(hw.networks, key=lambda n: n.ref)),
            ),
            safety=SafetyModel(
                units=tuple(sorted(sf.units)),
                tags=tuple(sorted(sf.tags)),
                parameters=tuple(sorted(sf.parameters, key=lambda p: (p.scope, p.name))),
                signatures=tuple(sorted(sf.signatures, key=lambda s: (s.scope, s.kind))),
            ),
            hmi=HmiModel(
                devices=tuple(sorted(hmi.devices, key=lambda d: d.name)),
                screens=tuple(sorted(hmi.screens, key=lambda s: (s.device, s.name))),
                alarms=tuple(sorted(hmi.alarms, key=lambda a: a.id)),
                hmi_tags=tuple(sorted(hmi.hmi_tags, key=lambda t: (t.device, t.name))),
                recipes=tuple(sorted(hmi.recipes, key=lambda r: (r.device, r.name))),
            ),
            structure=StructureModel(
                devices=tuple(sorted(st.devices, key=lambda d: d.name)),
                tasks=tuple(sorted(st.tasks, key=lambda t: t.name)),
                folders=tuple(sorted(st.folders, key=lambda f: f.path)),
            ),
            coverage=Coverage(
                categories={
                    c: self.coverage.categories[c]
                    for c in (*CATEGORIES, *OPTIONAL_CATEGORIES)
                    if c in self.coverage.categories
                },
                gaps=tuple(sorted(self.coverage.gaps, key=lambda g: (g.category, g.item))),
            ),
            connections=self.connections.sorted(),
            warnings=sorted(self.warnings, key=lambda w: (w.unit or "", w.code, w.message)),
            native_parts=sorted(
                (p.sorted() for p in self.native_parts), key=lambda p: (p.root, p.kind)
            ),
            library=self.library.sorted() if self.library else None,
            library_links=sorted(self.library_links, key=lambda k: (k.object, k.type_name)),
        )


@dataclass
class ExportBundle:
    """what an extractor returns for a source that holds several PLCs: one model per
    device (``project.device``), all published from one source. Single-model extractors keep
    returning an ``ExportModel``; the core wraps it with :func:`as_bundle`."""

    models: list[ExportModel]


def as_bundle(result: ExportModel | ExportBundle) -> ExportBundle:
    return result if isinstance(result, ExportBundle) else ExportBundle([result])


def xref_key(x: ExtractXref) -> tuple[Any, ...]:
    return (
        x.from_unit,
        x.network_no or 0,
        x.line or 0,
        x.target_text,
        x.access,
        x.via_param or "",
    )


HMI_UNIT_PREFIX = "hmi:"


def link_channels(m: ExportModel) -> ExportModel:
    """Set ``channel_ref`` on xrefs to I/O tags that a hardware channel is assigned to."""
    by_symbol = {c.symbol: c.ref for c in m.hardware.channels if c.symbol}
    m.xrefs = [
        replace(x, channel_ref=by_symbol[x.target_text])
        if x.target_kind == "variable" and x.channel_ref is None and x.target_text in by_symbol
        else x
        for x in m.xrefs
    ]
    return m


def link_hmi(m: ExportModel) -> ExportModel:
    """Add one xref per HMI tag binding: ``from_unit`` is ``hmi:<screen>`` and ``hmi_ref`` is
    ``<screen>/<object>``. The direction of a binding is not known in general."""
    existing = {(x.from_unit, x.target_text, x.hmi_ref) for x in m.xrefs}
    for screen in m.hmi.screens:
        for obj in screen.objects:
            for tag in obj.tag_bindings:
                key = (f"{HMI_UNIT_PREFIX}{screen.name}", tag, f"{screen.name}/{obj.name}")
                if key not in existing:
                    m.xrefs.append(
                        ExportXref(key[0], "variable", tag, "unknown_direction", hmi_ref=key[2])
                    )
                    existing.add(key)
    return link_channels(m)
