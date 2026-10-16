"""the platform-independent rules that link communication calls to configured
connections and report findings, shared by the STEP 7 and TIA extractors."""

from __future__ import annotations

from plcexport.connections_link import (
    DUPLICATE_R_ID,
    ID_NOT_CONFIGURED,
    MAYBE_SWAPPED,
    UNUSED,
    link,
    owner_of,
)
from plcexport.model import (
    CallValue,
    CommBlock,
    Connection,
    ConnectionEnd,
    ConnectionUse,
    InterfaceFinding,
)

PLC = "Station_1/PLC_1"
OTHER = "Station_2/PLC_2"


def conn(owner: str, ident: str, kind: str = "s7") -> Connection:
    return Connection(f"{owner}/{ident}", f"conn {ident}", kind, ConnectionEnd(ident))  # type: ignore[arg-type]


def call(
    block: CommBlock,
    ident: str | None,
    r_id: str | None = None,
    *,
    unit: str = "Main",
    nw: int = 1,
    safety: bool = False,
) -> ConnectionUse:
    no_r_id = block in ("GET", "PUT")
    rid = None if no_r_id else CallValue(r_id) if r_id else CallValue(unassigned=True)
    return ConnectionUse(
        unit=unit,
        block=block,
        called=f'"{block}_DB".{block}',
        network_no=nw,
        id=CallValue(ident) if ident else CallValue(unresolved="#id"),
        r_id=rid,
        safety=safety,
    )


def codes(u: ConnectionUse) -> list[str]:
    return [f.code for f in u.findings]


def test_owner_is_the_ref_without_the_id() -> None:
    assert owner_of(conn(PLC, "0x0100")) == PLC


def test_a_call_is_linked_to_its_own_connection_only() -> None:
    cs = [conn(PLC, "0x0100"), conn(OTHER, "0x0100")]
    r = link(cs, [(PLC, call("BSEND", "0x0100", "0x0000000B"))], {PLC, OTHER})
    (u,) = r.uses
    assert u.connection == f"{PLC}/0x0100" and codes(u) == []


def test_id_not_configured_and_maybe_swapped() -> None:
    cs = [conn(PLC, "0x0010")]
    r = link(cs, [(PLC, call("BSEND", "0xAAAA", "0x00000010"))], {PLC})
    (u,) = r.uses
    assert u.connection is None
    assert u.findings == (
        InterfaceFinding(ID_NOT_CONFIGURED),
        InterfaceFinding(MAYBE_SWAPPED, connection=f"{PLC}/0x0010"),
    )


def test_an_unresolved_id_is_neither_linked_nor_a_finding() -> None:
    r = link([conn(PLC, "0x0100")], [(PLC, call("GET", None))], {PLC})
    assert r.uses[0].connection is None and codes(r.uses[0]) == []


def test_unused_only_where_the_program_was_read() -> None:
    cs = [conn(PLC, "0x0100"), conn(PLC, "0x0101"), conn(OTHER, "0x0200")]
    r = link(cs, [(PLC, call("BSEND", "0x0100", "0x00000001"))], {PLC})
    assert r.findings == (InterfaceFinding(UNUSED, connection=f"{PLC}/0x0101"),)


def test_other_connection_kinds_are_never_linked() -> None:
    r = link([conn(PLC, "0x0100", kind="other")], [(PLC, call("GET", "0x0100"))], {PLC})
    assert r.uses[0].connection is None and codes(r.uses[0]) == [ID_NOT_CONFIGURED]
    assert r.findings == ()  # an "other" connection is not reported as unused


def test_a_connection_used_only_by_safety_calls_is_safety() -> None:
    cs = [conn(PLC, "0x0100"), conn(PLC, "0x0101")]
    calls = [
        (PLC, call("BSEND", "0x0100", "0x00000001", safety=True)),
        (PLC, call("BSEND", "0x0101", "0x00000001", safety=True)),
        (PLC, call("BRCV", "0x0101", "0x00000002")),
    ]
    by_ref = {c.ref: c for c in link(cs, calls, {PLC}).connections}
    assert by_ref[f"{PLC}/0x0100"].safety and not by_ref[f"{PLC}/0x0101"].safety


def test_several_calls_with_one_id_are_separate_uses() -> None:
    calls = [
        (PLC, call("BSEND", "0x0100", "0x00000001", nw=1)),
        (PLC, call("BSEND", "0x0100", "0x00000002", nw=2)),
        (PLC, call("BRCV", "0x0100", "0x00000003", nw=3)),
    ]
    r = link([conn(PLC, "0x0100")], calls, {PLC})
    assert [u.network_no for u in r.uses] == [1, 2, 3]
    assert {u.connection for u in r.uses} == {f"{PLC}/0x0100"}
    assert all(codes(u) == [] for u in r.uses)


def test_duplicate_r_id_on_one_connection() -> None:
    """two sends (or two receives) of one PLC on one connection with one R_ID."""
    ref = f"{PLC}/0x0100"
    calls = [
        (PLC, call("BSEND", "0x0100", "0x0000000B", nw=1)),
        (PLC, call("USEND", "0x0100", "0x0000000B", nw=2)),  # USEND also sends
        (PLC, call("BRCV", "0x0100", "0x0000000B", nw=3)),  # a receive: other direction
        (PLC, call("BRCV", "0x0100", "0x0000000C", nw=4)),
        (PLC, call("URCV", "0x0100", "0x0000000C", nw=5)),
        (PLC, call("BSEND", "0x0100", None, nw=6)),  # unassigned R_ID: never grouped
        (PLC, call("BSEND", "0x0100", None, nw=7)),
    ]
    r = link([conn(PLC, "0x0100")], calls, {PLC})
    dup = InterfaceFinding(DUPLICATE_R_ID, connection=ref)
    assert [dup in u.findings for u in r.uses] == [True, True, False, True, True, False, False]


def test_duplicate_r_id_needs_the_same_connection() -> None:
    cs = [conn(PLC, "0x0100"), conn(PLC, "0x0101")]
    calls = [
        (PLC, call("BSEND", "0x0100", "0x0000000B")),
        (PLC, call("BSEND", "0x0101", "0x0000000B")),
    ]
    assert all(codes(u) == [] for u in link(cs, calls, {PLC}).uses)
