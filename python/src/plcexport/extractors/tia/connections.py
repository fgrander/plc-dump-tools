"""TIA Portal connections -> the connection model.

The input is a PLC's ``configured_connections`` list of ``dump.json``; values are copied as
found, only the local ID is read as the hex value TIA Portal shows."""

from __future__ import annotations

import re
from collections.abc import Collection, Mapping, Sequence
from typing import Any

from plcexport.common import ExtractWarning
from plcexport.format.connections import hex_id
from plcexport.model import (
    Connection,
    ConnectionEnd,
    ConnectionPartner,
    Coupler,
    InterfaceFinding,
    TransferArea,
)

S7_CLASS = "S7Connection"
VALUE_NOT_AVAILABLE = "value_not_available"
# the two forms the format accepts (the second one for SIMATIC ACC)
_TSAP = re.compile(r"^(?:[0-9A-F]{2}\.[0-9A-F]{2}|SIMATIC-ACC[0-9A-F]+)$")


def _text(value: Any) -> str | None:
    return None if value is None or str(value) == "" else str(value)


def _int(value: Any) -> int | None:
    return None if value is None or str(value) == "" else int(value)


def map_connections(
    entries: Sequence[Mapping[str, Any]],
    *,
    station: str,
    plc: str,
    module: str | None,
    networks: Collection[str],
) -> tuple[list[Connection], list[InterfaceFinding], list[ExtractWarning]]:
    """The connections of one PLC, sorted by ref; ``module`` and ``networks`` are refs of the
    PLC's export (``hardware.json``)."""
    out: list[Connection] = []
    findings: list[InterfaceFinding] = []
    warnings: list[ExtractWarning] = []
    for e in entries:
        ident = hex_id(int(str(e["local_id"]), 16))
        ref = f"{station}/{plc}/{ident}"
        s7 = e.get("class") == S7_CLASS
        node, node_type = _text(e.get("local_interface")), _text(e.get("local_node_type"))
        interface = f"{station}/{node}/{node_type}" if node and node_type else None
        tsaps: dict[str, str | None] = {}
        missing: list[str] = []
        for key in ("local_tsap", "partner_tsap"):
            value = _text(e.get(key)) if s7 else None
            if value is not None and not _TSAP.match(value):
                missing.append(key)
                value = None
            tsaps[key] = value
        if missing:  # never changed to fit, never guessed
            findings.append(InterfaceFinding(VALUE_NOT_AVAILABLE, connection=ref))
            warnings.append(
                ExtractWarning(
                    "connection_value_not_available",
                    f"{ref}: {', '.join(missing)} not in a form the format knows: "
                    + ", ".join(repr(e.get(k)) for k in missing),
                )
            )
        out.append(
            Connection(
                ref=ref,
                name=_text(e.get("local_name")) or ident,
                kind="s7" if s7 else "other",
                local=ConnectionEnd(
                    ident,
                    module,
                    interface if interface in networks else None,
                    _text(e.get("local_address")),
                    tsaps["local_tsap"],
                ),
                partner=ConnectionPartner(
                    False,
                    _text(e.get("partner_name")),
                    None,
                    _text(e.get("partner_address")),
                    _int(e.get("partner_rack")),
                    _int(e.get("partner_slot")),
                    tsaps["partner_tsap"],
                )
                if s7
                else ConnectionPartner(),
                details="read" if s7 else "not_read",
                type_id=None if s7 else _int(e.get("type_value")),
                active=e.get("local_active") if s7 else None,
            )
        )
    out.sort(key=lambda c: c.ref)
    return out, findings, warnings


# ------------------------------------------------------------------ couplers
SIDE_WITHOUT_CONTROLLER = "coupler_side_without_controller"
LENGTH_MISMATCH = "transfer_area_length_mismatch"
_KINDS = {"6ES71583AD": "pn_pn", "6ES71580AD": "dp_dp"}  # order number prefixes
_IO_TAG = re.compile(r"^%([IQ])([BWD]?)(\d+)(?:\.\d)?$")
_TAG_BYTES = {"": 1, "B": 1, "W": 2, "D": 4}


def _kind(order_no: Any) -> str | None:
    key = re.sub(r"[\s-]", "", str(order_no or "")).upper()
    return next((k for prefix, k in _KINDS.items() if key.startswith(prefix)), None)


def _range(io: str, start: int, length_bytes: int) -> str:
    area = "I" if io == "input" else "Q"
    return f"%{area}{start}.0-%{area}{start + max(1, length_bytes) - 1}.7"


def _symbols(variables: Sequence[Any], io: str, start: int, length_bytes: int) -> tuple[str, ...]:
    """Global I/O tags of the PLC that lie in the area."""
    area = "I" if io == "input" else "Q"
    out = []
    for v in variables:
        m = _IO_TAG.match(str(v.address or ""))
        if m and m.group(1) == area:
            first = int(m.group(3))
            last = first + _TAG_BYTES[m.group(2)] - 1
            if start <= first and last < start + max(1, length_bytes):
                out.append(v.symbolic_path)
    return tuple(sorted(out))


def _owner(item: Mapping[str, Any]) -> str | None:
    """The PLC (device item name) that controls the IO system the item is connected to."""
    controller = (item.get("io_system") or {}).get("controller")
    return str(controller).rsplit("/", 1)[-1] if controller else None


def _bare(address: Any) -> str | None:
    return str(address).split("/", 1)[0] if address else None


def map_couplers(
    devices: Sequence[Mapping[str, Any]], *, plc: str, variables: Sequence[Any]
) -> tuple[list[Coupler], list[InterfaceFinding], list[ExtractWarning]]:
    """The coupler sides of ``devices`` (hardware entries of ``dump.json``) that ``plc``
    controls, and the findings: a side connected to no IO system, an area whose own length
    differs from its address length."""
    couplers: list[Coupler] = []
    findings: list[InterfaceFinding] = []
    warnings: list[ExtractWarning] = []
    for dev in devices:
        dname = str(dev["name"])
        items = list(dev.get("items") or [])
        heads = {str(it["path"]): it for it in items}
        # PN/PN: each side's interface carries its transfer areas
        for it in items:
            if not it.get("transfer_areas"):
                continue
            head = heads.get(str(it.get("rack"))) or {}
            kind = _kind(head.get("order_no"))
            if kind is None:
                continue
            side = f"{dname}/{it.get('rack')}"
            owner = _owner(it)
            if owner is None:
                findings.append(InterfaceFinding(SIDE_WITHOUT_CONTROLLER, coupler=side))
                warnings.append(ExtractWarning(
                    SIDE_WITHOUT_CONTROLLER,
                    f"{side}: connected to no IO system; its transfer areas have no addresses",
                ))  # fmt: skip
                continue
            if owner != plc:
                continue
            areas: list[TransferArea] = []
            for a in it["transfer_areas"]:
                for addr in a.get("controller_addresses") or []:
                    io, start, bits = str(addr["io"]), int(addr["start"]), int(addr["bits"])
                    length = (bits + 7) // 8
                    own = a.get(
                        "partner_to_local_bytes" if io == "input" else "local_to_partner_bytes"
                    )
                    if own is not None and int(own) != length:
                        findings.append(InterfaceFinding(LENGTH_MISMATCH, coupler=side))
                        warnings.append(ExtractWarning(
                            LENGTH_MISMATCH,
                            f"{side} {a['name']}: the area has {own} byte(s), its {io} address "
                            f"{start} has {bits} bits; the address is exported",
                        ))  # fmt: skip
                    areas.append(TransferArea(
                        f"{dname}/{head['path']}", "in" if io == "input" else "out",
                        _range(io, start, length), length, _symbols(variables, io, start, length),
                    ))  # fmt: skip
            address = next((_bare(i.get("address")) for i in it.get("interfaces") or []), None)
            couplers.append(
                Coupler(side, kind, head.get("order_no"), address, tuple(areas))  # type: ignore[arg-type]
            )
        # DP/DP: the head module carries the order number, its submodules the addresses
        for head in items:
            if _kind(head.get("order_no")) != "dp_dp" or head.get("transfer_areas"):
                continue
            if _owner(head) != plc:
                continue
            areas = []
            for it in items:
                for addr in it.get("addresses") or []:
                    io, start = str(addr["io"]), int(addr["start"])
                    length = (int(addr["length"]) + 7) // 8
                    if length <= 0:
                        continue
                    areas.append(TransferArea(
                        f"{dname}/{it['path']}", "in" if io == "input" else "out",
                        _range(io, start, length), length, _symbols(variables, io, start, length),
                    ))  # fmt: skip
            couplers.append(Coupler(f"{dname}/{head['rack']}", "dp_dp", head.get("order_no"), None,
                                    tuple(areas)))  # fmt: skip
    couplers.sort(key=lambda k: k.ref)
    return couplers, findings, warnings
