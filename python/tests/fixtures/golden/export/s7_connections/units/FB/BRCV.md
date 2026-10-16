---
name: BRCV
kind: FB
number: 13
language: none
original_language: STL
protected: true
parse_quality: full
attributes:
  address: FB 13
path_prefix: '"BRCV"'
variable_scope: fb_interface
interface:
- {name: EN_R, type: BOOL, section: IN}
- {name: ID, type: WORD, section: IN}
- {name: R_ID, type: DWORD, section: IN}
- {name: ERROR, type: BOOL, section: OUT}
- {name: NDR, type: BOOL, section: OUT}
- {name: STATUS, type: WORD, section: OUT}
- {name: LEN, type: WORD, section: IN_OUT}
- {name: RD_1, type: ANY, section: IN_OUT}
---

# BRCV

## Interface
| Section | Name | Type | Start | Comment |
|---|---|---|---|---|
| IN | EN_R | BOOL |  |  |
| IN | ID | WORD |  |  |
| IN | R_ID | DWORD |  |  |
| OUT | ERROR | BOOL |  |  |
| OUT | NDR | BOOL |  |  |
| OUT | STATUS | WORD |  |  |
| IN_OUT | LEN | WORD |  |  |
| IN_OUT | RD_1 | ANY |  |  |

> protected – logic not exported
