"""s7dump ``connections`` → export connections.

Every value keeps its source: the project's connection tables, the compiled connection record,
or both. Where both exist and differ, the entry carries the compiled value (what the PLC runs
with) and lists the difference; nothing is silently preferred.

Addresses are data here. Nothing in this module contacts a device.
"""

from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import dataclass, field
from typing import Any

from plcexport.common import ExtractWarning
from plcexport.format.connections import hex_id
from plcexport.model import (
    Connection,
    ConnectionEnd,
    ConnectionPartner,
    InterfaceFinding,
    ValueDifference,
    ValueSource,
)

S7_CONNECTION_TYPE = 1332225  # TYPE of an S7 connection in HOMOVERB.DBF
DIFFER = "tables_compiled_differ"
NO_OWNER = "connection_without_owner"
REASON_NO_COMPILED = "compiled connection data missing; TSAPs from the tables"


@dataclass
class MappedConnections:
    connections: list[Connection] = field(default_factory=list)
    findings: list[InterfaceFinding] = field(default_factory=list)
    warnings: list[ExtractWarning] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)  # why the category is only partly delivered


def tsap(resource: int | None, rack: int | None, slot: int | None) -> str | None:
    """TSAP of an S7 connection end: connection resource, then rack and slot in one byte."""
    if resource is None or slot is None:
        return None
    return f"{resource & 0xFF:02X}.{((rack or 0) * 32 + slot) & 0xFF:02X}"


def _source(tables: bool, compiled: bool) -> ValueSource | None:
    if tables and compiled:
        return "both"
    return "compiled" if compiled else "tables" if tables else None


def _module_ref(station: str | None, rack: int | None, slot: int | None) -> str:
    return f"{station or '-'}/{rack or 0}.{slot}"


def map_connections(
    dump: Mapping[str, Any], modules: Collection[str], networks: Collection[str]
) -> MappedConnections:
    """``modules`` and ``networks`` are the refs of the mapped hardware; a ref that is not among
    them is left out rather than written as a dangling reference."""
    out = MappedConnections()
    nodes = {e["node"]: e for e in dump.get("ethernet") or []}
    listed_only = without_compiled = 0
    for c in dump.get("connections") or []:
        owner = c.get("owner")
        ident = hex_id(c["local_id"])
        if owner:
            ref = f"{owner.get('station') or '-'}/{owner['module']}/{ident}"
            module = _module_ref(owner.get("station"), owner.get("rack"), owner.get("slot"))
        else:
            ref, module = f"list {c['list']}/{ident}", None
            out.warnings.append(
                ExtractWarning(NO_OWNER, f"connection {c['name']!r} (ID {ident}): owner not found")
            )
        local_module = module if module in modules else None
        if c["type_id"] != S7_CONNECTION_TYPE:
            listed_only += 1
            out.connections.append(
                Connection(ref, c["name"], "other", ConnectionEnd(ident, local_module),
                           details="not_read", type_id=c["type_id"])
            )  # fmt: skip
            continue

        tables, compiled = c.get("tables") or {}, c.get("compiled")
        node = nodes.get(c.get("local_node"))
        interface = f"{node.get('station')}/{node.get('module')}/ethernet" if node else None
        differences: list[ValueDifference] = []

        local_tables = tsap(tables.get("local_resource"), (owner or {}).get("rack"),
                            (owner or {}).get("slot"))  # fmt: skip
        partner_tables = tsap(tables.get("partner_resource"), tables.get("partner_rack"),
                              tables.get("partner_slot"))  # fmt: skip
        cp = compiled or {}
        local_tsap = _pick("local_tsap", local_tables, cp.get("local_tsap"), differences)
        partner_tsap = _pick("partner_tsap", partner_tables, cp.get("partner_tsap"), differences)
        address = _pick(
            "partner_address", tables.get("partner_ip"), cp.get("partner_ip"), differences
        )
        active = _pick("active", c.get("active"), cp.get("active"), differences)
        sources = {
            # "both" only when the tables give both TSAPs; one table value without a compiled
            # record is still a value from the tables
            "tsaps": _source(
                None not in (local_tables, partner_tables)
                or (not compiled and (local_tables or partner_tables) is not None),
                bool(compiled),
            ),
            "partner_address": _source(tables.get("partner_ip") is not None, bool(compiled)),
            "active": _source(c.get("active") is not None, bool(compiled)),
        }
        if not compiled:
            without_compiled += 1

        if c.get("unspecified"):
            partner = ConnectionPartner(
                False, tables.get("partner_name"), None, address,
                tables.get("partner_rack"), tables.get("partner_slot"), partner_tsap,
            )  # fmt: skip
        else:  # a station of the same project
            far = nodes.get(c.get("partner_node")) or {}
            far_ref = _module_ref(far.get("station"), far.get("rack"), far.get("slot"))
            partner = ConnectionPartner(
                True, far.get("module"), far_ref if far_ref in modules else None,
                address or far.get("ip"), far.get("rack"), far.get("slot"), partner_tsap,
            )  # fmt: skip
        out.connections.append(
            Connection(
                ref=ref,
                name=c["name"],
                kind="s7",
                local=ConnectionEnd(
                    ident, local_module, interface if interface in networks else None,
                    node.get("ip") if node else None, local_tsap,
                ),
                partner=partner,
                active=active,
                one_way=c.get("one_way"),
                sources={k: v for k, v in sources.items() if v},
                differences=tuple(differences),
            )
        )  # fmt: skip
        if differences:
            out.findings.append(InterfaceFinding(DIFFER, connection=ref))

    if listed_only:
        out.reasons.append(f"{listed_only} connection(s) listed only (type not read)")
    if without_compiled:
        out.reasons.append(REASON_NO_COMPILED)
    if any(w.code == NO_OWNER for w in out.warnings):
        out.reasons.append("owner module of a connection list not found")
    return out


def _pick(name: str, tables: Any, compiled: Any, differences: list[ValueDifference]) -> Any:
    """The compiled value when there is one, else the tables'; a disagreement is recorded."""
    if tables is not None and compiled is not None and tables != compiled:
        differences.append(ValueDifference(name, _text(tables), _text(compiled)))
    return compiled if compiled is not None else tables


def _text(value: Any) -> str:
    return str(value).lower() if isinstance(value, bool) else str(value)
