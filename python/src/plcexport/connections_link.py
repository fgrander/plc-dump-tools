"""Link communication calls to configured connections and report the findings.

Platform-independent: the STEP 7 and the TIA extractor build the connections and the unlinked
calls, and both get the same rules here.

An *owner* is the PLC a connection or a program belongs to, named like the connection ref
without its ID (``<station>/<module>``). Only S7 connections are linked.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Collection, Iterable, Sequence
from dataclasses import dataclass, replace

from plcexport.model import (
    Connection,
    ConnectionUse,
    ExportVariable,
    InterfaceFinding,
)

ID_NOT_CONFIGURED = "id_not_configured"
MAYBE_SWAPPED = "id_r_id_maybe_swapped"
UNUSED = "connection_unused"
DUPLICATE_R_ID = "duplicate_r_id"

SENDERS = frozenset({"BSEND", "USEND"})
RECEIVERS = frozenset({"BRCV", "URCV"})


@dataclass(frozen=True)
class Linked:
    connections: tuple[Connection, ...]
    uses: tuple[ConnectionUse, ...]
    findings: tuple[InterfaceFinding, ...]  # project level: connection_unused


def owner_of(c: Connection) -> str:
    return c.ref.rsplit("/", 1)[0]


def link(
    connections: Sequence[Connection],
    calls: Iterable[tuple[str | None, ConnectionUse]],
    read_owners: Collection[str],
) -> Linked:
    """``calls`` are (owner, call) pairs with ``connection`` and ``findings`` not yet set.
    ``read_owners`` are the owners whose program was read: only there is a connection without
    a call reported as unused."""
    by_owner: dict[str, list[Connection]] = {}
    for c in connections:
        if c.kind == "s7":
            by_owner.setdefault(owner_of(c), []).append(c)

    uses: list[ConnectionUse] = []
    for owner, u in calls:
        own = by_owner.get(owner or "", [])
        ident = u.id.value
        found = next((c for c in own if c.local.id == ident), None) if ident else None
        findings: list[InterfaceFinding] = []
        if ident and found is None:
            findings.append(InterfaceFinding(ID_NOT_CONFIGURED))
            r_id = u.r_id.value if u.r_id else None
            # a rule, not a guess: the R_ID is the local ID of a connection of this PLC
            swapped = next((c for c in own if r_id and int(r_id, 16) == int(c.local.id, 16)), None)
            if swapped is not None:
                findings.append(InterfaceFinding(MAYBE_SWAPPED, connection=swapped.ref))
        uses.append(replace(u, connection=found.ref if found else None, findings=tuple(findings)))
    uses = _duplicate_r_ids(uses)

    used = {u.connection for u in uses if u.connection}
    only_safety = {u.connection for u in uses if u.connection and u.safety} - {
        u.connection for u in uses if u.connection and not u.safety
    }
    marked = tuple(replace(c, safety=True) if c.ref in only_safety else c for c in connections)
    unused = tuple(
        InterfaceFinding(UNUSED, connection=c.ref)
        for owner, own in by_owner.items()
        if owner in read_owners  # only where the PLC's program was read
        for c in own
        if c.ref not in used
    )
    return Linked(marked, tuple(uses), unused)


def _duplicate_r_ids(uses: list[ConnectionUse]) -> list[ConnectionUse]:
    """two or more send (or receive) calls on one connection with one constant R_ID.
    Each of them gets the finding; the values stay as written."""

    def key(u: ConnectionUse) -> tuple[str, str, str] | None:
        direction = "send" if u.block in SENDERS else "receive" if u.block in RECEIVERS else None
        r_id = u.r_id.value if u.r_id else None
        return (u.connection, direction, r_id) if u.connection and direction and r_id else None

    counts = Counter(k for k in map(key, uses) if k is not None)
    out = []
    for u in uses:
        k = key(u)
        if k is not None and counts[k] > 1:
            dup = InterfaceFinding(DUPLICATE_R_ID, connection=u.connection)
            u = replace(u, findings=(*u.findings, dup))
        out.append(u)
    return out


def db_members(variables: Iterable[ExportVariable]) -> dict[str, list[tuple[int, str]]]:
    """Per data block unit: (byte offset, symbolic path) of its members with an offset."""
    out: dict[str, list[tuple[int, str]]] = {}
    for v in variables:
        if v.offset:
            out.setdefault(v.declared_in, []).append((int(v.offset.split(".")[0]), v.symbolic_path))
    return out


def members_in(
    members: dict[str, list[tuple[int, str]]], db: str, start_byte: int, length_bytes: int | None
) -> tuple[str, ...]:
    """The members of ``db`` whose offset lies in the area (a length of None counts as 1)."""
    hi = start_byte + (length_bytes or 1)
    return tuple(sorted(path for at, path in members.get(db, []) if start_byte <= at < hi))
