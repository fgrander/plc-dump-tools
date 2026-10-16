"""``s7dump`` document -> ``ExportModel``.

Pure function of the dump and a few settings, so it is tested on recorded fixtures without .NET.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Any, cast

from plcexport.common import ExtractText, ExtractWarning, Scope, UnitKind
from plcexport.connections_link import db_members, link, members_in, owner_of
from plcexport.extractors.s7classic.addresses import (
    area,
    collapse,
    io_direction,
    is_global_target,
    normalize,
)
from plcexport.extractors.s7classic.comm_calls import BLOCKS, FoundArea, FoundCall, find_calls
from plcexport.extractors.s7classic.connections import map_connections
from plcexport.extractors.s7classic.couplers import find_couplers
from plcexport.extractors.s7classic.stl import analyze
from plcexport.format.validate import BINARY_TEXT
from plcexport.model import (
    CATEGORIES,
    CONNECTIONS,
    BodyNetwork,
    CategoryCoverage,
    ConnectionsModel,
    ConnectionUse,
    Coverage,
    DataArea,
    ExportModel,
    ExportProject,
    ExportUnit,
    ExportVariable,
    ExportXref,
    Gap,
    HardwareModel,
    HwChannel,
    HwController,
    HwModule,
    HwNetwork,
    HwRack,
    SafetyModel,
    SafetySignature,
    StructDevice,
    StructFolder,
    StructTask,
    StructureModel,
    UnitBody,
)

PLATFORM = "siemens-step7-classic"
LANGUAGES = {
    "AWL": "STL", "KOP": "LAD", "FUP": "FBD", "UNKOWN": "", "UNKNOWN": "",  # sic: library
    # S7 Distributed Safety F-program languages
    "FAWL": "F-STL", "FFUP": "F-FBD", "FKOP": "F-LAD", "FCALL": "F-CALL",
}  # fmt: skip
SECTIONS = {"IN": "IN", "OUT": "OUT", "IN_OUT": "IN_OUT", "STAT": "STATIC", "TEMP": "TEMP",
            "RETURN": "RETURN"}  # fmt: skip
SCOPES: dict[str, Scope] = {
    "FB": "fb_interface",
    "FC": "fc_interface",
    "DB": "db_member",
    "UDT": "udt_member",
}
CODE_KINDS = ("OB", "FB", "FC")
HARDWARE_REASON = "other:direct route reads stations, CPUs, CPs and networks only"
PROTECTED_ONLY = "protected_only"


@dataclass(frozen=True)
class MappingOptions:
    extractor_id: str
    extractor_version: str
    text_language: str = "de"


def _kind(b: Mapping[str, Any]) -> tuple[UnitKind, dict[str, str]]:
    t = str(b["type"])
    if t == "DB" and b.get("instance_of"):
        return "IDB", {}
    if t in ("OB", "FB", "FC", "DB", "UDT"):
        return cast(UnitKind, t), {}
    if t in ("SFB", "SFC"):
        return "OTHER", {"type": t, "system": "true"}
    return "OTHER", {"type": t}


def _language(b: Mapping[str, Any]) -> str | None:
    if b["type"] not in (*CODE_KINDS, "SFB", "SFC"):
        return None
    raw = str(b.get("language") or "").upper()
    return LANGUAGES.get(raw, raw) or None


def _is_comm_block(b: Mapping[str, Any]) -> bool:
    """SFB/FB 8, 9, 12, 13, 14, 15 with the interface of the communication block for S7
    connections. A library's own FB 12 is none (seen: OSCAT)."""
    if b.get("type") not in ("FB", "SFB") or int(b.get("number") or 0) not in BLOCKS:
        return False
    return BLOCKS[int(b["number"])][1] <= {str(m.get("name")) for m in b.get("interface") or []}


class _Program:
    """Names and interfaces of one S7 program (for unit names and callee lookup)."""

    def __init__(self, prog: Mapping[str, Any], prefix: str) -> None:
        self.name = str(prog["name"])
        self.prefix = prefix
        self.blocks = list(prog["blocks"])
        self.has_comm_blocks = any(_is_comm_block(b) for b in self.blocks)
        self.by_key: dict[str, Mapping[str, Any]] = {}
        for b in self.blocks:
            self.by_key[normalize(f"{b['type']} {b['number']}")] = b
            if b.get("symbolic_name"):
                self.by_key[f'"{b["symbolic_name"]}"'] = b

    def unit_name(self, b: Mapping[str, Any]) -> str:
        base = b.get("symbolic_name") or f"{b['type']}{b['number']}"
        return f"{self.prefix}{base}"

    def resolve(self, target: str) -> Mapping[str, Any] | None:
        t = target.strip()
        return self.by_key.get(t) or self.by_key.get(normalize(t))

    def resolve_call(self, caller: Mapping[str, Any], target: str) -> Mapping[str, Any] | None:
        """The called block; for ``CALL #Valve`` (multi-instance) the static member's FB type."""
        if target.startswith("#"):
            member = next(
                (m for m in caller.get("interface", []) if f"#{m['name']}" == target), None
            )
            return self.resolve(str(member["type"])) if member else None
        return self.resolve(target)

    def callee_sections(
        self, caller: Mapping[str, Any]
    ) -> Any:  # Callable[[str], Mapping[str, str] | None]
        def lookup(target: str) -> Mapping[str, str] | None:
            callee = self.resolve_call(caller, target)
            if callee is None:
                return None
            return {
                str(m["name"]): SECTIONS.get(str(m.get("section")), "") for m in callee["interface"]
            }

        return lookup


def _qualify(prefix: str, operand: str) -> str:
    """In multi-program projects symbols are per program: ``"X".a`` -> ``"<prog>/X".a``."""
    if prefix and operand.startswith('"'):
        return f'"{prefix}{operand[1:]}'
    return operand


def _instance_of(p: _Program, b: Mapping[str, Any]) -> str | None:
    if not b.get("instance_of"):
        return None
    fb = p.resolve(str(b["instance_of"]))
    return p.unit_name(fb) if fb is not None else str(b["instance_of"])


_LABEL_DEF = re.compile(r"^(\S.{0,3}?)\s*:(?!=)")  # a label starts in the first column
_VALID_LABEL = re.compile(r"[A-Za-z_]\w{0,3}")
_JUMP_LINE = re.compile(r"^(\s+\S+\s+)(\S.*?)\s*$")


def readable_labels(networks: list[list[str]]) -> tuple[list[list[str]], int]:
    """The STL lines of one block with unreadable jump labels replaced, and their count.

    Some projects hold no usable label names for a block (seen in projects written for
    INSEVIS controllers): the library then returns arbitrary bytes, also control characters.
    Such a label gets a generated name (``M001`` …, as STEP 7 shows labels whose names are
    lost), the same at its definition and at every jump to it. Readable labels stay.
    """
    defined: list[str] = []
    for lines in networks:
        for line in lines:
            if not line.startswith("//") and (m := _LABEL_DEF.match(line)):
                defined.append(m.group(1))
    bad = [x for x in dict.fromkeys(defined) if not _VALID_LABEL.fullmatch(x)]
    if not bad:
        return networks, 0
    taken = {x for x in defined if x not in bad}
    names: dict[str, str] = {}
    n = 0
    for label in bad:
        n += 1
        while f"M{n:03d}" in taken:
            n += 1
        names[label] = f"M{n:03d}"
    out: list[list[str]] = []
    for lines in networks:
        fixed = []
        for line in lines:
            if line.startswith("//"):
                fixed.append(line)
            elif (m := _LABEL_DEF.match(line)) and m.group(1) in names:
                rest = line[line.index(":", len(m.group(1))) :]
                fixed.append(f"{names[m.group(1)]}{rest}")
            elif (j := _JUMP_LINE.match(line)) and j.group(2) in names:
                fixed.append(f"{j.group(1)}{names[j.group(2)]}")
            else:
                fixed.append(line)
        out.append(fixed)
    return out, len(bad)


def _layout_fits(b: Mapping[str, Any]) -> bool:
    """the library's DB layout ends exactly at the compiled block's data size. It does not
    for arrays of odd-length strings (the library leaves out the fill byte per element); such a
    DB keeps no offsets (an offset is never estimated)."""
    ends = [
        int(str(m["offset"]).split(".")[0]) + int(m.get("length") or 0)
        for m in b["interface"]
        if m.get("offset") is not None
    ]
    if not ends:
        return True
    end = max(ends)
    return end + end % 2 == b.get("mc7_size")


_STRING_ARRAY = re.compile(r"ARRAY\s*\[[^\]]*\]\s*OF\s+STRING\s*\[\s*(\d+)\s*\]", re.IGNORECASE)


_COMPOUND = re.compile(r"\s*(STRING|ARRAY|STRUCT|DATE_AND_TIME)\b", re.IGNORECASE)


def _bits(offset: Any) -> int:
    byte, bit = str(offset).split(".")
    return int(byte) * 8 + int(bit)


def _shape(members: list[Any], path: str, start: int, end: int | None) -> str | None:
    """Why the members do not lie one after the other inside ``start``..``end`` (bits), or None.
    Also refuses the one layout the library is known to get wrong."""
    cursor = start
    after: str | None = None  # the string, array or structure before this member
    for m in members:
        name = f"{path}{m['name']}"
        if m.get("offset") is None:
            return f"{name} has no offset"
        at = _bits(m["offset"])
        compound = bool(m.get("members")) or bool(_COMPOUND.match(str(m.get("type"))))
        # STEP 7 starts a string, array or structure on an even byte, and the member after
        # one too. The library leaves out the fill byte after one of odd length (seen: a
        # BOOL at 25.0 after a STRING[5] that ends at 25.0; STEP 7 puts it at 26.0).
        if (compound or after) and at % 16:
            return (
                f"{name} at {m['offset']} "
                + (f"follows {after} and " if after else "")
                + "has to start on an even byte"
            )
        if at < cursor:
            return f"{name} at {m['offset']} starts before the end of the member before it"
        size = 1 if str(m.get("type")).upper() == "BOOL" else int(m.get("length") or 0) * 8
        if end is not None and at + size > end:
            return f"{name} at {m['offset']} ends outside {path.rstrip('.')}"
        odd = _STRING_ARRAY.search(str(m.get("type")))
        if odd and int(odd.group(1)) % 2:
            return (
                f"{name} is an array of odd-length strings, which the library lays out without "
                "their fill bytes"
            )
        if reason := _shape(m.get("members") or [], f"{name}.", at, at + size):
            return reason
        cursor = at + max(size, 1)
        after = name if compound else None
    return None


def _disagreement(db: str, member: Mapping[str, Any], udt: Mapping[str, Any]) -> str | None:
    """Where a data block's copy of the type's members differs from the type's own layout."""
    base = _bits(member["offset"])

    def walk(copies: list[Any], declared: list[Any], path: str) -> str | None:
        by_name = {c["name"]: c for c in copies}
        for d in declared:
            c = by_name.get(d["name"])
            if c is None or c.get("offset") is None or d.get("offset") is None:
                continue
            if _bits(c["offset"]) - base != _bits(d["offset"]):
                return (
                    f"{db} lists {path}{d['name']} at {c['offset']}, the type says "
                    f"{d['offset']} after {member['offset']}"
                )
            if reason := walk(
                c.get("members") or [], d.get("members") or [], f"{path}{d['name']}."
            ):
                return reason
        return None

    return walk(member.get("members") or [], udt["interface"], f"{member['name']}.")


def _udt_layout(udt: Mapping[str, Any], program: _Program) -> str | None:
    """Why the library's layout of a data type is not reliable, or None.

    A data type has no compiled size to check the layout against, as ``_layout_fits`` does for a
    data block. Three checks instead: the members lie one after the other from 0.0; there is no
    array of odd-length strings; and every data block of the program that uses the type, and
    whose own layout fits its size, lists the type's members where the type says.
    """
    members = udt["interface"]
    if not members:
        return None
    if members[0].get("offset") is not None and _bits(members[0]["offset"]) != 0:
        return f"the first member is at {members[0]['offset']}, not at 0.0"
    if reason := _shape(members, "", 0, None):
        return reason

    def uses(ms: list[Any]) -> list[Mapping[str, Any]]:
        found = []
        for m in ms:
            typ = str(m.get("type") or "")
            if (program.resolve(typ) or program.resolve(f'"{typ}"')) is udt:
                if m.get("offset") is not None and m.get("members"):
                    found.append(m)
            else:
                found += uses(m.get("members") or [])
        return found

    for b in program.blocks:
        if b["type"] != "DB" or not _layout_fits(b):
            continue
        for member in uses(b["interface"]):
            if reason := _disagreement(program.unit_name(b), member, udt):
                return reason
    return None


def _members(
    unit: str,
    scope: Scope,
    prefix: str,
    parent: str | None,
    members: list[Any],
    lang: str,
    offsets: bool = True,
    positions: bool = False,
) -> list[ExportVariable]:
    out: list[ExportVariable] = []
    for index, m in enumerate(members):
        path = f"{parent or prefix}.{m['name']}"
        section = SECTIONS.get(str(m.get("section"))) if m.get("section") else None
        out.append(
            ExportVariable(
                declared_in=unit,
                scope=scope,
                symbolic_path=path,
                data_type=str(m.get("type") or "Unknown"),
                section=cast(Any, section),
                parent_path=parent,
                start_value=m.get("start"),
                comments={lang: m["comment"]} if m.get("comment") else {},
                # the library's layout, for the members of data blocks and of
                # data types; never for parameters and variables of code blocks
                offset=m.get("offset")
                if scope in ("db_member", "udt_member") and offsets
                else None,
                # a data type without offsets keeps its declaration order
                position=index if positions else None,
            )
        )
        # a compound IN_OUT parameter is a pointer in the instance DB: what it points to (its
        # members) is not in this block, so the members have no offset here
        inner = offsets and m.get("section") != "IN_OUT"
        out += _members(unit, scope, prefix, path, m.get("members") or [], lang, inner, positions)
    return out


TEXT_KEYS = frozenset({"title", "comment", "description"})


def _unify_newlines(node: Any, key: str | None = None) -> Any:
    """The document with ``\\n`` as the only line break in titles and comments. The library
    joins comment lines with the line break of the platform it runs on, so without this a
    Windows and a Linux export of one project would differ."""
    if isinstance(node, dict):
        return {k: _unify_newlines(v, k) for k, v in node.items()}
    if isinstance(node, list):
        return [_unify_newlines(v, key) for v in node]
    if isinstance(node, str) and key in TEXT_KEYS:
        return node.replace("\r\n", "\n").replace("\r", "\n")
    return node


def to_model(dump: Mapping[str, Any], opts: MappingOptions) -> ExportModel:
    dump = _unify_newlines(dump)
    proj = dump["project"]
    stored = str(proj["languages"]["stored"])
    lang = opts.text_language if stored in ("", "und") else stored
    programs = list(dump["programs"])
    multi = len(programs) > 1
    # a program's prefix and folder: its name, or station/name when names repeat across stations
    names = [str(prog["name"]) for prog in programs]
    labels = {
        id(prog): (
            f"{prog['station']}/{prog['name']}"
            if names.count(str(prog["name"])) > 1 and prog.get("station")
            else str(prog["name"])
        )
        for prog in programs
    }
    m = ExportModel(
        project=ExportProject(
            platform_id=PLATFORM,
            platform_version=proj.get("step7_version"),
            controller=dump["cpus"][0]["name"] if dump["cpus"] else None,
            line_or_machine=proj.get("name"),
            extractor_id=opts.extractor_id,
            extractor_version=opts.extractor_version,
            languages=(lang,),
        )
    )
    gaps: list[Gap] = []
    tasks: list[StructTask] = []
    folders: list[StructFolder] = []
    source_problems = False
    safety_units: list[str] = []
    table_station: dict[str, str | None] = {}  # symbol table -> station of its program
    signatures: list[SafetySignature] = []
    comm_calls: list[_PendingCall] = []  # resolved once connections and variables exist
    comm_protected: list[str] = []  # protected callers in programs with communication blocks

    for prog in programs:
        p = _Program(prog, f"{labels[id(prog)]}/" if multi else "")
        units_here: list[str] = []
        generated: dict[str, str] = {}
        for s in prog["sources"]:
            sname = f"{p.prefix}{s['name']}.{s['kind']}"
            for d in s.get("defines") or []:
                defined = p.resolve(d) or p.resolve(f'"{d}"')
                if defined is not None:
                    generated[p.unit_name(defined)] = sname
            m.units.append(
                ExportUnit(
                    name=sname, kind="OTHER", language=s["kind"].upper(), files=(),
                    attributes={"type": "source", "source_kind": s["kind"]},
                    folder=labels[id(prog)] if multi else None,
                )
            )  # fmt: skip
            units_here.append(sname)
            text = s.get("text")
            if text is not None and BINARY_TEXT.search(text):
                # a "source" whose file is not text (a Siemens example has 12 binary bytes): no
                # body, reported as corrupt; the rest of the project is still exported
                source_problems = True
                gaps.append(Gap("program_units", sname, "corrupt"))
                m.warnings.append(
                    ExtractWarning("source_not_text", f"{sname}: source file is not text", sname)
                )
            elif text is not None:
                m.unit_bodies[sname] = UnitBody(cast(Any, s["kind"]), (), text.rstrip("\n"))
            if s.get("errors") and not (text is not None and BINARY_TEXT.search(text)):
                source_problems = True
                gaps.append(Gap("program_units", sname, "corrupt"))

        for b in p.blocks:
            name = p.unit_name(b)
            kind, extra = _kind(b)
            attrs = {"address": f"{b['type']} {b['number']}", **extra}
            for key in ("family", "version", "author"):
                if b.get(key):
                    attrs[key] = str(b[key])
            if name in generated:
                attrs["generated_from"] = generated[name]
            if b.get("attributes"):  # Attributes tab, as the library reads it
                attrs["block_attributes"] = json.dumps(
                    b["attributes"], ensure_ascii=False, sort_keys=True
                )
            scope = SCOPES.get("DB" if kind == "IDB" else kind)  # instance DBs: db_member too
            protected = bool(b.get("know_how_protected"))
            # F-blocks (header attribute bit 6) are safety units, exported as found
            f_block = bool(b.get("f_block"))
            if f_block:
                safety_units.append(name)
                if b.get("checksum") is not None:
                    signatures.append(SafetySignature(name, str(b["checksum"]), "mc7_checksum"))
                if (collective := _collective_signature(name, b)) is not None:
                    signatures.append(collective)
            m.units.append(
                ExportUnit(
                    name=name,
                    kind=kind,
                    language=_language(b),
                    files=(),
                    number=int(b["number"]),
                    instance_of=_instance_of(p, b),
                    protected=protected,
                    attributes=attrs,
                    safety=f_block,
                    folder=labels[id(prog)] if multi else None,
                    path_prefix=f'"{name}"' if scope else None,
                    variable_scope=scope,
                )
            )
            units_here.append(name)
            if b.get("title"):
                m.texts.append(ExtractText(name, "title", lang, str(b["title"]).strip()))
            if b.get("description"):
                m.texts.append(ExtractText(name, "comment", lang, str(b["description"])))
            if b.get("actual_values_read") is False:
                m.warnings.append(
                    ExtractWarning(
                        "db_actual_values_unread",
                        f"{name}: the stored actual values do not fit the declaration; "
                        "members exported with their start values only",
                        name,
                    )
                )
            if scope:
                fits = scope != "db_member" or _layout_fits(b)
                if not fits:
                    m.warnings.append(
                        ExtractWarning(
                            "db_layout_mismatch",
                            f"{name}: the library's layout does not fill the block's "
                            f"{b.get('mc7_size')} data bytes; members exported without offsets",
                            name,
                        )
                    )
                unreliable = _udt_layout(b, p) if kind == "UDT" else None
                if unreliable:
                    fits = False
                    m.warnings.append(
                        ExtractWarning(
                            "udt_layout_mismatch",
                            f"{name}: {unreliable}; members exported without offsets",
                            name,
                        )
                    )
                m.variables += _members(
                    name,
                    scope,
                    f'"{name}"',
                    None,
                    b["interface"],
                    lang,
                    offsets=fits,
                    positions=bool(unreliable),
                )
            if protected:
                gaps.append(Gap("program_units", name, "protected"))
                if p.has_comm_blocks and not _is_comm_block(b) and b["type"] in CODE_KINDS:
                    comm_protected.append(name)  # its calls cannot be read
            if kind == "OB":
                tasks.append(StructTask(name, "ob", units=(name,)))
            if b["type"] in CODE_KINDS and b["networks"] and not protected:
                networks = []
                lookup = p.callee_sections(b)
                bodies, unreadable = readable_labels(
                    [[str(line) for line in nw["stl"]] for nw in b["networks"]]
                )
                if unreadable:
                    m.warnings.append(
                        ExtractWarning(
                            "stl_label_unreadable",
                            f"{name}: {unreadable} jump label(s) have no readable name in the "
                            "project; generated names (M001 ...) are used",
                            name,
                        )
                    )
                for nw, stl in zip(b["networks"], bodies, strict=True):
                    networks.append(
                        BodyNetwork(
                            int(nw["no"]),
                            "\n".join(stl) or "// (empty network)",
                            {lang: nw["title"]} if nw.get("title") else {},
                            {lang: nw["comment"]} if nw.get("comment") else {},
                        )
                    )
                    for call in find_calls(nw.get("raw_stl") or [], p.resolve):
                        comm_calls.append(_PendingCall(name, int(nw["no"]), prog, p, call, f_block))
                    result = analyze(stl, lookup)
                    for r in result.refs:
                        if r.target_kind == "variable" and not is_global_target(r.target_text):
                            continue  # no locals, stack, registers or indirect operands
                        target = r.target_text
                        if r.target_kind == "unit" and (callee := p.resolve_call(b, target)):
                            target = p.unit_name(callee)
                        else:
                            target = _qualify(p.prefix, target)
                        m.xrefs.append(
                            ExportXref(name, r.target_kind, target, r.access, int(nw["no"]),
                                       r.line + 1, r.via_param)
                        )  # fmt: skip
                    for line, text in result.warnings:
                        m.warnings.append(
                            ExtractWarning("stl_unclassified",
                                           f"{name} NW{nw['no']} line {line + 1}: {text}", name)
                        )  # fmt: skip
                m.unit_bodies[name] = UnitBody("stl", tuple(networks))

        symbols = [s for s in prog["symbols"] if s.get("address") and area(s["address"]) != "block"]
        # a row with an address but no name is not a symbol (STEP 7 keeps such incomplete rows)
        nameless = [s for s in symbols if not str(s.get("symbol") or "").strip()]
        symbols = [s for s in symbols if str(s.get("symbol") or "").strip()]
        if nameless:
            commented = sum(1 for s in nameless if s.get("comment"))
            m.warnings.append(
                ExtractWarning(
                    "symbol_without_name",
                    f"{p.prefix}Symbols: {len(nameless)} symbol table row(s) have an address but "
                    f"no name and are left out ({commented} of them with a comment)",
                )
            )
        if symbols:
            table = f"{p.prefix}Symbols"
            table_station[table] = prog.get("station")
            m.units.append(ExportUnit(table, "TAG_TABLE", None, (),
                                      folder=labels[id(prog)] if multi else None))  # fmt: skip
            units_here.append(table)
            for s in symbols:
                m.variables.append(
                    ExportVariable(
                        declared_in=table,
                        scope="global_tag",
                        symbolic_path=f'"{p.prefix}{s["symbol"]}"',
                        data_type=str(s.get("type") or "Unknown"),
                        io_direction=io_direction(s["address"]),
                        address=collapse(str(s["address"])),  # "Q       0.1" -> "Q 0.1"
                        comments={lang: s["comment"]} if s.get("comment") else {},
                    )
                )
        if multi:
            folders.append(StructFolder(labels[id(prog)], tuple(sorted(units_here))))

    m.hardware = _hardware(dump)
    m.hardware = replace(m.hardware, channels=_channels(dump, m.variables, table_station))
    m.structure = StructureModel(
        devices=tuple(StructDevice(s["name"], s.get("type")) for s in dump["stations"]),
        tasks=tuple(tasks),
        folders=tuple(folders),
    )
    for chart in dump.get("pcs7_charts") or []:
        gaps.append(Gap("program_units", f"{chart['kind'].upper()} {chart['location']}/"
                                         f"{chart['name']}", "not_exported_cfc_sfc"))  # fmt: skip
    for e in dump.get("errors") or []:
        m.warnings.append(ExtractWarning("s7dump_error", f"{e['where']}: {e['message']}"))
    maintained = [x for x in proj["languages"].get("maintained") or [] if x != lang]
    m.platform = {
        "encoding": proj["encoding"],
        "library": proj["kind"] == "library",
        "mnemonic": proj["mnemonic"]["exported"],
        "mnemonic_project": proj["mnemonic"]["project"],
        "pcs7": bool(proj.get("pcs7")),
        "s7dump": dump["tool"]["version"],
        "toolbox_library": dump["tool"]["library_version"],
    }
    m.safety = SafetyModel(
        units=tuple(sorted(safety_units)),
        signatures=tuple(sorted(signatures, key=lambda g: (g.scope, g.kind, g.value))),
    )
    blocks = [b for prog in programs for b in prog["blocks"]]
    m.coverage = _coverage(m, gaps, source_problems, maintained, _safety_check(blocks))
    if "connections" in dump:  # 005; a dump of an older s7dump carries no connection data
        _connections(m, dump, comm_calls, comm_protected)
    code = [u for u in m.units if u.kind in CODE_KINDS]
    if code and all(u.protected for u in code):
        m.warnings.append(
            ExtractWarning(PROTECTED_ONLY, "every program block is know-how protected")
        )
    return m


@dataclass(frozen=True)
class _PendingCall:
    unit: str
    network_no: int
    prog: Mapping[str, Any]
    program: _Program
    call: FoundCall
    safety: bool


def _connections(
    m: ExportModel, dump: Mapping[str, Any], calls: list[_PendingCall], protected: list[str]
) -> None:
    """configured connections, the calls that use them and the per-project findings, with
    their coverage (optional category of the format). Linking and findings are the shared rules
    of ``connections_link``."""
    mapped = map_connections(
        dump, {x.ref for x in m.hardware.modules}, {n.ref for n in m.hardware.networks}
    )
    owners = {owner_of(c) for c in mapped.connections if c.kind == "s7"}
    members = db_members(m.variables)

    def owner(prog: Mapping[str, Any]) -> str | None:
        key = f"{prog.get('station') or '-'}/{prog.get('cpu')}"
        if key in owners or not prog.get("station"):
            return key
        # the program's CPU name differs from its module
        in_station = [k for k in owners if k.startswith(f"{prog['station']}/")]
        return in_station[0] if len(in_station) == 1 else None

    linked = link(
        mapped.connections,
        [
            (
                owner(pc.prog),
                ConnectionUse(
                    unit=pc.unit,
                    block=pc.call.block,
                    called=pc.call.called,
                    network_no=pc.network_no,
                    id=pc.call.id,
                    r_id=pc.call.r_id,
                    areas=tuple(_data_area(a, pc.program, members) for a in pc.call.areas),
                    len=pc.call.len,
                    safety=pc.safety,
                ),
            )
            for pc in calls
        ],
        {f"{p.get('station') or '-'}/{p.get('cpu')}" for p in dump.get("programs") or []},
    )
    m.connections = ConnectionsModel(
        connections=linked.connections,
        uses=linked.uses,
        couplers=tuple(find_couplers(m.hardware)),  # PN/PN and DP/DP couplers
        findings=(*mapped.findings, *linked.findings),
    )
    m.warnings += mapped.warnings
    reasons = list(mapped.reasons)
    if protected:
        reasons.append(f"calls in {len(protected)} protected block(s) not readable")
        unreadable = tuple(Gap(CONNECTIONS, name, "protected") for name in protected)
        m.coverage = replace(m.coverage, gaps=(*m.coverage.gaps, *unreadable))
    if not m.connections.item_count():
        cov = CategoryCoverage("unavailable", "not_in_project")
    elif reasons:
        cov = CategoryCoverage("partial", "other:" + "; ".join(reasons))
    else:
        cov = CategoryCoverage("delivered")
    m.coverage = replace(m.coverage, categories={**m.coverage.categories, CONNECTIONS: cov})


def _data_area(
    a: FoundArea, program: _Program, members: dict[str, list[tuple[int, str]]]
) -> DataArea:
    """A call's data area; a local area in a data block names the members it covers (T052
    offsets). A remote area (GET/PUT ``ADDR_i``) lies in the partner PLC: no local names."""
    if a.unassigned or a.unresolved is not None:
        return DataArea(a.param, a.role, unresolved=a.unresolved, unassigned=a.unassigned)
    db = None
    names: tuple[str, ...] = ()
    if a.role != "remote" and a.db_number:
        block = program.resolve(f"DB {a.db_number}")
        if block is not None:
            db = program.unit_name(block)
            names = members_in(members, db, a.start_byte or 0, a.length_bytes)
    return DataArea(a.param, a.role, a.pointer, db, a.start, a.length_bytes, names)


def _module_place(d: Mapping[str, Any]) -> tuple[str, str, str]:
    """(rack ref, rack label, module ref) of a dump module: a slot of a central rack, or a slot
    of a PROFIBUS/PROFINET device, which is its own "rack" on its IO system."""
    station = d.get("station") or "-"
    sub = f".{d['subslot']}" if d.get("subslot") else ""
    if d.get("device") is not None:
        system = d.get("io_system") or "IO system"
        rack_ref = f"{station}/{system} #{d['device']}"
        label = f"{d.get('device_name') or d['name']} (device {d['device']} on {system})"
        return rack_ref, label, f"{rack_ref}.{d['slot']}{sub}"
    rack = d.get("rack") or 0
    return f"{station}/R{rack}", f"{station} rack {rack}", f"{station}/{rack}.{d['slot']}{sub}"


def _address_ranges(d: Mapping[str, Any]) -> tuple[str, ...]:
    """``%I256.0-%I263.7`` per input range, then the output ranges (lengths are bytes)."""
    return tuple(
        f"%{area}{r['start']}.0-%{area}{r['start'] + r['length'] - 1}.7"
        for area, key in (("I", "inputs"), ("Q", "outputs"))
        for r in d.get(key) or []
        if r["length"] > 0
    )


_IO_ADDRESS = re.compile(r"^P?([IQ])[BWD]?(\d+)(?:\.\d)?$")


def _channels(
    dump: Mapping[str, Any], variables: list[ExportVariable], table_station: dict[str, str | None]
) -> tuple[HwChannel, ...]:
    """One channel per I/O symbol whose address lies in a module's input or output range, in the
    station of the symbol's program (I/O tags linked to the hardware). The module is
    the one of the symbol's first byte: a word or double word may reach into the next module of
    its DP slave or IO device (seen: ``QD 342`` over ``312-343`` and ``344-357``)."""
    ranges = [
        (d.get("station"), area, r["start"], r["start"] + r["length"], _module_place(d)[2])
        for d in dump.get("modules") or []
        for area, key in (("I", "inputs"), ("Q", "outputs"))
        for r in d.get(key) or []
        if r["length"] > 0
    ]
    channels: dict[str, HwChannel] = {}
    for v in variables:
        if v.scope != "global_tag" or not v.address:
            continue
        found = _IO_ADDRESS.match(normalize(v.address))
        if not found:
            continue
        area, byte = found.group(1), int(found.group(2))
        station = table_station.get(v.declared_in)
        for st, a, lo, hi, module_ref in ranges:
            if a == area and lo <= byte < hi and station in (None, st):
                ref = f"{module_ref}/{v.address}"
                channels.setdefault(ref, HwChannel(ref, module_ref, v.address, v.symbolic_path))
                break
    return tuple(sorted(channels.values(), key=lambda c: c.ref))


def _hardware(dump: Mapping[str, Any]) -> HardwareModel:
    racks: dict[str, HwRack] = {}
    modules: list[HwModule] = []
    # every module from the project's hardware tables; the library's CPU/CP entries only
    # fill gaps (order number of a CPU, projects dumped by an older s7dump)
    library = {
        (item.get("station") or "-", item.get("slot")): item
        for item in [*dump["cpus"], *dump["cps"]]
    }
    for d in dump.get("modules") or []:
        rack_ref, label, ref = _module_place(d)
        racks.setdefault(rack_ref, HwRack(rack_ref, label))
        lib = library.get((d["station"], d["slot"])) if d.get("device") is None else None
        lib_order = lib.get("order_no") if lib and not d.get("subslot") else None
        modules.append(
            HwModule(
                ref=ref,
                type=str(d["name"]),
                rack=rack_ref,
                slot=d["slot"],
                order_no=d.get("order_no") or lib_order,
                firmware=d.get("firmware"),
                address_ranges=_address_ranges(d),
            )
        )
    placed = {(m.rack, m.slot) for m in modules}
    # the library may report a CPU/CP without its station; it is the hardware-table module
    # of the same name and slot
    named = {
        (str(d["name"]), d["slot"]) for d in dump.get("modules") or [] if d.get("device") is None
    }
    for item in [*dump["cpus"], *dump["cps"]]:
        station = item.get("station") or "-"
        rack_ref = f"{station}/R{item.get('rack', 0)}"
        if (rack_ref, item.get("slot")) in placed:
            continue
        if not item.get("station") and (str(item["name"]), item.get("slot")) in named:
            continue
        racks.setdefault(rack_ref, HwRack(rack_ref, f"{station} rack {item.get('rack', 0)}"))
        modules.append(
            HwModule(
                ref=f"{station}/{item.get('rack', 0)}.{item.get('slot', 0)}",
                type=str(item["name"]),  # module name, e.g. "CPU 315-2 PN/DP" or "CP 343-1"
                rack=rack_ref,
                slot=item.get("slot"),
                order_no=item.get("order_no"),
            )
        )
    # modules with an Ethernet interface that the library does not recognize (unknown CPU or CP
    # types, PROFINET IO devices such as drives): s7dump finds them through the hardware tables.
    # An IO device gets its own "rack" (the device on its IO system), not a slot of the PLC rack.
    known = {(m.rack, m.slot) for m in modules}
    for e in dump.get("ethernet") or []:
        if not e.get("module") or e.get("slot") is None:
            continue
        station = e.get("station") or "-"
        if e.get("device"):
            system = e.get("io_system") or "IO system"
            rack_ref = f"{station}/{system} #{e['device']}"
            label = f"{e['module']} (device {e['device']} on {system})"
            ref = f"{rack_ref}.{e['slot']}"
        else:
            rack_ref = f"{station}/R{e.get('rack') or 0}"
            label = f"{station} rack {e.get('rack') or 0}"
            ref = f"{station}/{e.get('rack') or 0}.{e['slot']}"
        if (rack_ref, e["slot"]) in known:
            continue
        racks.setdefault(rack_ref, HwRack(rack_ref, label))
        modules.append(HwModule(ref=ref, type=str(e["module"]), rack=rack_ref, slot=e["slot"]))
        known.add((rack_ref, e["slot"]))
    return HardwareModel(
        controllers=tuple(
            HwController(f"cpu:{c['name']}", c["name"], c.get("type"), c.get("order_no"))
            for c in dump["cpus"]
        ),
        racks=tuple(racks.values()),
        modules=tuple(modules),
        networks=tuple(
            HwNetwork(_network_ref(n), n["kind"], n.get("address"), n.get("device_name"),
                      n.get("subnet"))
            for n in dump["networks"]
        ),
    )  # fmt: skip


def _network_ref(n: Mapping[str, Any]) -> str:
    """``<station>/<node>[ #<device>]/<kind>``: names repeat across stations (three "CPU 315F-2
    PN/DP") and within one (several drives of the same type). Dumps without ``station`` keep the
    old ``<node>/<kind>``."""
    node = f"{n['node']} #{n['device']}" if n.get("device") else str(n["node"])
    return f"{n['station']}/{node}/{n['kind']}" if n.get("station") else f"{node}/{n['kind']}"


F_SHARED_DB = "F_GLOBDB"  # S7 Distributed Safety's F-shared DB (fixed symbolic name)
COLLECTIVE_SIGNATURE = "f_collective_signature"
SAFETY_REASON_NO_SIGNATURE = (
    "other:F-blocks exported as found with their MC7 checksums; no collective F-signature "
    "found in F_GLOBDB.F_PROG_SIG"
)


def _collective_signature(name: str, b: Mapping[str, Any]) -> SafetySignature | None:
    """``F_GLOBDB.F_PROG_SIG`` as found: the actual value, else the start value; never zero."""
    if b["type"] != "DB" or (b.get("symbolic_name") or "") != F_SHARED_DB:
        return None
    member = next((x for x in b.get("interface") or [] if x["name"] == "F_PROG_SIG"), None)
    value = member and (member.get("actual") or member.get("start"))
    digits = str(value or "").upper().removeprefix("DW#16#").replace("_", "")
    if not value or not digits.strip("0"):
        return None
    return SafetySignature(f"{name}.F_PROG_SIG", str(value), COLLECTIVE_SIGNATURE)


def _safety_check(blocks: list[Mapping[str, Any]]) -> tuple[bool, int]:
    """(F-block flag reported by s7dump, number of blocks whose flag is unknown or unread)."""
    checked = any("f_block" in b for b in blocks)
    unknown = sum(
        1
        for b in blocks
        if ("f_block" in b and b["f_block"] is None)
        or (b.get("errors") and b.get("checksum") is None)
    )
    return checked, unknown


def _safety_coverage(m: ExportModel, check: tuple[bool, int]) -> CategoryCoverage:
    checked, unknown = check
    if not checked:  # older s7dump: no F-block flag in the dump
        return CategoryCoverage("unavailable", "other:safety program detection is not built yet")
    open_ = f"{unknown} block(s) could not be checked for the F-block flag"
    if m.safety.units:
        signed = any(g.kind == COLLECTIVE_SIGNATURE for g in m.safety.signatures)
        if signed and not unknown:
            return CategoryCoverage("delivered")
        reason = SAFETY_REASON_NO_SIGNATURE if not signed else f"other:{open_}"
        if signed is False and unknown:
            reason = f"{SAFETY_REASON_NO_SIGNATURE}; {open_}"
        return CategoryCoverage("partial", reason)
    if unknown:
        return CategoryCoverage("unavailable", f"other:no F-blocks found, but {open_}")
    return CategoryCoverage("unavailable", "not_in_project")


def _coverage(
    m: ExportModel,
    gaps: list[Gap],
    source_problems: bool,
    maintained: list[str],
    safety_check: tuple[bool, int] = (False, 0),
) -> Coverage:
    counts = m.item_counts()
    cats: dict[str, CategoryCoverage] = {}
    for cat in CATEGORIES:
        cats[cat] = (
            CategoryCoverage("delivered") if counts[cat] else
            CategoryCoverage("unavailable", "not_in_project")
        )  # fmt: skip
    if source_problems:
        cats["program_units"] = CategoryCoverage("partial", "corrupt")
    if counts["hardware"]:
        cats["hardware"] = CategoryCoverage("partial", HARDWARE_REASON)
    cats["safety"] = _safety_coverage(m, safety_check)
    cats["hmi"] = CategoryCoverage("unavailable", "unsupported")
    if maintained:
        gaps.append(
            Gap("program_units", f"comment languages {', '.join(sorted(maintained))}",
                "other:additional comment languages need the worker route")
        )  # fmt: skip
    return Coverage(categories=cats, gaps=tuple(gaps))
