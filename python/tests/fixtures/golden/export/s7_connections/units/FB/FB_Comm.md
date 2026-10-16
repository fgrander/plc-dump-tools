---
name: FB_Comm
kind: FB
number: 40
language: stl
original_language: LAD
protected: false
parse_quality: full
attributes:
  address: FB 40
path_prefix: '"FB_Comm"'
variable_scope: fb_interface
interface:
- {name: Read, type: SFB14, section: STATIC}
- {name: Recv, type: FB13, section: STATIC}
- {name: Send, type: FB12, section: STATIC}
networks:
- {'no': 1, line_start: 32, line_end: 39, title: {de: Daten von PLC2 lesen}}
- {'no': 2, line_start: 41, line_end: 49, title: {de: Daten an PLC3 senden}}
- {'no': 3, line_start: 51, line_end: 59, title: {de: Daten aus dem Projekt empfangen}}
---

# FB_Comm

## Interface
| Section | Name | Type | Start | Comment |
|---|---|---|---|---|
| STATIC | Read | SFB14 |  |  |
| STATIC | Recv | FB13 |  |  |
| STATIC | Send | FB12 |  |  |

## NW 1 — Daten von PLC2 lesen

```stl
      CALL  #Read (
            ID     := W#16#1,
            ADDR_1 := P#DBX 0.0 BYTE 1,
            RD_1   :=  BYTE )
```

## NW 2 — Daten an PLC3 senden

```stl
      CALL  #Send (
            ID     := -21846,
            R_ID   := L#16,
            SD_1   := P#DBX 0.0 BYTE 1,
            LEN    := MW 10 )
```

## NW 3 — Daten aus dem Projekt empfangen

```stl
      CALL  #Recv (
            ID     := W#16#2,
            R_ID   := DW#16#1,
            RD_1   :=  BYTE ,
            LEN    := )
```
