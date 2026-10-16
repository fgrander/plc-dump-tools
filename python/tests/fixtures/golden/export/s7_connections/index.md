# Index — PRESS_1  (siemens-step7-classic, CPU 315-2 PN/DP)
See README.md for how to read this export.

| Cat | Name | Path | Size | Title |
|---|---|---|---|---|
| OB | Main | units/OB/Main.md | 943 | Hauptprogramm |
| FB | BRCV | units/FB/BRCV.md | 884 |  |
| FB | BSEND | units/FB/BSEND.md | 948 |  |
| FB | FB_Comm | units/FB/FB_Comm.md | 1.3k |  |
| FB | FB_Heating | units/FB/FB_Heating.md | 1.4k | Heizplattenregelung |
| FB | FB_Secret | units/FB/FB_Secret.md | 252 |  |
| FB | FB_Valve | units/FB/FB_Valve.md | 649 |  |
| FC | FC_Scale | units/FC/FC_Scale.md | 1.1k | Analogwert skalieren |
| DB | DB_Recipe | units/DB/DB_Recipe.md | 862 |  |
| IDB | DB_Heating | units/IDB/DB_Heating.md | 791 |  |
| TAG_TABLE | Symbols | units/TAG_TABLE/Symbols.md | 157 |  |
| OTHER | FB_Valve.scl | units/OTHER/FB_Valve.scl.md | 380 |  |
| OTHER | GET | units/OTHER/GET.md | 182 |  |
| OTHER | TON | units/OTHER/TON.md | 180 |  |
| OTHER | VAT1 | units/OTHER/VAT1.md | 195 | Beobachten Presse |
| UDT | UDT_Limits | datatypes/UDT_Limits.md | 439 |  |
| tags | Symbols (tags: 6) | symbols.json | 1.3k |  |
| io | Inputs and outputs | io.json | 828 |  |
| hw | Hardware (modules: 3) | hardware.json | 1.4k |  |
| xref | Cross-reference (entries: 26) | xref.json | 3.9k |  |
| safety | Safety (units: 0) | safety/safety.json | 72 |  |
| hmi | HMI (screens: 0, alarms: 0) | hmi/hmi.json | 71 |  |
| struct | Structure | structure.json | 223 |  |
| conn | Connections (connections: 6, calls: 3, couplers: 0) | connections.json | 6.1k |  |
| platform | siemens-step7-classic | platform/siemens-step7-classic/platform.json | 172 |  |
| cov | Coverage | coverage.json | 1.5k |  |
| doc | README | README.md | 8.7k | How to read this export |
| meta | Manifest | manifest.json |  |  |

## Connections

| ID | Name | Local | Partner | Partner address | TSAP local / partner | Sets up | One-way | Used by |
|---|---|---|---|---|---|---|---|---|
| 1 | S7-Verbindung 1 | SIMATIC 300(1)/CPU 315-2 PN/DP | HomePLC2 | 10.101.10.20 | 10.02 / 10.02 | local | yes | FB_Comm NW 1 (GET) |
| 2 | S7-Verbindung 3 | SIMATIC 300(1)/CPU 315-2 PN/DP | CP 343-1 | 10.1.2.20 | 12.02 / 03.04 | local | yes | FB_Comm NW 3 (BRCV) |
| 3 | ISO-on-TCP-Verbindung 1 | SIMATIC 300(1)/CPU 315-2 PN/DP | details not read | – | – | – | – | – |
| 4 | S7-Verbindung 4 | SIMATIC 300(1)/CPU 315-2 PN/DP | Unbekannt | 10.5.5.5 | 14.02 / 03.00 | local | yes | – |
| 10 | S7-Verbindung 2 | SIMATIC 300(1)/CPU 315-2 PN/DP | HomePLC3 | 10.102.10.20 | 11.02 / 10.04 | partner | yes | – |
| 5 | S7-Verbindung 5 | list 2 | Fremd | 10.9.9.9 | – / 10.02 | local | yes | – |

Calls without a configured connection:

- FB_Comm NW 2 (BSEND): ID AAAA, R_ID 10 (ID is not a configured connection; R_ID equals configured connection ID 10: ID and R_ID may be swapped)

Findings:

- connection_unused: SIMATIC 300(1)/CPU 315-2 PN/DP/0x0004
- connection_unused: SIMATIC 300(1)/CPU 315-2 PN/DP/0x0010
- tables_compiled_differ: SIMATIC 300(1)/CPU 315-2 PN/DP/0x0010 (partner_tsap: tables 10.03, compiled 10.04)
