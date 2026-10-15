# `tiadump`: connections in `dump.json` (`tiadump project`, dump_version 1, additive)

Extends [`tiadump.md`](tiadump.md). [`tiadump.schema.json`](../schema/tiadump.schema.json) has the keys below; dumps without them stay valid.

## PLC device entry

```jsonc
{
  "name": "PLC_1", "kind": "plc", "...": "...",
  "configured_connections": [                     // sorted by local_id, then local_name
    {
      "class": "S7Connection",                    // Openness class name
      "type": "S7Connection",                     // Connection.ConnectionType as text
      "type_value": 0,                            // its numeric value (for kind "other")
      "owner_item": "PLC_1",                      // device item that holds the connection
      "local_name": "S7_Verbindung_1",
      "local_id": "100",                          // LocalConnectionId, text as Openness gives it
      "local_address": "192.168.1.1",
      "local_interface": "X2",                     // name of the local Node (as hardware.json "node")
      "local_node_type": "Ethernet",               // its NodeType (as hardware.json "type")
      "local_subnet": "PN/IE_1",
      "local_rack": 0, "local_slot": 1,
      "local_tsap": "14.01",                       // or "SIMATIC-ACC10201" with SIMATIC ACC
      "use_acc": false,                           // LocalUseSimaticACC
      "local_active": true,
      "partner_name": null,                       // partner PLC name when PartnerTarget is set
      "partner_id": null,                         // PartnerConnectionId (set for a partner in the project)
      "partner_address": "192.168.1.50",
      "partner_rack": 0, "partner_slot": 2,
      "partner_tsap": "15.02",
      "partner_active": false,
      "valid": true                               // Connection.IsValid
    }
  ],
  "configured_connections_error": null            // text when the list could not be read
}
```

- Every value is copied as found; `null` when Openness gives none or an empty string.
- `class`/`type` other than `S7Connection`: the same keys, those that the class has.
- Only reads: `GetService<CommunicationManagement>()`, enumeration of `Connections`,
  `GetAttribute`, and the `LocalInterface`/`LocalTarget`/`PartnerTarget` links.
  `Connection.Delete`, `SetAttribute(s)` and `ConnectionComposition.Create` are forbidden
  (`ForbiddenApiTests`).

## Hardware item

```jsonc
{"name": "PROFINET-Schnittstelle X1", "path": "...", "interfaces": [...],
 "io_system": {"name": "PROFINET-IO-System (100)", "controller": "S7-1500/ET200MP-Station_1/PLC_1"}}
```

`io_system` is present only for items whose interface is connected to an IO system
(`NetworkInterface.IoConnectors[].ConnectedToIoSystem`); `controller` is the device item whose
interface has that system in `IoControllers[].IoSystem`.

Items with transfer areas (PN/PN coupler sides) also carry:

```jsonc
"transfer_areas": [                               // NetworkInterface.TransferAreas, by PositionNumber
  {"name": "Transferbereich_IN1", "type": "IN", "direction": "LocalToPartner", "position": 1,
   "local_to_partner_bytes": 0, "partner_to_local_bytes": 10,
   "controller_addresses": [{"io": "input", "start": 500, "bits": 80,
                             "controller": "S7-1500/ET200MP-Station_1/PLC_1"}]}
]
```

`controller_addresses` are the area's `PartnerAddresses` (start and length as Openness gives
them, length in bits); empty for a side connected to no IO system. `LocalAddresses` carry no
start address and are not dumped.
