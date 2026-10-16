---
name: S7-Programm(2)/Ethernet_Comm
kind: FB
number: 3
language: stl
original_language: LAD
protected: false
parse_quality: full
folder: S7-Programm(2)
attributes:
  address: FB 3
  version: '0.1'
path_prefix: '"S7-Programm(2)/Ethernet_Comm"'
variable_scope: fb_interface
interface:
- {name: ReadPLC2, type: SFB14, section: STATIC}
- {name: ReadPLC3, type: FB13, section: STATIC}
- {name: WritePLC3, type: FB12, section: STATIC}
networks:
- {'no': 1, line_start: 34, line_end: 52}
- {'no': 2, line_start: 54, line_end: 68}
- {'no': 3, line_start: 70, line_end: 83}
---

# S7-Programm(2)/Ethernet_Comm

## Interface
| Section | Name | Type | Start | Comment |
|---|---|---|---|---|
| STATIC | ReadPLC2 | SFB14 |  |  |
| STATIC | ReadPLC3 | FB13 |  |  |
| STATIC | WritePLC3 | FB12 |  |  |

## NW 1

```stl
      CALL  "GET" (
            REQ    := ,
            ID     := 1,
            NDR    := ,
            ERROR  := ,
            STATUS := ,
            ADDR_1 := P#DBX 0.0 BYTE 1,
            ADDR_2 :=  BYTE ,
            ADDR_3 :=  BYTE ,
            ADDR_4 :=  BYTE ,
            RD_1   := P#DBX 0.0 BYTE 1,
            RD_2   :=  BYTE ,
            RD_3   :=  BYTE ,
            RD_4   :=  BYTE )
      NOP   0
```

## NW 2

```stl
      CALL  "BSEND" (
            REQ    := ,
            R      := ,
            ID     := 16,
            R_ID   := L#43690,
            DONE   := ,
            ERROR  := ,
            STATUS := ,
            SD_1   := P#DBX 0.0 BYTE 1,
            LEN    := )
      NOP   0
```

## NW 3

```stl
      CALL  "BRCV" (
            EN_R   := ,
            ID     := 1,
            R_ID   := L#48059,
            NDR    := ,
            ERROR  := ,
            STATUS := ,
            RD_1   := P#DBX 0.0 BYTE 1,
            LEN    := )
      NOP   0
```
