"""``connections.json`` of the common format (contracts/connections-json.md).

One place for the three directions: model → document (writer), document → model (reader) and
the rules a document must keep (validator). Additive in format version 1: an export without the
file has no connection content.
"""

from __future__ import annotations

import re
from collections.abc import Collection, Mapping
from dataclasses import asdict
from typing import Any

from plcexport.format.canonical import compact
from plcexport.model import (
    COMM_BLOCKS,
    CONNECTION_KINDS,
    COUPLER_KINDS,
    CallValue,
    Connection,
    ConnectionEnd,
    ConnectionPartner,
    ConnectionsModel,
    ConnectionUse,
    Coupler,
    DataArea,
    InterfaceFinding,
    TransferArea,
    ValueDifference,
)

FILE = "connections.json"
_ID = re.compile(r"^0x[0-9A-F]{4}$")
_R_ID = re.compile(r"^0x[0-9A-F]{8}$")
# two hex bytes (STEP 7, TIA without ACC), or as TIA writes it with SIMATIC ACC
_TSAP = re.compile(r"^(?:[0-9A-F]{2}\.[0-9A-F]{2}|SIMATIC-ACC[0-9A-F]+)$")
_ROLES = ("send", "receive", "remote")
_VALUE_KEYS = ("value", "unresolved", "unassigned")


def hex_id(value: int) -> str:
    """A connection ID as the format writes it: ``0x0010``."""
    return f"0x{value:04X}"


def shown_id(text: str) -> str:
    """A connection ID as NetPro shows it: hex without prefix and leading zeros (``10``)."""
    return f"{int(text, 16):X}" if text.lower().startswith("0x") else text


# ------------------------------------------------------------------ model -> document
def _value(v: CallValue | None) -> dict[str, Any] | None:
    if v is None:
        return None
    if v.value is not None:
        return {"value": v.value}
    if v.unresolved is not None:
        return {"unresolved": v.unresolved}
    return {"unassigned": True}


def _area(a: DataArea) -> dict[str, Any]:
    if a.unassigned:
        return {"param": a.param, "role": a.role, "unassigned": True}
    if a.unresolved is not None:
        return {"param": a.param, "role": a.role, "unresolved": a.unresolved}
    return compact(
        {
            "param": a.param,
            "role": a.role,
            "pointer": a.pointer,
            "db": a.db,
            "start": a.start,
            "length_bytes": a.length_bytes,
            "members": list(a.members),
        }
    )


def _finding(f: InterfaceFinding) -> dict[str, Any]:
    return compact(asdict(f))


def _connection(c: Connection) -> dict[str, Any]:
    if c.details == "not_read":
        return compact(
            {
                "ref": c.ref,
                "name": c.name,
                "kind": c.kind,
                "type_id": c.type_id,
                "details": c.details,
                "local": compact({"module": c.local.module, "id": c.local.id}),
            }
        )
    partner = compact(asdict(c.partner)) | {"specified": c.partner.specified}
    return compact(
        {
            "ref": c.ref,
            "name": c.name,
            "kind": c.kind,
            "type_id": c.type_id,
            "details": c.details,
            "local": compact(asdict(c.local)),
            "partner": dict(sorted(partner.items())),
            "active": c.active,
            "one_way": c.one_way,
            "sources": dict(sorted(c.sources.items())),
            "differences": [asdict(d) for d in c.differences],
            "safety": c.safety or None,
        }
    )


def _use(u: ConnectionUse) -> dict[str, Any]:
    return compact(
        {
            "unit": u.unit,
            "network_no": u.network_no,
            "line": u.line,
            "block": u.block,
            "called": u.called,
            "id": _value(u.id),
            "r_id": _value(u.r_id),
            "areas": [_area(a) for a in u.areas],
            "len": _value(u.len),
            "connection": u.connection,
            "findings": [_finding(f) for f in u.findings],
            "safety": u.safety or None,
        }
    )


def _coupler(c: Coupler) -> dict[str, Any]:
    return compact(
        {
            "ref": c.ref,
            "kind": c.kind,
            "order_no": c.order_no,
            "address": c.address,
            "transfer_areas": [
                compact(asdict(t) | {"symbols": list(t.symbols)}) for t in c.transfer_areas
            ],
            "safety": c.safety or None,
        }
    )


def to_doc(cm: ConnectionsModel) -> dict[str, Any]:
    cm = cm.sorted()
    return {
        "connections": [_connection(c) for c in cm.connections],
        "uses": [_use(u) for u in cm.uses],
        "couplers": [_coupler(c) for c in cm.couplers],
        "findings": [_finding(f) for f in cm.findings],
    }


# ------------------------------------------------------------------ document -> model
def _read_value(d: Mapping[str, Any] | None) -> CallValue | None:
    if d is None:
        return None
    return CallValue(d.get("value"), d.get("unresolved"), bool(d.get("unassigned")))


def _read_finding(d: Mapping[str, Any]) -> InterfaceFinding:
    return InterfaceFinding(
        d["code"], d.get("connection"), d.get("unit"), d.get("network_no"), d.get("coupler")
    )


def from_doc(doc: Mapping[str, Any] | None) -> ConnectionsModel:
    """The model of a ``connections.json`` document; empty for an export without the file."""
    if not doc:
        return ConnectionsModel()
    connections = []
    for c in doc.get("connections", []):
        local, partner = c.get("local") or {}, c.get("partner") or {}
        connections.append(
            Connection(
                ref=c["ref"],
                name=c.get("name", ""),
                kind=c["kind"],
                local=ConnectionEnd(
                    id=local.get("id", ""),
                    module=local.get("module"),
                    interface=local.get("interface"),
                    address=local.get("address"),
                    tsap=local.get("tsap"),
                ),
                partner=ConnectionPartner(
                    specified=bool(partner.get("specified")),
                    name=partner.get("name"),
                    module=partner.get("module"),
                    address=partner.get("address"),
                    rack=partner.get("rack"),
                    slot=partner.get("slot"),
                    tsap=partner.get("tsap"),
                ),
                details=c.get("details", "read"),
                type_id=c.get("type_id"),
                active=c.get("active"),
                one_way=c.get("one_way"),
                sources=dict(c.get("sources") or {}),
                differences=tuple(
                    ValueDifference(d["field"], d["tables"], d["compiled"])
                    for d in c.get("differences", [])
                ),
                safety=bool(c.get("safety")),
            )
        )
    uses = []
    for u in doc.get("uses", []):
        uses.append(
            ConnectionUse(
                unit=u["unit"],
                block=u["block"],
                called=u.get("called", ""),
                network_no=u.get("network_no"),
                line=u.get("line"),
                id=_read_value(u.get("id")) or CallValue(unassigned=True),
                r_id=_read_value(u.get("r_id")),
                areas=tuple(
                    DataArea(
                        param=a["param"],
                        role=a["role"],
                        pointer=a.get("pointer"),
                        db=a.get("db"),
                        start=a.get("start"),
                        length_bytes=a.get("length_bytes"),
                        members=tuple(a.get("members", [])),
                        unresolved=a.get("unresolved"),
                        unassigned=bool(a.get("unassigned")),
                    )
                    for a in u.get("areas", [])
                ),
                len=_read_value(u.get("len")),
                connection=u.get("connection"),
                findings=tuple(_read_finding(f) for f in u.get("findings", [])),
                safety=bool(u.get("safety")),
            )
        )
    couplers = [
        Coupler(
            ref=c["ref"],
            kind=c["kind"],
            order_no=c.get("order_no"),
            address=c.get("address"),
            transfer_areas=tuple(
                TransferArea(
                    t["module"], t["direction"], t["range"], t["length_bytes"],
                    tuple(t.get("symbols", [])),
                )
                for t in c.get("transfer_areas", [])
            ),
            safety=bool(c.get("safety")),
        )
        for c in doc.get("couplers", [])
    ]  # fmt: skip
    return ConnectionsModel(
        tuple(connections),
        tuple(uses),
        tuple(couplers),
        tuple(_read_finding(f) for f in doc.get("findings", [])),
    )


# ------------------------------------------------------------------ rules
def check_doc(
    doc: Mapping[str, Any],
    modules: Collection[str],
    networks: Collection[str],
    racks: Collection[str],
    units: Collection[str],
) -> list[str]:
    """Violations of contracts/connections-json.md; refs are checked against the export."""
    v: list[str] = []
    refs: set[str] = set()
    for c in doc.get("connections", []):
        ref = str(c.get("ref"))
        where = f"{FILE}: connection {ref!r}"
        if ref in refs:
            v.append(f"{where}: ref is not unique")
        refs.add(ref)
        kind, local, partner = c.get("kind"), c.get("local") or {}, c.get("partner") or {}
        if kind not in CONNECTION_KINDS:
            v.append(f"{where}: unknown kind {kind!r}")
        if (kind == "other") != ("type_id" in c):
            v.append(f"{where}: type_id belongs to kind 'other' exactly")
        if not _ID.match(str(local.get("id"))):
            v.append(f"{where}: local.id {local.get('id')!r} is not 0x + 4 hex digits")
        for side, tsap in (("local", local.get("tsap")), ("partner", partner.get("tsap"))):
            if tsap is not None and not _TSAP.match(str(tsap)):
                v.append(f"{where}: {side} TSAP {tsap!r} is neither two hex bytes nor SIMATIC-ACC")
        if "module" in local and local["module"] not in modules:
            v.append(f"{where}: local.module {local['module']!r} not in hardware.json")
        if "interface" in local and local["interface"] not in networks:
            v.append(f"{where}: local.interface {local['interface']!r} not in hardware.json")
        if "module" in partner and partner["module"] not in modules:
            v.append(f"{where}: partner.module {partner['module']!r} not in hardware.json")
        if c.get("details") == "not_read" and ("tsap" in local or partner):
            v.append(f"{where}: details not read, but TSAP or partner fields present")
    for u in doc.get("uses", []):
        where = f"{FILE}: {u.get('block')} in {u.get('unit')!r} NW{u.get('network_no')}"
        if u.get("unit") not in units:
            v.append(f"{where}: unit has no unit file")
        if u.get("block") not in COMM_BLOCKS:
            v.append(f"{where}: unknown block")
        for key, pattern in (("id", _ID), ("r_id", _R_ID), ("len", None)):
            val = u.get(key)
            if val is None:
                if key == "id":
                    v.append(f"{where}: id is missing")
                continue
            if sum(k in val for k in _VALUE_KEYS) != 1:
                v.append(f"{where}: {key} must be exactly one of {', '.join(_VALUE_KEYS)}")
            elif pattern and "value" in val and not pattern.match(str(val["value"])):
                v.append(f"{where}: {key} value {val['value']!r} has the wrong form")
        for a in u.get("areas", []):
            if a.get("role") not in _ROLES:
                v.append(f"{where}: area {a.get('param')!r} has unknown role {a.get('role')!r}")
        if "connection" in u and u["connection"] not in refs:
            v.append(f"{where}: connection {u['connection']!r} is not in the file")
        v += _finding_refs(u.get("findings", []), refs, where)
    for c in doc.get("couplers", []):
        where = f"{FILE}: coupler {c.get('ref')!r}"
        if c.get("ref") not in racks:
            v.append(f"{where}: ref is not a rack of hardware.json")
        if c.get("kind") not in COUPLER_KINDS:
            v.append(f"{where}: unknown kind {c.get('kind')!r}")
        for t in c.get("transfer_areas", []):
            if t.get("module") not in modules:
                v.append(f"{where}: transfer module {t.get('module')!r} not in hardware.json")
    v += _finding_refs(doc.get("findings", []), refs, FILE)
    v += [
        f"{FILE}: finding {f.get('code')!r} names coupler {f['coupler']!r}, not a rack of "
        "hardware.json"
        for f in doc.get("findings", [])
        if "coupler" in f and f["coupler"] not in racks
    ]
    return v


def _finding_refs(findings: Any, refs: set[str], where: str) -> list[str]:
    return [
        f"{where}: finding {f.get('code')!r} names unknown connection {f['connection']!r}"
        for f in findings
        if "connection" in f and f["connection"] not in refs
    ]


# ------------------------------------------------------------------ index.md section
HEADING = "## Connections"
_TABLE = (
    "| ID | Name | Local | Partner | Partner address | TSAP local / partner | Sets up "
    "| One-way | Used by |",
    "|---|---|---|---|---|---|---|---|---|",
)


def _cell(text: object) -> str:
    return " ".join(str(text if text is not None else "–").split()).replace("|", "\\|") or "–"


def _yes_no(flag: bool | None, yes: str = "yes", no: str = "no") -> str:
    return "–" if flag is None else (yes if flag else no)


def index_section(cm: ConnectionsModel) -> list[str]:
    """The readable part of ``index.md``; IDs as the engineering tool shows them."""
    cm = cm.sorted()
    lines = ["", HEADING, ""]
    if not cm.connections:
        lines.append("No connections configured.")
    else:
        lines += _TABLE
        for c in cm.connections:
            used = [
                f"{u.unit} NW {u.network_no} ({u.block})" for u in cm.uses if u.connection == c.ref
            ]
            partner: str | None
            address: str | None
            if c.details == "not_read":
                partner, address, tsaps = "details not read", "–", "–"
            else:
                partner = c.partner.name or c.partner.module
                address = c.partner.address
                tsaps = f"{c.local.tsap or '–'} / {c.partner.tsap or '–'}"
            lines.append(
                "| "
                + " | ".join(
                    _cell(x)
                    for x in (
                        shown_id(c.local.id),
                        c.name,
                        c.ref.rsplit("/", 1)[0],
                        partner,
                        address,
                        tsaps,
                        _yes_no(c.active, "local", "partner"),
                        _yes_no(c.one_way),
                        ", ".join(used) or "–",
                    )
                )
                + " |"
            )
    unlinked = [u for u in cm.uses if u.connection is None]
    if unlinked:
        lines += ["", "Calls without a configured connection:", ""]
        for u in unlinked:
            values = [f"ID {_shown(u.id)}"] + ([f"R_ID {_shown(u.r_id)}"] if u.r_id else [])
            shown = {c.ref: shown_id(c.local.id) for c in cm.connections}
            codes = "; ".join(
                # a hint, worded as a possibility; the values stay as written
                f"R_ID equals configured connection ID {shown.get(f.connection or '', '?')}: "
                "ID and R_ID may be swapped"
                if f.code == "id_r_id_maybe_swapped"
                else "ID is not a configured connection"
                if f.code == "id_not_configured"
                else f.code
                for f in u.findings
            )
            lines.append(
                f"- {u.unit} NW {u.network_no} ({u.block}): {', '.join(values)}"
                + (f" ({codes})" if codes else "")
            )
    if cm.findings:
        lines += ["", "Findings:", ""]
        differences = {c.ref: c.differences for c in cm.connections}
        for f in cm.findings:
            detail = "; ".join(
                f"{d.field}: tables {d.tables}, compiled {d.compiled}"
                for d in differences.get(f.connection or "", ())
                if f.code == "tables_compiled_differ"
            )
            where = f.connection or f.coupler or f.unit or ""
            lines.append(f"- {f.code}: {where}" + (f" ({detail})" if detail else ""))
    if cm.couplers:
        lines += ["", "Couplers:", ""]
        for k in cm.couplers:
            areas = ", ".join(t.range for t in k.transfer_areas) or "no transfer areas"
            lines.append(f"- {k.ref} ({k.kind}, {k.order_no or 'no order number'}): {areas}")
    return lines


def _shown(v: CallValue) -> str:
    if v.value is not None:
        return shown_id(v.value)
    return f"unresolved ({v.unresolved})" if v.unresolved is not None else "unassigned"
