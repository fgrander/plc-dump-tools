"""Generate the synthetic s7dump fixtures.

Run: ``python tests/fixtures/s7dump/make_fixtures.py``.

They imitate what ``s7dump`` writes for a small S7-300 press project (contracts/s7dump-json.md):
LAD/FBD/SCL/STL blocks, timers, counters, register- and memory-indirect accesses, a DB with a
struct, a UDT, an instance DB, a VAT, an SFB reference, an SCL source and a symbol table.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

HERE = Path(__file__).parent


def member(
    name: str,
    type_: str,
    section: str | None = None,
    start: str | None = None,
    comment: str | None = None,
    members: list[Any] | None = None,
    offset: str | None = None,
    length: int | None = None,
) -> dict[str, Any]:
    m = {"name": name, "section": section, "type": type_, "start": start, "comment": comment,
         "members": members or []}  # fmt: skip
    if offset is not None:
        m |= {"offset": offset, "length": length}
    return m


def block(type_: str, number: int, name: str | None, language: str, **kw: Any) -> dict[str, Any]:
    b = {
        "type": type_, "number": number, "symbolic_name": name, "family": None, "version": None,
        "author": None, "language": language, "know_how_protected": False, "title": None,
        "description": None, "mc7_size": 0, "interface": [], "networks": [], "instance_of": None,
        "errors": [],
    }  # fmt: skip
    b.update(kw)
    return b


def nw(no: int, title: str | None, stl: list[str], comment: str | None = None) -> dict[str, Any]:
    return {"no": no, "title": title, "comment": comment, "stl": stl}


SYMBOLS = [
    ("DB_Heating", "DB 30", "FB 10", "Instanz Heizung"),
    ("DB_Recipe", "DB 20", "DB 20", "Rezeptdaten"),
    ("FB_Heating", "FB 10", "FB 10", "Heizplattenregelung"),
    ("FB_Valve", "FB 11", "FB 11", None),
    ("FC_Scale", "FC 5", "FC 5", "Analogwert skalieren"),
    ("I_Start", "I 0.0", "BOOL", "Start Taster"),
    ("I_Stop", "I 0.1", "BOOL", "Stopp Taster (Öffner)"),
    ("I_TempPlate", "PIW 256", "INT", "Plattentemperatur"),
    ("M_Run", "M 10.0", "BOOL", "Anlage läuft"),
    ("Main", "OB 1", "OB 1", "Hauptprogramm"),
    ("Q_Heater_On", "Q 4.1", "BOOL", "Heizung ein"),
    ("Q_Pump", "Q 4.0", "BOOL", "Hydraulikpumpe"),
    ("TON", "SFB 4", "SFB 4", None),
    ("UDT_Limits", "UDT 1", "UDT 1", None),
]


def base() -> dict[str, Any]:
    blocks = [
        block(
            "OB",
            1,
            "Main",
            "KOP",
            title="Hauptprogramm",
            mc7_size=180,
            family="MAIN",
            version="0.1",
            networks=[
                nw(
                    1,
                    "Pumpe Start/Stopp",
                    [
                        '      A     "I_Start"',
                        '      O     "M_Run"',
                        '      AN    "I_Stop"',
                        '      =     "Q_Pump"',
                        '      =     "M_Run"',
                    ],
                    comment="Selbsthaltung der Hydraulikpumpe",
                ),
                nw(
                    2,
                    "Heizung",
                    [
                        '      CALL  "FB_Heating" , "DB_Heating"',
                        '       TempActual:="I_TempPlate"',
                        '       HeaterOn  :="Q_Heater_On"',
                    ],
                ),
                nw(
                    3,
                    "Rezeptzähler",
                    [
                        '      L     "DB_Recipe".Counter',
                        "      L     1",
                        "      +I",
                        '      T     "DB_Recipe".Counter',
                    ],
                ),
            ],
        ),
        block(
            "FB",
            10,
            "FB_Heating",
            "FUP",
            title="Heizplattenregelung",
            family="HEAT",
            version="1.2",
            author="Max Mustermann",
            mc7_size=96,
            description="Begrenzt die Plattentemperatur auf TempLimit.",
            interface=[
                member("TempActual", "REAL", "IN"),
                member("HeaterOn", "BOOL", "OUT"),
                member("TempLimit", "REAL", "STAT", "2.500000e+002", "Maximale Plattentemperatur"),
                member("Valve", "FB11", "STAT", offset="10.0", length=4),
                member("t", "REAL", "TEMP"),
            ],
            networks=[
                nw(
                    1,
                    "Temperatur begrenzen",
                    [
                        "      L     #TempActual",
                        "      L     #TempLimit",
                        "      <R",
                        "      =     #HeaterOn",
                    ],
                ),
                nw(
                    2,
                    "Ventil",
                    [
                        "      CALL  #Valve",
                        "       Open    :=#HeaterOn",
                        "       Position:=#t",
                    ],
                ),
            ],
        ),
        block(
            "FB",
            11,
            "FB_Valve",
            "SCL",
            mc7_size=40,
            interface=[member("Open", "BOOL", "IN"), member("Position", "REAL", "OUT")],
            networks=[
                nw(
                    1,
                    None,
                    [
                        "      A     #Open",
                        "      JCN   M001",
                        "      L     1.000000e+002",
                        "      T     #Position",
                        "M001: NOP   0",
                    ],
                )
            ],
        ),
        block(
            "FC",
            5,
            "FC_Scale",
            "AWL",
            title="Analogwert skalieren",
            mc7_size=120,
            interface=[member("Raw", "INT", "IN"), member("RET_VAL", "REAL", "RETURN")],
            networks=[
                nw(
                    1,
                    "Skalieren",
                    ["      L     #Raw", "      ITD", "      DTR", "      T     #RET_VAL"],
                ),
                nw(
                    2,
                    "Zeiten, Zähler, indirekt",
                    [
                        "      A     M     10.0",
                        "      L     S5T#5S",
                        "      SE    T      5",
                        "      A     T      5",
                        "      =     Q      4.2",
                        "      A     I      0.3",
                        "      CU    C      3",
                        "      L     MW    20",
                        "      T     DB20.DBW    4",
                        "      L     IW [AR1,P#0.0]",
                        "      OPN   DB    20",
                        "      L     DBW [MD    10]",
                    ],
                ),
            ],
        ),
        block("SFB", 4, "TON", "STL"),
        block(
            "DB",
            20,
            "DB_Recipe",
            "DB",
            mc7_size=14,
            interface=[
                member("Counter", "INT", start="0", offset="0.0", length=2),
                member(
                    "Limits",
                    "STRUCT",
                    members=[
                        member("Max", "REAL", start="2.600000e+002", offset="2.0", length=4),
                        member("Min", "REAL", start="2.000000e+001", offset="6.0", length=4),
                    ],
                    offset="2.0",
                    length=8,
                ),
                member(
                    "Setpoint",
                    "REAL",
                    start="2.300000e+002",
                    comment="Sollwert",
                    offset="10.0",
                    length=4,
                ),
            ],
        ),
        block(
            "DB",
            30,
            "DB_Heating",
            "DB",
            mc7_size=14,
            instance_of="FB10",
            interface=[
                member("TempActual", "REAL", "IN", offset="0.0", length=4),
                member("HeaterOn", "BOOL", "OUT", offset="4.0", length=1),
                member("TempLimit", "REAL", "STAT", start="2.500000e+002", offset="6.0", length=4),
                member("Valve", "FB11", "STAT", offset="10.0", length=4),
            ],
        ),
        block(
            "UDT", 1, "UDT_Limits", "DB", interface=[member("Max", "REAL"), member("Min", "REAL")]
        ),
        block("VAT", 1, None, "STL", title="Beobachten Presse"),
    ]
    order = ["OB", "FB", "FC", "SFB", "SFC", "DB", "UDT", "VAT"]
    blocks.sort(key=lambda b: (order.index(b["type"]), b["number"]))
    symbols = [{"symbol": s, "address": a, "type": t, "comment": c} for s, a, t, c in SYMBOLS]
    source = "\n".join(
        [
            "FUNCTION_BLOCK FB 11", "TITLE = 'Ventil'", "VAR_INPUT", "  Open : BOOL;", "END_VAR",
            "VAR_OUTPUT", "  Position : REAL;", "END_VAR", "BEGIN", "  IF Open THEN",
            "    Position := 100.0;", "  END_IF;", "END_FUNCTION_BLOCK", "",
        ]
    )  # fmt: skip
    return {
        "dump_version": 1,
        "tool": {"name": "s7dump", "version": "1.0.0", "library_version": "4.4.10.0"},
        "project": {
            "name": "PRESS_1", "description": "Presse 1 Steuerung", "kind": "project",
            "step7_version": None, "encoding": "windows-1252",
            "languages": {"stored": "und", "maintained": []},
            "mnemonic": {"exported": "en", "project": "de"}, "pcs7": False,
        },
        "stations": [{"name": "SIMATIC 300(1)", "type": "Simatic300"}],
        "cpus": [{"name": "CPU 315-2 PN/DP", "station": "SIMATIC 300(1)", "rack": 0, "slot": 2,
                  "order_no": "6ES7 315-2EH14-0AB0", "type": "Simatic300",
                  "program": "S7 Program(1)"}],
        "cps": [{"name": "CP 343-1", "station": "SIMATIC 300(1)", "rack": 0, "slot": 4,
                 "order_no": None}],
        "networks": [
            {"kind": "ethernet", "subnet": None, "node": "CPU 315-2 PN/DP",
             "address": "192.168.0.10", "device_name": None},
            {"kind": "mpi", "subnet": None, "node": "CPU 315-2 PN/DP", "address": "2",
             "device_name": None},
        ],
        "programs": [{
            "name": "S7 Program(1)", "cpu": "CPU 315-2 PN/DP",
            "catalog": {"blocks": len(blocks), "sources": 1, "symbols": len(symbols)},
            "blocks": blocks,
            "sources": [{"name": "FB_Valve", "kind": "scl", "text": source, "defines": ["FB 11"],
                         "errors": []}],
            "symbols": symbols,
        }],
        "pcs7_charts": [],
        "errors": [],
    }  # fmt: skip


def variants() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {"press_s7300": base()}

    d = base()
    fb = next(b for b in d["programs"][0]["blocks"] if b["symbolic_name"] == "FB_Heating")
    fb["know_how_protected"], fb["networks"] = True, []
    out["protected"] = d

    d = base()
    fc = next(b for b in d["programs"][0]["blocks"] if b["symbolic_name"] == "FC_Scale")
    fc["errors"] = ["MC7 decoding failed at byte 42"]
    d["errors"] = [{"where": "S7 Program(1)/FC5", "message": "MC7 decoding failed at byte 42"}]
    out["decode_error"] = d

    d = base()
    d["programs"][0]["catalog"]["blocks"] += 1
    out["catalog_mismatch"] = d

    d = base()
    p2 = copy.deepcopy(d["programs"][0])
    p2["name"], p2["cpu"] = "S7 Program(2)", "CPU 317-2 DP"
    p2["blocks"] = [b for b in p2["blocks"] if b["type"] in ("OB", "FC")]
    p2["sources"], p2["symbols"] = [], [s for s in p2["symbols"] if s["symbol"] in ("I_Start",)]
    p2["catalog"] = {"blocks": len(p2["blocks"]), "sources": 0, "symbols": 1}
    d["programs"].append(p2)
    d["cpus"].append(
        {
            "name": "CPU 317-2 DP",
            "station": "SIMATIC 300(1)",
            "rack": 0,
            "slot": 3,
            "order_no": None,
            "type": "Simatic300",
            "program": "S7 Program(2)",
        }
    )
    out["two_programs"] = d

    d = base()
    d["project"]["pcs7"] = True
    d["pcs7_charts"] = [
        {"kind": "cfc", "name": "Mixer1", "location": "Plant/Unit1"},
        {"kind": "cfc", "name": "Dosing", "location": "Plant/Unit1"},
        {"kind": "sfc", "name": "Batch", "location": "Plant/Unit2"},
    ]
    out["pcs7"] = d

    d = base()
    d["project"]["kind"] = "library"
    out["library"] = d

    d = base()
    for b in d["programs"][0]["blocks"]:
        if b["type"] in ("OB", "FB", "FC"):
            b["know_how_protected"], b["networks"] = True, []
    out["all_protected"] = d

    # an S7 Distributed Safety program as the real Siemens example AS-FE-I-006
    # dumps it: header_attribute from SUBBLK.DBF (65 = linked + F-block, 97 for F-DBs, 1 for
    # standard blocks), f_block = bit 6, MC7 checksums, and the F-shared DB whose F_PROG_SIG
    # holds the collective signature as an actual value (start value 0)
    d = base()
    blocks = d["programs"][0]["blocks"]
    for n, b in enumerate(blocks):
        b["f_block"], b["header_attribute"], b["checksum"], b["attributes"] = False, 1, 1000 + n, []
    blocks.append(
        block(
            "FB", 100, "F_EStop", "FFUP", f_block=True, header_attribute=65, checksum=23100,
            attributes=[], title="Not-Halt Presse",
            interface=[member("ESTOP", "BOOL", "IN", comment="Not-Halt Kanal")],
            networks=[nw(1, "Not-Halt", ["U     #ESTOP", "=     \"Q_Pump\""])],
        )
    )  # fmt: skip
    blocks.append(
        block("DB", 101, "F_DB_EStop", "unkown", f_block=True, header_attribute=97,
              checksum=4711, attributes=[], instance_of="FB100")
    )  # fmt: skip
    sig = member("F_PROG_SIG", "DWORD", start="DW#16#0")
    sig["actual"] = "DW#16#626E0828"
    blocks.append(
        block("DB", 818, "F_GLOBDB", "unkown", f_block=True, header_attribute=97, checksum=10574,
              attributes=[], interface=[member("DB_VERSION", "WORD", start="W#16#402"), sig])
    )  # fmt: skip
    d["programs"][0]["catalog"]["blocks"] += 3
    out["safety"] = d

    # 004 IP extraction: s7dump reads the Ethernet settings from S7Netze/S7NONFGX.tab and the
    # hardware tables; the CP 343-1 is a type the library does not know, so it is not in "cps",
    # and the drive is a PROFINET IO device (device 1 on the IO system, its own slot 1)
    d = base()
    d["cps"] = []
    eth = {"rack": 0, "interface": None, "io_system": None, "device": None, "router": None,
           "mac": "08-00-06-01-00-00", "use_router": False, "use_ip": True,
           "use_iso": False}  # fmt: skip
    st = "SIMATIC 300(1)"
    d["ethernet"] = [
        {"node": 4, **eth, "station": st, "slot": 2, "module": "CPU 315-2 PN/DP",
         "interface": "PN-IO", "ip": "192.168.0.10", "mask": "255.255.255.0"},
        {"node": 7, **eth, "station": st, "slot": 4, "module": "CP 343-1", "ip": "10.1.2.20",
         "mask": "255.255.0.0"},
        {"node": 21, **eth, "station": st, "rack": None, "slot": 1, "module": "AKD-PN",
         "interface": "AKD-PN", "io_system": "PROFINET-IO-System", "device": 1,
         "ip": "192.168.0.11", "mask": "255.255.255.0"},
    ]  # fmt: skip
    net = {"subnet": None, "station": st, "device": None, "device_name": None}
    d["networks"] = [
        {**net, "kind": "ethernet", "node": "AKD-PN", "device": 1, "address": "192.168.0.11/24"},
        {**net, "kind": "ethernet", "node": "CP 343-1", "address": "10.1.2.20/16"},
        {**net, "kind": "ethernet", "node": "CPU 315-2 PN/DP", "address": "192.168.0.10/24"},
        {**net, "kind": "mpi", "node": "CPU 315-2 PN/DP", "address": "2"},
    ]  # fmt: skip
    out["ethernet"] = d

    # every module from the hardware tables with its I/O address ranges (bytes);
    # channels link the symbols I_Start/I_Stop, Q_Pump/Q_Heater_On and I_TempPlate (PIW 256)
    d = base()
    d["cps"][0]["slot"] = 7  # a CP the hardware tables do not list (library entry only)
    st = "SIMATIC 300(1)"
    mod = {"station": st, "rack": 0, "io_system": None, "device": None, "device_name": None,
           "subslot": None, "catalog": None, "order_no": None, "firmware": None,
           "inputs": [], "outputs": []}  # fmt: skip
    d["modules"] = [
        {**mod, "key": "2363560:2", "slot": 2, "name": "CPU 315-2 PN/DP", "catalog": "CPU",
         "firmware": "V3.2"},
        {**mod, "key": "1314842:3", "slot": 4, "name": "DI16xDC24V",
         "catalog": "_S7H_6ES7_321_1BH02_0AA~", "order_no": "6ES7 321-1BH02-0AA0",
         "inputs": [{"start": 0, "length": 2}]},
        {**mod, "key": "1314843:4", "slot": 5, "name": "DO16xDC24V/0.5A",
         "catalog": "_S7H_6ES7_322_1BH01_0AA~", "outputs": [{"start": 4, "length": 2}]},
        {**mod, "key": "1314850:5", "slot": 6, "name": "AI2x12Bit",
         "inputs": [{"start": 256, "length": 4}]},
        {**mod, "key": "1316805:82", "rack": None, "io_system": "PROFINET-IO-System",
         "device": 1, "device_name": "AKD-PN", "slot": 2, "name": "AKD Telegramm",
         "inputs": [{"start": 300, "length": 10}], "outputs": [{"start": 300, "length": 24}]},
        {**mod, "key": "1338070:1", "slot": 8, "name": "CP 443-1 Advanced", "catalog": "CP",
         "order_no": "6GK7 443-1EX40-0XE0", "firmware": "V2.4"},
    ]  # fmt: skip
    # the library lists this CP without its station (seen in a Pepperl+Fuchs sample)
    d["cps"].append({"name": "CP 443-1 Advanced", "station": None, "rack": 0, "slot": 8,
                     "order_no": None})  # fmt: skip
    out["modules"] = d

    # a PN/PN coupler with a PROFIsafe transfer module and a DP/DP coupler, next to
    # the drive of the `modules` variant (an ordinary IO device, no coupler); one input symbol
    # lies in the PN/PN coupler's transfer area. No connections are configured
    d = copy.deepcopy(out["modules"])
    pn = {**mod, "rack": None, "io_system": "PROFINET-IO-System", "device": 2,
          "device_name": "PN-PN-Coupler"}  # fmt: skip
    dp = {**mod, "rack": None, "io_system": "DP master system", "device": 5,
          "device_name": "DP/DP-Koppler"}  # fmt: skip
    d["modules"] += [
        {**pn, "key": "2365840:2", "slot": 1, "name": "6ES7 158-3AD10-0XA0",
         "order_no": "6ES7 158-3AD10-0XA0", "firmware": "V4.2"},
        {**pn, "key": "2365692:5", "slot": 2, "name": "PROFIsafe IN/OUT 12 Byt~",
         "inputs": [{"start": 2, "length": 12}], "outputs": [{"start": 2, "length": 6}]},
        {**dp, "key": "1316000:1", "slot": 0, "name": "DP/DP Coupler",
         "order_no": "6ES7 158-0AD01-0XA0"},
        {**dp, "key": "1316001:2", "slot": 1, "name": "4 Byte IN / 4 Byte OUT",
         "inputs": [{"start": 100, "length": 4}], "outputs": [{"start": 100, "length": 4}]},
    ]  # fmt: skip
    prog = d["programs"][0]
    prog["symbols"].append({"symbol": "I_Release_From_B", "address": "I 2.0", "type": "BOOL",
                            "comment": "Freigabe von Maschine B"})  # fmt: skip
    prog["symbols"].sort(key=lambda x: x["symbol"])
    prog["catalog"]["symbols"] += 1
    d["connections"] = []
    out["couplers"] = d

    # configured connections (NetPro) of the CPU, on the hardware of the `ethernet`
    # variant: both sources equal; a compiled partner TSAP that differs from the tables; a
    # partner inside the project (the CP); another connection type; no compiled record; a list
    # whose owner module was not found
    d = copy.deepcopy(out["ethernet"])
    owner = {"station": st, "rack": 0, "slot": 2, "module": "CPU 315-2 PN/DP"}
    con = {"list": 1, "owner": owner, "local_node": 4, "partner_node": None, "type_id": 1332225,
           "active": True, "one_way": True, "unspecified": True}  # fmt: skip
    no_partner = {"partner_name": None, "partner_rack": None, "partner_slot": None,
                  "partner_resource": None, "partner_ip": None}  # fmt: skip

    def partner(name: str, slot: int, resource: int, ip: str) -> dict[str, Any]:
        return {"partner_name": name, "partner_rack": 0, "partner_slot": slot,
                "partner_resource": resource, "partner_ip": ip}  # fmt: skip

    def compiled(file: str, active: bool, local: str, ip: str, far: str) -> dict[str, Any]:
        return {"file": f"sdb/00000001/{file}.PG", "active": active, "local_tsap": local,
                "partner_ip": ip, "partner_tsap": far}  # fmt: skip

    d["connections"] = [
        {**con, "name": "S7-Verbindung 1", "local_id": 1,
         "tables": {"local_resource": 16, **partner("HomePLC2", 2, 16, "10.101.10.20")},
         "compiled": compiled("00000030", True, "10.02", "10.101.10.20", "10.02")},
        {**con, "name": "S7-Verbindung 2", "local_id": 16, "active": False,
         "tables": {"local_resource": 17, **partner("HomePLC3", 3, 16, "10.102.10.20")},
         "compiled": compiled("0000002f", False, "11.02", "10.102.10.20", "10.04")},
        {**con, "name": "S7-Verbindung 3", "local_id": 2, "unspecified": False, "partner_node": 7,
         "tables": {"local_resource": 18, **no_partner},
         "compiled": compiled("00000031", True, "12.02", "10.1.2.20", "03.04")},
        {**con, "name": "ISO-on-TCP-Verbindung 1", "local_id": 3, "type_id": 1332999,
         "tables": {"local_resource": 19, **no_partner}, "compiled": None},
        {**con, "name": "S7-Verbindung 4", "local_id": 4,
         "tables": {"local_resource": 20, **partner("Unbekannt", 0, 3, "10.5.5.5")},
         "compiled": None},
        {**con, "list": 2, "owner": None, "local_node": None, "name": "S7-Verbindung 5",
         "local_id": 5, "tables": {"local_resource": 16, **partner("Fremd", 2, 16, "10.9.9.9")},
         "compiled": None},
    ]  # fmt: skip
    # the program uses the connections: GET over ID 1 with a remote and a local area,
    # BSEND with ID and R_ID swapped and a length from a variable, BRCV over ID 2 without a data
    # area; a protected block whose calls cannot be read. `raw_stl` is what s7dump emits without
    # call reconstruction (contracts/s7dump-connections.md)
    prog = d["programs"][0]
    prog["station"] = st
    template = next(b for b in prog["blocks"] if b["symbolic_name"] == "FB_Valve")

    def comm_block(
        type_: str, number: int, name: str, interface: list[Any], **more: Any
    ) -> dict[str, Any]:
        b = copy.deepcopy(template)
        b |= {"type": type_, "number": number, "symbolic_name": name, "family": None,
              "version": None, "author": None, "language": "AWL", "title": None,
              "description": None, "interface": interface, "networks": [], **more}  # fmt: skip
        return b

    def io(name: str, section: str, type_: str, offset: str, length: int) -> dict[str, Any]:
        return member(name, type_, section, offset=offset, length=length)

    get = [io("REQ", "IN", "BOOL", "0.0", 1), io("ID", "IN", "WORD", "2.0", 2),
           io("NDR", "OUT", "BOOL", "4.0", 1), io("ERROR", "OUT", "BOOL", "4.1", 1),
           io("STATUS", "OUT", "WORD", "6.0", 2), io("ADDR_1", "IN_OUT", "ANY", "8.0", 10),
           io("RD_1", "IN_OUT", "ANY", "48.0", 10)]  # fmt: skip
    bsend = [io("REQ", "IN", "BOOL", "0.0", 1), io("R", "IN", "BOOL", "0.1", 1),
             io("ID", "IN", "WORD", "2.0", 2), io("R_ID", "IN", "DWORD", "4.0", 4),
             io("DONE", "OUT", "BOOL", "8.0", 1), io("ERROR", "OUT", "BOOL", "8.1", 1),
             io("STATUS", "OUT", "WORD", "10.0", 2), io("SD_1", "IN_OUT", "ANY", "12.0", 10),
             io("LEN", "IN_OUT", "WORD", "22.0", 2)]  # fmt: skip
    brcv = [io("EN_R", "IN", "BOOL", "0.0", 1), io("ID", "IN", "WORD", "2.0", 2),
            io("R_ID", "IN", "DWORD", "4.0", 4), io("NDR", "OUT", "BOOL", "8.0", 1),
            io("ERROR", "OUT", "BOOL", "8.1", 1), io("STATUS", "OUT", "WORD", "10.0", 2),
            io("RD_1", "IN_OUT", "ANY", "12.0", 10),
            io("LEN", "IN_OUT", "WORD", "22.0", 2)]  # fmt: skip
    comm = comm_block(
        "FB", 40, "FB_Comm",
        [io("Read", "STAT", "SFB14", "0.0", 90), io("Send", "STAT", "FB12", "90.0", 366),
         io("Recv", "STAT", "FB13", "456.0", 368)],
        language="KOP",
        networks=[
            {"no": 1, "title": "Daten von PLC2 lesen", "comment": None,
             "stl": ['      CALL  #Read (', "            ID     := W#16#1,",
                     "            ADDR_1 := P#DBX 0.0 BYTE 1,", "            RD_1   :=  BYTE )"],
             "raw_stl": ["      BLD   16", "      TAR2  LD1", "      L     1",
                         "      T     #Read.IN.ID", "      L     W#16#1005",
                         "      T     #Read.IN_OUT.ADDR_1", "      L     1",
                         "      T     DIW[AR2,P#10.0]", "      L     1",
                         "      T     DIW[AR2,P#12.0]", "      L     P#DBX 0.0",
                         "      T     DID[AR2,P#14.0]", "      L     W#16#1008",
                         "      T     #Read.IN_OUT.RD_1", "      L     2",
                         "      T     DIW[AR2,P#50.0]", "      L     20",
                         "      T     DIW[AR2,P#52.0]", "      L     P#DBX 2.0",
                         "      T     DID[AR2,P#54.0]", "      +AR2  P#0.0",
                         '      UC    "GET"', "      BLD   17", "      NOP   0"]},
            {"no": 2, "title": "Daten an PLC3 senden", "comment": None,
             "stl": ['      CALL  #Send (', "            ID     := -21846,",
                     "            R_ID   := L#16,", "            SD_1   := P#DBX 0.0 BYTE 1,",
                     "            LEN    := MW 10 )"],
             "raw_stl": ["      BLD   14", "      TAR2  LD1", "      L     -21846",
                         "      T     #Send.IN.ID", "      L     L#16", "      T     #Send.IN.R_ID",
                         "      L     W#16#1008", "      T     #Send.IN_OUT.SD_1", "      L     1",
                         "      T     DIW[AR2,P#104.0]", "      L     20",
                         "      T     DIW[AR2,P#106.0]", "      L     P#DBX 10.0",
                         "      T     DID[AR2,P#108.0]", "      L     MW 10",
                         "      T     #Send.IN_OUT.LEN", "      +AR2  P#90.0",
                         '      UC    "BSEND"', "      BLD   15", "      NOP   0"]},
            {"no": 3, "title": "Daten aus dem Projekt empfangen", "comment": None,
             "stl": ['      CALL  #Recv (', "            ID     := W#16#2,",
                     "            R_ID   := DW#16#1,", "            RD_1   :=  BYTE ,",
                     "            LEN    := )"],
             "raw_stl": ["      BLD   14", "      TAR2  LD1", "      L     W#16#2",
                         "      T     #Recv.IN.ID", "      L     DW#16#1",
                         "      T     #Recv.IN.R_ID",
                         "      +AR2  P#456.0", '      UC    "BRCV"', "      BLD   15",
                         "      NOP   0"]},
        ],
    )  # fmt: skip
    prog["blocks"] += [
        comm,
        comm_block("FB", 41, "FB_Secret", [], know_how_protected=True),
        comm_block("FB", 12, "BSEND", bsend, know_how_protected=True),
        comm_block("FB", 13, "BRCV", brcv, know_how_protected=True),
        comm_block("SFB", 14, "GET", get),
    ]
    prog["symbols"] += [
        {"symbol": name, "address": address, "type": address, "comment": None}
        for name, address in (("FB_Comm", "FB 40"), ("FB_Secret", "FB 41"), ("BSEND", "FB 12"),
                              ("BRCV", "FB 13"), ("GET", "SFB 14"))
    ]  # fmt: skip
    prog["symbols"].sort(key=lambda x: x["symbol"])
    prog["catalog"]["blocks"] += 5
    prog["catalog"]["symbols"] += 5
    out["connections"] = d
    return out


if __name__ == "__main__":
    for name, doc in variants().items():
        (HERE / f"{name}.json").write_text(
            json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
        )
        print(name)
