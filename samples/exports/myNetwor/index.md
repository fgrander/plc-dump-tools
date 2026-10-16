# Index — myNetworkDemo  (siemens-step7-classic, CPU 317F-2 PN/DP)
See README.md for how to read this export.

| Cat | Name | Path | Size | Title |
|---|---|---|---|---|
| OB | S7-Programm(2)/CYC_INT5 | units/OB/S7-Programm(2)_CYC_INT5.md | 3.1k | "Cyclic Interrupt" |
| OB | S7-Programm(2)/MAIN | units/OB/S7-Programm(2)_MAIN.md | 407 | "Main Program Sweep (Cycle)" |
| OB | S7-Programm(3)/OB1 | units/OB/S7-Programm(3)_OB1.md | 271 | "Main Program Sweep (Cycle)" |
| FB | S7-Programm(2)/BRCV | units/FB/S7-Programm(2)_BRCV.md | 15.9k |  |
| FB | S7-Programm(2)/BSEND | units/FB/S7-Programm(2)_BSEND.md | 15.8k |  |
| FB | S7-Programm(2)/Ethernet_Comm | units/FB/S7-Programm(2)_Ethernet_Comm.md | 1.8k |  |
| FC | S7-Programm(2)/SCALE | units/FC/S7-Programm(2)_SCALE.md | 2.3k | SCALING VALUES |
| FC | S7-Programm(2)/UNSCALE | units/FC/S7-Programm(2)_UNSCALE.md | 2.2k | UNSCALING VALUES |
| DB | S7-Programm(2)/DB_READ_PLC2 | units/DB/S7-Programm(2)_DB_READ_PLC2.md | 541 |  |
| DB | S7-Programm(2)/DB_READ_PLC3 | units/DB/S7-Programm(2)_DB_READ_PLC3.md | 541 |  |
| DB | S7-Programm(2)/DB_SEND_PLC2 | units/DB/S7-Programm(2)_DB_SEND_PLC2.md | 541 |  |
| DB | S7-Programm(2)/DB_SEND_PLC3 | units/DB/S7-Programm(2)_DB_SEND_PLC3.md | 541 |  |
| DB | S7-Programm(3)/ProcessValues | units/DB/S7-Programm(3)_ProcessValues.md | 780 |  |
| IDB | S7-Programm(2)/DB100 | units/IDB/S7-Programm(2)_DB100.md | 8.0k |  |
| IDB | S7-Programm(2)/DB101 | units/IDB/S7-Programm(2)_DB101.md | 5.7k |  |
| IDB | S7-Programm(2)/DB_COMM | units/IDB/S7-Programm(2)_DB_COMM.md | 765 |  |
| TAG_TABLE | S7-Programm(2)/Symbols | units/TAG_TABLE/S7-Programm(2)_Symbols.md | 225 |  |
| OTHER | S7-Programm(2)/CONT_C | units/OTHER/S7-Programm(2)_CONT_C.md | 276 |  |
| OTHER | S7-Programm(2)/CONT_S | units/OTHER/S7-Programm(2)_CONT_S.md | 276 |  |
| OTHER | S7-Programm(2)/GET | units/OTHER/S7-Programm(2)_GET.md | 270 |  |
| OTHER | S7-Programm(2)/SFB12 | units/OTHER/S7-Programm(2)_SFB12.md | 274 |  |
| OTHER | S7-Programm(2)/SFB13 | units/OTHER/S7-Programm(2)_SFB13.md | 274 |  |
| tags | Symbols (tags: 2) | symbols.json | 409 |  |
| io | Inputs and outputs | io.json | 422 |  |
| hw | Hardware (modules: 18) | hardware.json | 7.8k |  |
| xref | Cross-reference (entries: 12) | xref.json | 2.1k |  |
| safety | Safety (units: 0) | safety/safety.json | 72 |  |
| hmi | HMI (screens: 0, alarms: 0) | hmi/hmi.json | 71 |  |
| struct | Structure | structure.json | 1.4k |  |
| conn | Connections (connections: 4, calls: 3, couplers: 1) | connections.json | 6.4k |  |
| platform | siemens-step7-classic | platform/siemens-step7-classic/platform.json | 172 |  |
| cov | Coverage | coverage.json | 1.4k |  |
| doc | README | README.md | 8.7k | How to read this export |
| meta | Manifest | manifest.json |  |  |

## Connections

| ID | Name | Local | Partner | Partner address | TSAP local / partner | Sets up | One-way | Used by |
|---|---|---|---|---|---|---|---|---|
| 1 | S7-Verbindung 1 | SIMATIC 300-Station/CPU 317F-2 PN/DP | HomePLC2 | 10.101.10.20 | 10.02 / 10.02 | local | yes | S7-Programm(2)/Ethernet_Comm NW 1 (GET), S7-Programm(2)/Ethernet_Comm NW 3 (BRCV) |
| 10 | S7-Verbindung 2 | SIMATIC 300-Station/CPU 317F-2 PN/DP | HomePLC3 | 10.102.10.20 | 11.02 / 10.03 | partner | yes | S7-Programm(2)/Ethernet_Comm NW 2 (BSEND) |
| 12 | S7-Verbindung 2 | SIMATIC 300-Station/CPU 317F-2 PN/DP | unbekannt | 10.5.5.5 | 12.02 / 03.00 | local | yes | – |
| 1 | S7-Verbindung 1 | SIMATIC 400(1)/CPU 414-3 PN/DP | CP 343-1 PN | 10.60.10.2 | 10.02 / 03.02 | local | yes | – |

Findings:

- connection_unused: SIMATIC 300-Station/CPU 317F-2 PN/DP/0x0012
- connection_unused: SIMATIC 400(1)/CPU 414-3 PN/DP/0x0001

Couplers:

- SIMATIC 300-Station/PROFINET-IO-System #1 (pn_pn, 6ES7 158-3AD10-0XA0): %I2.0-%I13.7, %Q2.0-%Q7.7
