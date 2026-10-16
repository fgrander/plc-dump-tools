---
name: Ethernet_Comm
kind: FB
number: 3
language: stl
original_language: LAD
protected: false
parse_quality: full
attributes:
  address: FB 3
  version: '0.1'
path_prefix: '"Ethernet_Comm"'
variable_scope: fb_interface
interface:
- {name: ReadPLC3, type: FB13, section: STATIC}
- {name: WritePLC3, type: FB12, section: STATIC}
networks:
- {'no': 1, line_start: 30, line_end: 44}
- {'no': 2, line_start: 46, line_end: 59}
---

# Ethernet_Comm

## Interface
| Section | Name | Type | Start | Comment |
|---|---|---|---|---|
| STATIC | ReadPLC3 | FB13 |  |  |
| STATIC | WritePLC3 | FB12 |  |  |

## NW 1

```stl
      CALL  "BSEND" (
            REQ    := ,
            R      := ,
            ID     := -17477,
            R_ID   := L#1,
            DONE   := ,
            ERROR  := ,
            STATUS := ,
            SD_1   := P#DBX 0.0 BYTE 1,
            LEN    := )
      NOP   0
```

## NW 2

```stl
      CALL  "BRCV" (
            EN_R   := ,
            ID     := -21846,
            R_ID   := L#1,
            NDR    := ,
            ERROR  := ,
            STATUS := ,
            RD_1   := P#DBX 0.0 BYTE 1,
            LEN    := )
      NOP   0
```
