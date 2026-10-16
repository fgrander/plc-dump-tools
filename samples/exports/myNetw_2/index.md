# Index — myNetworkDemo3  (siemens-step7-classic, CPU 416-3 PN/DP)
See README.md for how to read this export.

| Cat | Name | Path | Size | Title |
|---|---|---|---|---|
| OB | MAIN | units/OB/MAIN.md | 354 | "Main Program Sweep (Cycle)" |
| FB | BRCV | units/FB/BRCV.md | 15.8k |  |
| FB | BSEND | units/FB/BSEND.md | 15.7k |  |
| FB | Ethernet_Comm | units/FB/Ethernet_Comm.md | 1.1k |  |
| DB | DB_READ_PLC1 | units/DB/DB_READ_PLC1.md | 473 |  |
| DB | DB_SEND_PLC1 | units/DB/DB_SEND_PLC1.md | 473 |  |
| IDB | DB_COMM | units/IDB/DB_COMM.md | 559 |  |
| OTHER | GET | units/OTHER/GET.md | 217 |  |
| OTHER | SFB12 | units/OTHER/SFB12.md | 221 |  |
| OTHER | SFB13 | units/OTHER/SFB13.md | 221 |  |
| tags | Symbols (tags: 0) | symbols.json | 3 |  |
| io | Inputs and outputs | io.json | 36 |  |
| hw | Hardware (modules: 2) | hardware.json | 948 |  |
| xref | Cross-reference (entries: 4) | xref.json | 606 |  |
| safety | Safety (units: 0) | safety/safety.json | 72 |  |
| hmi | HMI (screens: 0, alarms: 0) | hmi/hmi.json | 71 |  |
| struct | Structure | structure.json | 223 |  |
| conn | Connections (connections: 1, calls: 2, couplers: 0) | connections.json | 2.4k |  |
| platform | siemens-step7-classic | platform/siemens-step7-classic/platform.json | 172 |  |
| cov | Coverage | coverage.json | 961 |  |
| doc | README | README.md | 8.7k | How to read this export |
| meta | Manifest | manifest.json |  |  |

## Connections

| ID | Name | Local | Partner | Partner address | TSAP local / partner | Sets up | One-way | Used by |
|---|---|---|---|---|---|---|---|---|
| 1 | S7-Verbindung 1 | SIMATIC 400(1)/CPU 416-3 PN/DP | HomePLC1 | 10.100.10.20 | 10.03 / 11.02 | local | yes | – |

Calls without a configured connection:

- Ethernet_Comm NW 1 (BSEND): ID BBBB, R_ID 1 (ID is not a configured connection; R_ID equals configured connection ID 1: ID and R_ID may be swapped)
- Ethernet_Comm NW 2 (BRCV): ID AAAA, R_ID 1 (ID is not a configured connection; R_ID equals configured connection ID 1: ID and R_ID may be swapped)

Findings:

- connection_unused: SIMATIC 400(1)/CPU 416-3 PN/DP/0x0001
