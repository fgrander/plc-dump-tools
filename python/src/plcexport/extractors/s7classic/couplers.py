"""Couplers in the exported hardware.

A PN/PN coupler or a DP/DP coupler links two controllers: each side is a device in its own
project, and the data crosses through the I/O ranges of the coupler's modules (its transfer
areas). The coupler is recognized by its order number; I-Devices and intelligent DP slaves are
not detected (analysis 2026-10-10).

Works on the mapped hardware only: nothing here reads a project or contacts a device.
"""

from __future__ import annotations

import re

from plcexport.model import Coupler, CouplerKind, HardwareModel, HwModule, TransferArea

# order number without blanks -> kind
KINDS: dict[str, CouplerKind] = {"6ES7158-3AD": "pn_pn", "6ES7158-0AD": "dp_dp"}
_RANGE = re.compile(r"^%([IQ])(\d+)\.0-%[IQ](\d+)\.7$")
_DEVICE = re.compile(r"^(?P<station>.+)/(?P<system>[^/]+) #(?P<device>\d+)$")


def kind_of(order_no: str | None) -> CouplerKind | None:
    compact = (order_no or "").replace(" ", "").upper()
    return next((kind for prefix, kind in KINDS.items() if compact.startswith(prefix)), None)


def _is_safety(module: HwModule) -> bool:
    name = module.type.upper()
    return "PROFISAFE" in name or name.startswith("F-")


def _direction(address: str) -> str | None:
    letter = address.lstrip("%").lstrip("Pp")[:1].upper()
    return {"I": "in", "E": "in", "Q": "out", "A": "out"}.get(letter)


def _address(hw: HardwareModel, rack: str) -> str | None:
    """The coupler's own network address: the Ethernet entry of this device in its station."""
    m = _DEVICE.match(rack)
    if not m:
        return None
    found = [
        n.address
        for n in hw.networks
        if n.interface == "ethernet"
        and n.address
        and n.ref.startswith(f"{m['station']}/")
        and n.ref.endswith(f" #{m['device']}/ethernet")
    ]
    return found[0].split("/")[0] if len(found) == 1 and found[0] else None


def find_couplers(hw: HardwareModel) -> list[Coupler]:
    by_rack: dict[str, list[HwModule]] = {}
    for module in hw.modules:
        if module.rack:
            by_rack.setdefault(module.rack, []).append(module)
    symbols: dict[tuple[str, str], list[str]] = {}
    for ch in hw.channels:
        direction = _direction(ch.address)
        if ch.symbol and direction:
            symbols.setdefault((ch.module_ref, direction), []).append(ch.symbol)

    couplers: list[Coupler] = []
    for rack, modules in sorted(by_rack.items()):
        head = next((m for m in modules if kind_of(m.order_no)), None)
        if head is None:
            continue
        areas: list[TransferArea] = []
        for module in sorted(modules, key=lambda x: (x.slot or 0, x.ref)):
            for text in module.address_ranges:
                r = _RANGE.match(text)
                if not r:
                    continue
                direction = "in" if r.group(1) == "I" else "out"
                areas.append(
                    TransferArea(
                        module=module.ref,
                        direction=direction,  # type: ignore[arg-type]
                        range=text,
                        length_bytes=int(r.group(3)) - int(r.group(2)) + 1,
                        symbols=tuple(sorted(symbols.get((module.ref, direction), []))),
                    )
                )
        kind = kind_of(head.order_no)
        assert kind is not None
        couplers.append(
            Coupler(
                ref=rack,
                kind=kind,
                order_no=head.order_no,
                address=_address(hw, rack),
                transfer_areas=tuple(areas),
                safety=any(_is_safety(m) for m in modules),
            )
        )
    return couplers
