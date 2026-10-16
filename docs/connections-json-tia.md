# `connections.json` of a TIA export

The file format is [`connections-json.md`](connections-json.md),
unchanged (format version 1). This page fixes how a TIA export fills it; the example is the
expected content for `PLC_1` of the reference sample (owner-confirmed values). PLC_2's export holds the mirrored end
`0x0110` (192.168.1.5, active, TSAPs `SIMATIC-ACC11001` / `SIMATIC-ACC10201`, partner `PLC_1`
192.168.1.1). The `couplers[]` of PLC_1 are fixed by the golden export.

```json
{
  "connections": [
    {
      "active": true,
      "details": "read",
      "kind": "s7",
      "local": {
        "address": "192.168.1.1",
        "id": "0x0100",
        "interface": "S7-1500/ET200MP-Station_1/X2/Ethernet",
        "module": "S7-1500/ET200MP-Station_1/PLC_1",
        "tsap": "14.01"
      },
      "name": "S7_Verbindung_1",
      "partner": {"address": "192.168.1.50", "rack": 0, "slot": 2, "specified": false, "tsap": "15.02"},
      "ref": "S7-1500/ET200MP-Station_1/PLC_1/0x0100"
    },
    {
      "active": true,
      "details": "read",
      "kind": "s7",
      "local": {
        "address": "192.168.1.1",
        "id": "0x0101",
        "interface": "S7-1500/ET200MP-Station_1/X2/Ethernet",
        "module": "S7-1500/ET200MP-Station_1/PLC_1",
        "tsap": "10.01"
      },
      "name": "S7_Verbindung_2",
      "partner": {"address": "192.168.1.70", "rack": 0, "slot": 1, "specified": false, "tsap": "11.01"},
      "ref": "S7-1500/ET200MP-Station_1/PLC_1/0x0101"
    },
    {
      "active": false,
      "details": "read",
      "kind": "s7",
      "local": {
        "address": "192.168.1.1",
        "id": "0x0102",
        "interface": "S7-1500/ET200MP-Station_1/X2/Ethernet",
        "module": "S7-1500/ET200MP-Station_1/PLC_1",
        "tsap": "SIMATIC-ACC10201"
      },
      "name": "S7_Verbindung_3",
      "partner": {"address": "192.168.1.5", "name": "PLC_2", "rack": 0, "slot": 1,
                  "specified": false, "tsap": "SIMATIC-ACC11001"},
      "ref": "S7-1500/ET200MP-Station_1/PLC_1/0x0102"
    }
  ],
  "uses": [
    {
      "areas": [{"db": "Datenbaustein_1", "members": ["\"Datenbaustein_1\".write"],
                 "param": "SD_1", "pointer": "\"Datenbaustein_1\".write", "role": "send"}],
      "block": "BSEND",
      "called": "\"BSEND_DB\".BSEND",
      "connection": "S7-1500/ET200MP-Station_1/PLC_1/0x0100",
      "id": {"value": "0x0100"},
      "len": {"unresolved": "\"Datenbaustein_1\".Len1"},
      "network_no": 1,
      "r_id": {"value": "0x0000000B"},
      "unit": "Main"
    },
    {
      "areas": [{"db": "Datenbaustein_1", "members": ["\"Datenbaustein_1\".read"],
                 "param": "RD_1", "pointer": "\"Datenbaustein_1\".read", "role": "receive"}],
      "block": "BRCV",
      "called": "\"BRCV_DB\".BRCV",
      "connection": "S7-1500/ET200MP-Station_1/PLC_1/0x0101",
      "id": {"value": "0x0101"},
      "len": {"unresolved": "\"Datenbaustein_1\".Len2"},
      "network_no": 2,
      "r_id": {"value": "0x0000000A"},
      "unit": "Main"
    }
  ]
}
```

Rules specific to TIA (`python/src/plcexport/extractors/tia/mapping.py` has the full mapping):

- `partner.specified` is always `false`; a partner PLC of the same project is named in
  `partner.name` and paired across exports by address and TSAP.
- `sources`, `differences` and `one_way` are never written.
- The module and interface refs are those of the TIA export's `hardware.json`;
  the exact ref strings above follow the 2026-10-13 export of the sample and are fixed by the
  golden export.
- Couplers: `couplers[]` as in `connections-json.md`, one entry per coupler side placed in
  this export.
- A coupler finding (`coupler_side_without_controller`, `transfer_area_length_mismatch`) names
  the coupler side in the optional field `coupler`, a rack ref of `hardware.json` (additive;
  STEP 7 findings never have it).
