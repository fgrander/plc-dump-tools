# Index — PLC_1  (siemens-tia V21, 6ES7 517-3FP00-0AB0)
See README.md for how to read this export.

| Cat | Name | Path | Size | Title |
|---|---|---|---|---|
| OB | FOB_RTG1 | units/OB/FOB_RTG1.md | 227 |  |
| FB | Baustein_Graph | units/FB/Baustein_Graph.md | 40.3k |  |
| TAG_TABLE | Standard-Variablentabelle | units/TAG_TABLE/Standard-Variablentabelle.md | 233 |  |
| unit (SD) | Datenbaustein_1 | sd/Programmbausteine/Datenbaustein_1.s7dcl | 371 |  |
| unit (SD) | Main_Safety_RTG1 | sd/Programmbausteine/Main_Safety_RTG1.s7dcl | 300 |  |
| unit (SD) | Main_Safety_RTG1_DB | sd/Programmbausteine/Main_Safety_RTG1_DB.s7dcl | 224 |  |
| unit (SD) | Main | sd/Programmbausteine/Main.s7dcl | 1.2k |  |
| unit (SD) | send_rec | sd/PLC-Datentypen/send_rec.s7dcl | 150 |  |
| tags | Symbols (tags: 0) | symbols.json | 3 |  |
| io | Inputs and outputs | io.json | 36 |  |
| hw | Hardware (modules: 23) | hardware.json | 9.1k |  |
| xref | Cross-reference (entries: 0) | xref.json | 3 |  |
| safety | Safety (units: 2) | safety/safety.json | 125 |  |
| hmi | HMI (screens: 0, alarms: 0) | hmi/hmi.json | 71 |  |
| part | siemens-simatic-sd | parts/siemens-simatic-sd.json | 1.1k |  |
| struct | Structure | structure.json | 998 |  |
| conn | Connections (connections: 3, calls: 2, couplers: 3) | connections.json | 5.5k |  |
| platform | siemens-tia | platform/siemens-tia/platform.json | 403 |  |
| cov | Coverage | coverage.json | 1.5k |  |
| doc | README | README.md | 11.0k | How to read this export |
| meta | Manifest | manifest.json |  |  |

## Connections

| ID | Name | Local | Partner | Partner address | TSAP local / partner | Sets up | One-way | Used by |
|---|---|---|---|---|---|---|---|---|
| 100 | S7_Verbindung_1 | S7-1500/ET200MP-Station_1/PLC_1 | – | 192.168.1.50 | 14.01 / 15.02 | local | – | Main NW 1 (BSEND) |
| 101 | S7_Verbindung_2 | S7-1500/ET200MP-Station_1/PLC_1 | – | 192.168.1.70 | 10.01 / 11.01 | local | – | Main NW 2 (BRCV) |
| 102 | S7_Verbindung_3 | S7-1500/ET200MP-Station_1/PLC_1 | PLC_2 | 192.168.1.5 | SIMATIC-ACC10201 / SIMATIC-ACC11001 | partner | – | – |

Findings:

- connection_unused: S7-1500/ET200MP-Station_1/PLC_1/0x0102
- coupler_side_without_controller: PNPN Coupler/PNPN Coupler.X2
- coupler_side_without_controller: PNPN Coupler_1/PNPN Coupler_1.X2
- transfer_area_length_mismatch: PNPN Coupler_1/PNPN Coupler_1.X1

Couplers:

- GSD-Geraet_1/Slave_1 (dp_dp, 6ES7 158-0AD01-0XA0): %I10.0-%I25.7, %Q4.0-%Q7.7
- PNPN Coupler/PNPN Coupler.X1 (pn_pn, 6ES7 158-3AD01-0XA0): %I500.0-%I509.7, %I26.0-%I35.7, %Q8.0-%Q8.7, %Q9.0-%Q9.7, %I5.0-%I5.7, %I38.0-%I38.7, %Q10.0-%Q10.7
- PNPN Coupler_1/PNPN Coupler_1.X1 (pn_pn, 6ES7 158-3AD10-0XA0): %I36.0-%I37.7
