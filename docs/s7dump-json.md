# `s7dump` JSON output (version 1)

`s7dump` is a .NET 8 tool that reads STEP 7 V5.x projects without STEP 7. Its output is described
by the JSON Schema [`schema/s7dump.schema.json`](../schema/s7dump.schema.json); consumers should
validate a dump against it before using it.

## Command line

```text
s7dump <path to .s7p | .s7l | project folder> --out <dump.json>
       [--mnemonic en|de] [--no-sources] [--max-block-bytes N]
```

- Reads only. Opens the project from the path it is given (best: a copy of the project).
- Exit code 0: the JSON was written (it may contain `errors`). Exit code 2: the project could not
  be opened at all (message on stderr). Exit code 64: usage error. Anything else is a crash.
- Never writes anything except `--out`.

## Document

```json
{
  "dump_version": 1,
  "tool": {"name": "s7dump", "version": "1.0.0", "library_version": "…"},
  "project": {
    "name": "PRESS_1", "description": "…", "kind": "project|library",
    "step7_version": null, "encoding": "iso-8859-1",
    "languages": {"stored": "und", "maintained": []},
    "mnemonic": {"exported": "en", "project": "de"},
    "pcs7": false
  },
  "stations": [{"name": "SIMATIC 300(1)", "type": "S7-300"}],
  "cpus": [{"name": "CPU 315-2 DP", "station": "SIMATIC 300(1)", "rack": 0, "slot": 2,
            "order_no": "6ES7 315-2AG10-0AB0", "program": "S7-Programm(1)"}],
  "cps": [{"name": "CP 343-1", "station": "SIMATIC 300(1)", "rack": 0, "slot": 4,
           "order_no": "6GK7 343-1EX30-0XE0"}],
  "networks": [{"kind": "profinet|profibus|mpi|ethernet", "subnet": "PN/IE(1)",
                "node": "CPU 315-2 DP", "address": "192.168.0.1", "device_name": null}],
  "programs": [{
    "name": "S7-Programm(1)", "cpu": "CPU 315-2 DP",
    "catalog": {"blocks": 42, "sources": 3, "symbols": 512},
    "blocks": [{
      "type": "FB", "number": 10, "symbolic_name": "FB_Heating", "family": "HEAT",
      "version": "1.2", "author": "…", "language": "KOP", "know_how_protected": false,
      "title": "…", "description": "…",
      "mc7_size": 734, "f_block": false, "header_attribute": 1, "checksum": 41234,
      "attributes": [],
      "interface": [{"name": "TempActual", "section": "IN", "type": "REAL",
                     "start": null, "comment": "…", "members": []}],
      "networks": [{"no": 1, "title": "…", "comment": "…",
                    "stl": ["      A     #TempActual", "…"]}],
      "instance_of": null,
      "errors": []
    }],
    "sources": [{"name": "Heating.scl", "kind": "scl|stl", "text": "…",
                 "defines": ["FB 10"], "errors": []}],
    "symbols": [{"symbol": "I_Start", "address": "I 0.0", "type": "BOOL", "comment": "…"}]
  }],
  "pcs7_charts": [{"kind": "cfc|sfc", "name": "Mixer1", "location": "Plant/Unit1"}],
  "errors": [{"where": "block FC 5", "message": "…"}]
}
```

## Rules

- Values the library cannot provide are `null`/empty, for the consumer to fill in:
  `step7_version` (null), `languages.stored` (`"und"`), `languages.maintained` (empty), `pcs7`
  (false) and `pcs7_charts` (empty).
- `language` is the library's raw block language: `AWL/KOP/FUP/SCL/GRAPH/…` or
  `STL/LAD/FBD/…`; a consumer maps the German names (AWL→STL, KOP→LAD, FUP→FBD).
  It is `unknown` for a block the library could not decode; such a block has `errors`, and the
  tool goes on with the next block (one undecodable block used to end the run).
- All texts are decoded with the project encoding (sources from their bytes) and
  written as UTF-8. Undecodable bytes are replaced by `U+FFFD` **and** listed in `errors`
  (never dropped silently).
- `stl` lines are emitted exactly as the library converts them, in the requested mnemonic.
- `know_how_protected: true` blocks carry interface and texts but `networks: []`.
- `header_attribute` is the block's `ATTRIBUTE` value in the program's `SUBBLK.DBF` (read by
  `s7dump`; the library leaves `S7Block.BlockAttribute` at 0 for offline blocks), e.g. `1` for a
  linked standard block, `65` for an F-FB/F-FC, `97` for an F-DB. `f_block` is its bit 6
  (`0x40`, `S7BlockAtributes.FBlock`), `null` when the table cannot be read. `checksum` is the
  library's MC7 code checksum (`S7Block.CheckSum`, without DB actual values), `null` when the
  block could not be read. `attributes` are the entries of the block's Attributes tab with all
  their properties, as the library reads them. A dump without `f_block` means the F-block check
  did not run (older s7dump).
- `ethernet`: one entry per Ethernet node in `S7Netze/S7NONFGX.tab`:
  `{node, station, rack, slot, module, interface, io_system, device, ip, mask, router, mac,
  use_router, use_ip, use_iso}`; a PROFINET IO device has `device` (its number, `SUBSTATN`) and
  `io_system` instead of `rack`, linked to its module through relation 64 in `hOmSave7/*/HRELATI1.DBF` and the
  parent chain in `hOmSave7/*/HOBJECT1.DBF` (no hardware type IDs). These entries replace the
  library's Ethernet entries in `networks`, with `address` as `IP/prefix` when the mask is
  contiguous. A node no hardware object links to (the interface of a PG/PC station in the
  network configuration) has no `station`, `module` or `slot`; its `interface` is its module
  name in the network table (field `0x1001`), and it is a `networks` entry with that name as
  `node` and no `station`. A library Ethernet entry without `station` is replaced by
  the node of the same module name and IP address, so a CP the library reports without its
  station is one `networks` entry.
- `modules`: every module of the hardware configuration:
  `{key, station, rack, io_system, device, device_name, slot, name, catalog, order_no, firmware,
  inputs: [{start, length}], outputs: [{start, length}]}`. `rack` is set for central racks,
  `io_system`/`device`/`device_name` for PROFIBUS DP slaves and PROFINET IO devices (device =
  PROFIBUS address or device number). `name` is the object name, or attribute 110970 where the
  object name is a number (GSD modules). `catalog` is attribute 4098 as found; `order_no` and
  `firmware` come from the station's HW Config table file (`hOmSave7/s7hstatx/*.s7h`) when its
  row matches, else an order number spelled out in `catalog` (never completed by guessing).
  Modules of DP slaves and IO devices take `order_no` from their station's table
  rows with the same name when those agree on one value (a shortened `catalog` must be its
  start; rows of DP ID tables count only with that confirmation); the head of a PROFINET IO
  device takes the order number of the access point row (slot 0), matched by name ignoring case.
  A device head still without one, and its `firmware`, come from the IO system's
  device list row with the device's IP address (from `ethernet`; not when several rows or
  devices share it), else with its module name as device name ignoring case.
  Address ranges are in bytes, from `hOmSave7/s7hstatx/HADDRES3.DBF` (entries of submodules are
  added to their module); diagnostic addresses (length 0) are left out.
- `networks` entries carry `station` and, for IO devices, `device`; `programs` carry `station`
  (program names repeat across stations).
- Interface members carry `offset` (`byte.bit` in the block, as the library lays it out) and
  `length` (bytes). Instance DB members carry their FB `section`.
- Interface members carry `actual` (DB actual value) where it differs from `start`; DBs are read
  with actual values. `F_GLOBDB.F_PROG_SIG` holds the collective F-signature this way.
  A DB whose stored actual values are shorter than its declaration (the library runs past
  their end) is read again without them and carries `actual_values_read: false`; a
  consumer should warn that its actual values were not read. The field is absent
  otherwise.
- `catalog` holds the counts from the project's own tables; a consumer can compare them
  with what was decoded as a plausibility check.
- Paths from the project tables are looked up ignoring case (block folders are `0000000a` on
  disk and `0000000A` in the tables), so the tool reads the same on Linux as on Windows. A
  source whose file is still not found carries an error: the library's own reader alters
  such text (it drops `+`), so the project should be treated as unreliable.
- Titles, comments and descriptions may hold `\r\n` or `\n` as line break, depending on the
  platform the tool ran on; a consumer should turn both into `\n`.
- Order: programs by name, blocks by (type, number), sources by name, symbols by symbol.
