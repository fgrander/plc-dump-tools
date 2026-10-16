# `connections.json` (common export format, version 1, additive)

Extends [`common-format.md`](common-format.md). The
format version stays 1. An export without this file is valid; a reader treats it as "no
connection content". Keys are sorted, null and empty values are omitted, `false` is kept only
where the table below says so (same rules as the other JSON files of the format).

## File

```json
{
  "connections": [
    {
      "ref": "SIMATIC 300-Station/CPU 317F-2 PN/DP/0x0010",
      "name": "S7-Verbindung 2",
      "kind": "s7",
      "details": "read",
      "local": {
        "module": "SIMATIC 300-Station/0.2",
        "interface": "SIMATIC 300-Station/CPU 317F-2 PN/DP/ethernet",
        "address": "10.100.10.20",
        "id": "0x0010",
        "tsap": "11.02"
      },
      "partner": {
        "specified": false,
        "name": "HomePLC3",
        "address": "10.102.10.20",
        "rack": 0,
        "slot": 3,
        "tsap": "10.03"
      },
      "active": false,
      "one_way": true,
      "sources": {"active": "both", "partner_address": "both", "tsaps": "both"}
    }
  ],
  "uses": [
    {
      "unit": "Ethernet_Comm",
      "network_no": 2,
      "line": 31,
      "block": "BSEND",
      "called": "FB 12 #WritePLC3",
      "id": {"value": "0xAAAA"},
      "r_id": {"value": "0x00000010"},
      "areas": [
        {"param": "SD_1", "role": "send", "pointer": "P#DB4.DBX0.0 INT 1",
         "db": "DB_SEND_PLC3", "start": "0.0", "length_bytes": 2,
         "members": ["\"DB_SEND_PLC3\".DB_VAR"]}
      ],
      "len": {"unassigned": true},
      "findings": [
        {"code": "id_not_configured"},
        {"code": "id_r_id_maybe_swapped",
         "connection": "SIMATIC 300-Station/CPU 317F-2 PN/DP/0x0010"}
      ]
    }
  ],
  "couplers": [
    {
      "ref": "SIMATIC 300-Station/PROFINET-IO-System #1",
      "kind": "pn_pn",
      "order_no": "6ES7 158-3AD10-0XA0",
      "address": "10.100.10.10",
      "safety": true,
      "transfer_areas": [
        {"module": "SIMATIC 300-Station/PROFINET-IO-System #1.2", "direction": "in",
         "range": "%I2.0-%I13.7", "length_bytes": 12},
        {"module": "SIMATIC 300-Station/PROFINET-IO-System #1.2", "direction": "out",
         "range": "%Q2.0-%Q7.7", "length_bytes": 6}
      ]
    }
  ],
  "findings": [
    {"code": "connection_unused", "connection": "SIMATIC 300-Station/CPU 317F-2 PN/DP/0x0012"}
  ]
}
```

## Rules

- **Order**: `connections` by `ref`; `uses` by unit, network, line; `couplers` by `ref`;
  `findings` by code, then ref. Two exports of the same project are byte-identical
  (determinism).
- **IDs** are hex: connection IDs `0x` + 4 digits, R_IDs `0x` + 8 digits, upper case. TSAPs are
  two upper-case hex bytes joined by a dot, or, for a TIA connection with SIMATIC ACC, the text
  TIA Portal shows (`SIMATIC-ACC` + hex digits, e.g. `SIMATIC-ACC10201`).
- **Refs**: `local.module`, `local.interface`, `partner.module`, coupler `ref` and transfer
  `module` name entries of `hardware.json`; `unit` names a unit of the export; `connection`
  names a `ref` of this file. The validator checks all of them.
- **`kind`** is `s7` or `other`. For `other`, `type_id` holds the type number as stored in the
  project, `details` is `not_read`, and the entry has `ref`, `name`, `kind`, `type_id`,
  `local.module` and `local.id` only.
- **`line`** of a use is optional and not written by the STEP 7 extractor yet; `unit` and
  `network_no` locate the call.
- **Values as written**: `id`, `r_id`, `len` and each area are one of
  `{"value": ...}` / a resolved area, `{"unresolved": "<operand>"}`, `{"unassigned": true}`.
  Nothing is corrected. A finding never changes a value or adds a `connection` link.
- **`one_way`** is NetPro's "Einseitiger Verbindungsaufbau", kept with `false`; `index.md`
  shows it as a column "One-way".
- **`differences`**: `[{"field": "partner_tsap", "tables": "10.03", "compiled":
  "10.04"}]`; the fields of the entry then carry the compiled value, and the finding
  `tables_compiled_differ` is listed.
- **`safety: true`** on a connection, use or coupler whose module or unit is safety content.

## `index.md`

A section "Connections" at the end of `index.md`, after the file list (which also gets a row
for `connections.json`):

```markdown
## Connections

| ID | Name | Local | Partner | Partner address | TSAP local / partner | Sets up | One-way | Used by |
|---|---|---|---|---|---|---|---|---|
| 1 | S7-Verbindung 1 | CPU 317F-2 PN/DP | HomePLC2 | 10.101.10.20 | 10.02 / 10.02 | local | yes | Ethernet_Comm NW 1 (GET) |
| 10 | S7-Verbindung 2 | CPU 317F-2 PN/DP | HomePLC3 | 10.102.10.20 | 11.02 / 10.03 | partner | yes | – |
```

IDs are shown as NetPro shows them (hex, no prefix). Below the table: calls without a
connection with their findings, and the couplers with their transfer areas. A project without
connections gets the line "No connections configured."

## `coverage.json`

New **optional** category `connections` with the states of the format (`delivered`,
`partial` + reason, `unavailable` + `not_in_project`). An export without the category was not
checked for connections: an export written before this change, an extractor that does not read
them, or a dump of an older `s7dump`. Validator and reader accept that. The file
`connections.json` exists only when there is content; a project that was checked and has no
connection has the category (`unavailable`, `not_in_project`), the line "No connections
configured." in `index.md`, and no file.
