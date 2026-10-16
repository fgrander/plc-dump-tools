"""real STEP 7 V5.x sample projects for the ``s7reference`` tests.

Projects live in ``samples/s7classic/`` (git-ignored; ``S7DUMP_SAMPLES_DIR`` overrides it).
Only real STEP 7 V5.x projects count: zips are inspected for a ``.s7p``/``.s7l`` entry, so TIA
Portal archives in the folder do not make the tests run.
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path
from typing import Any

import pytest

from tests.conftest import S7_SAMPLES

S7_SUFFIXES = (".s7p", ".s7l")


def _is_step7_zip(path: Path) -> bool:
    try:
        with zipfile.ZipFile(path) as zf:
            return any(n.lower().endswith(S7_SUFFIXES) for n in zf.namelist())
    except zipfile.BadZipFile:
        return False


def reference_projects(root: Path | None = None) -> list[Path]:
    root = root or S7_SAMPLES
    if not root.is_dir():
        return []
    found = [p for p in root.rglob("*.zip") if _is_step7_zip(p)]
    found += [p for p in root.rglob("*") if p.suffix.lower() in S7_SUFFIXES]
    return sorted(found)


@pytest.fixture
def s7_reference_projects() -> list[Path]:
    projects = reference_projects()
    if not projects:
        pytest.skip("no STEP 7 V5.x sample projects in samples/s7classic")
    return projects


# SUBBLKTYP of the block header records in SUBBLK.DBF (OB, DB, FC, SFC, FB, SFB)
_SUBBLK_TYPES = {8: "OB", 10: "DB", 12: "FC", 13: "SFC", 14: "FB", 15: "SFB"}
_F_BLOCK_BIT = 0x40


def _subblk_f_blocks(raw: bytes) -> set[str]:
    """F-blocks (``"FB 211"``) from a SUBBLK.DBF, read independently of s7dump (dBase III)."""
    count = int.from_bytes(raw[4:8], "little")
    header, record = int.from_bytes(raw[8:10], "little"), int.from_bytes(raw[10:12], "little")
    fields: dict[str, tuple[int, int]] = {}
    offset, pos = 1, 32
    while raw[pos] != 0x0D:
        name = raw[pos : pos + 11].split(b"\0")[0].decode("ascii")
        fields[name] = (offset, raw[pos + 16])
        offset, pos = offset + raw[pos + 16], pos + 32

    def field(rec: bytes, name: str) -> str:
        start, length = fields[name]
        return rec[start : start + length].decode("latin-1").strip()

    found: set[str] = set()
    for i in range(count):
        rec = raw[header + i * record : header + (i + 1) * record]
        if rec[:1] == b"*" or len(rec) < record:
            continue
        kind = _SUBBLK_TYPES.get(int(field(rec, "SUBBLKTYP") or 0))
        attribute = field(rec, "ATTRIBUTE")
        if kind and attribute.isdigit() and int(attribute) & _F_BLOCK_BIT:
            found.add(f"{kind} {int(field(rec, 'BLKNUMBER'))}")
    return found


def f_blocks_in_zip(path: Path) -> set[str]:
    """The F-blocks of a zipped STEP 7 project (empty for projects without a safety program)."""
    with zipfile.ZipFile(path) as zf:
        tables = [n for n in zf.namelist() if n.lower().endswith("/subblk.dbf")]
        return set().union(*(_subblk_f_blocks(zf.read(n)) for n in tables)) if tables else set()


_IP_FIELD = bytes.fromhex("E00F0000E00F0000")  # field 0x0FE0 written twice, as STEP 7 does


def ips_in_zip(path: Path) -> set[str]:
    """IP addresses in S7Netze/S7NONFGX.tab, read independently of s7dump: after the IP field
    marker, a length byte at +19 and 8 hex digits at +20."""
    found: set[str] = set()
    with zipfile.ZipFile(path) as zf:
        for name in (n for n in zf.namelist() if n.lower().endswith("s7netze/s7nonfgx.tab")):
            buf = zf.read(name)
            pos = buf.find(_IP_FIELD)
            while pos >= 0:
                text = buf[pos + 20 : pos + 20 + buf[pos + 19]].decode("ascii", "replace")
                if len(text) == 8 and all(c in "0123456789abcdefABCDEF" for c in text):
                    found.add(".".join(str(int(text[i : i + 2], 16)) for i in range(0, 8, 2)))
                pos = buf.find(_IP_FIELD, pos + 1)
    return found


def _dbf_rows(raw: bytes) -> list[dict[str, str]]:
    count = int.from_bytes(raw[4:8], "little")
    header, record = int.from_bytes(raw[8:10], "little"), int.from_bytes(raw[10:12], "little")
    fields: list[tuple[str, int, int]] = []
    offset, pos = 1, 32
    while raw[pos] != 0x0D:
        fields.append((raw[pos : pos + 11].split(b"\0")[0].decode("ascii"), offset, raw[pos + 16]))
        offset, pos = offset + raw[pos + 16], pos + 32
    rows = []
    for i in range(count):
        rec = raw[header + i * record : header + (i + 1) * record]
        if rec[:1] != b"*" and len(rec) == record:
            rows.append({n: rec[o : o + ln].decode("latin-1").strip() for n, o, ln in fields})
    return rows


def io_ranges_in_zip(path: Path) -> set[tuple[str, int, int]]:
    """(``I``/``Q``, start byte, length) of every I/O range in hOmSave7/s7hstatx/HADDRES3, read
    independently of s7dump: 36-byte entries in the memo, start and length as UInt16 at 32/34."""
    found: set[tuple[str, int, int]] = set()
    with zipfile.ZipFile(path) as zf:
        names = {n.lower(): n for n in zf.namelist()}
        for low, name in names.items():
            if not low.endswith("s7hstatx/haddres3.dbf"):
                continue
            memo = zf.read(names[low[:-4] + ".dbt"]) if low[:-4] + ".dbt" in names else b""
            for row in _dbf_rows(zf.read(name)):
                area = (
                    "I"
                    if "INADDR" in row["LISTNAME"]
                    else "Q"
                    if "OUTADDR" in row["LISTNAME"]
                    else ""
                )
                if not area or not row["MEMOARRAYA"].isdigit():
                    continue
                start = int(row["MEMOARRAYA"]) * 512 + 8
                for i in range(int(row["LISTCOUNT"] or 0)):
                    e = start + i * int(row["LISTLEN"])
                    begin, length = (
                        int.from_bytes(memo[e + k : e + k + 2], "little") for k in (32, 34)
                    )
                    if length:
                        found.add((area, begin, length))
    return found


def _string_before(raw: bytes, end: int) -> str:
    """The length-prefixed string that ends right before ``end`` (the module name of a table
    row stands directly in front of its order number); empty when there is none."""
    for n in range(1, min(end, 80)):
        start = end - n
        if raw[start - 1] == n and all(32 <= c < 127 or c >= 160 for c in raw[start:end]):
            return raw[start:end].decode("latin-1")
    return ""


_SIEMENS_ORDER_NO = re.compile(r"\d[A-Z]{2}\d \d{3}-[0-9A-Z]{5}-[0-9A-Z]{4}")


def siemens_order_numbers_in_zip(path: Path) -> dict[str, set[str]]:
    """Every Siemens order number (``6ES7 138-4FA03-0AB0``) per station table file
    (hOmSave7/s7hstatx/*.s7h), read independently of s7dump: any length-prefixed string that is
    one, wherever it stands in the file. A project may keep the file of a deleted station.

    Order numbers of RJ45 port rows are left out: a row ``Port 1 RJ45`` names the
    built-in network interface of its module (a PN/PN coupler's bus adapter in the myNetwor
    sample), and ports are not exported as modules."""
    found: dict[str, set[str]] = {}
    with zipfile.ZipFile(path) as zf:
        for name in zf.namelist():
            if "s7hstatx/" not in name.lower() or not name.lower().endswith(".s7h"):
                continue
            raw = zf.read(name)
            orders = found.setdefault(name, set())
            for i in range(len(raw) - 19):
                if (
                    raw[i] == 19
                    and _SIEMENS_ORDER_NO.fullmatch(text := raw[i + 1 : i + 20].decode("latin-1"))
                    and "RJ45" not in _string_before(raw, i).upper()
                ):
                    orders.add(text)
    return {name: orders for name, orders in found.items() if orders}


# STEP 7 V5.x data block layout, written from the layout rules (not from the library):
# BOOL bit-packed; BYTE/CHAR one byte; every other elementary type, STRUCT, ARRAY and STRING
# starts on an even byte; STRUCT/ARRAY/STRING/block sizes are padded to an even byte count.
_SIZES = {"BYTE": 1, "CHAR": 1, "WORD": 2, "INT": 2, "DATE": 2, "S5TIME": 2, "BLOCK_DB": 2,
          "BLOCK_FB": 2, "BLOCK_FC": 2, "BLOCK_SDB": 2, "TIMER": 2, "COUNTER": 2, "DWORD": 4,
          "DINT": 4, "REAL": 4, "TIME": 4, "TIME_OF_DAY": 4, "POINTER": 6, "DATE_AND_TIME": 8,
          "ANY": 10}  # fmt: skip
_ARRAY = re.compile(r"^ARRAY\s*\[(.+?)\]\s*OF\s+(.+)$", re.IGNORECASE)
_STRING = re.compile(r"^STRING\s*\[\s*(\d+)\s*\]$", re.IGNORECASE)
_INSTANCE = re.compile(r"^S?FB\s*\d+$", re.IGNORECASE)
_PARAMETER_SECTIONS = ("IN", "OUT", "IN_OUT")


def _even(bits: int) -> int:
    return -(-bits // 16) * 16


def _count(dims: str) -> int:
    n = 1
    for d in dims.split(","):
        low, high = (int(x) for x in d.split(".."))
        n *= high - low + 1
    return n


def step7_offsets(members: list[dict[str, Any]], bits: int = 0) -> tuple[dict[int, str], int]:
    """Offsets (``byte.bit``) of ``members`` (s7dump member dicts, laid out from bit ``bits``),
    keyed by ``id()`` of each member dict, and the bit position after the last one. Instance
    DBs: members carry ``section`` and each section starts on an even byte; IN_OUT parameters of
    a compound type are 6-byte pointers (their members have no place in the DB)."""
    found: dict[int, str] = {}
    section: str | None = None
    for m in members:
        if m.get("section") != section:
            section = m.get("section")
            bits = _even(bits)
        typ = str(m["type"]).strip()
        array = _ARRAY.match(typ)
        element = array.group(2).strip() if array else typ
        count = _count(array.group(1)) if array else 1
        compound = bool(array or m["members"] or _STRING.match(element) or _INSTANCE.match(typ))
        if element.upper() == "BOOL" and not array:
            found[id(m)] = f"{bits // 8}.{bits % 8}"
            bits += 1
            continue
        if section == "IN_OUT" and compound:
            bits = _even(bits)
            found[id(m)] = f"{bits // 8}.0"
            bits += 48
            continue
        one_byte = not compound and _SIZES[element.upper()] == 1
        bits = -(-bits // 8) * 8 if one_byte else _even(bits)
        found[id(m)] = f"{bits // 8}.0"
        start = bits
        if _INSTANCE.match(typ):  # multi-instance: size from the library
            bits += 8 * int(m["length"])
        elif m["members"]:  # STRUCT / UDT, or ARRAY OF STRUCT / UDT: element 0 is listed
            inner, end = step7_offsets(m["members"], start)
            found |= inner
            bits = start + _even(end - start) * count
        elif match := _STRING.match(element):
            bits += _even(8 * (int(match.group(1)) + 2)) * count
        elif element.upper() == "BOOL":
            bits += count
        else:
            bits += 8 * _SIZES[element.upper()] * count
        if compound:
            bits = start + _even(bits - start)
    return found, bits


# the tail of a compiled connection record (sdb/*/*.PG), read independently of s7dump
_CONNECTION_TAIL = re.compile(
    rb"\x1c\x01\x08\x02\x00([\x00\x01])\x00\x00(..)\x03\x03..\x04\x04(..)\x06\x06(....)\x04\x07(..)\Z",
    re.S,
)


def compiled_connections_in_zip(path: Path) -> set[tuple[int, bool, str, str, str]]:
    """``(local ID, active, local TSAP, partner IP, partner TSAP)`` of every compiled connection
    record of a zipped STEP 7 project. Records of deleted connections may still be among them."""
    found: set[tuple[int, bool, str, str, str]] = set()
    with zipfile.ZipFile(path) as zf:
        for name in zf.namelist():
            parts = name.lower().split("/")
            if "sdb" not in parts or not name.lower().endswith(".pg"):
                continue
            m = _CONNECTION_TAIL.search(zf.read(name))
            if m:
                active, ident, local, ip, partner = m.groups()
                found.add(
                    (
                        int.from_bytes(ident, "big"),
                        active == b"\x01",
                        f"{local[0]:02X}.{local[1]:02X}",
                        ".".join(str(b) for b in ip),
                        f"{partner[0]:02X}.{partner[1]:02X}",
                    )
                )
    return found
