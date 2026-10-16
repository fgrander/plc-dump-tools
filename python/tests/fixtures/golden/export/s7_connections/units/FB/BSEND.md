---
name: BSEND
kind: FB
number: 12
language: none
original_language: STL
protected: true
parse_quality: full
attributes:
  address: FB 12
path_prefix: '"BSEND"'
variable_scope: fb_interface
interface:
- {name: ID, type: WORD, section: IN}
- {name: R, type: BOOL, section: IN}
- {name: REQ, type: BOOL, section: IN}
- {name: R_ID, type: DWORD, section: IN}
- {name: DONE, type: BOOL, section: OUT}
- {name: ERROR, type: BOOL, section: OUT}
- {name: STATUS, type: WORD, section: OUT}
- {name: LEN, type: WORD, section: IN_OUT}
- {name: SD_1, type: ANY, section: IN_OUT}
---

# BSEND

## Interface
| Section | Name | Type | Start | Comment |
|---|---|---|---|---|
| IN | ID | WORD |  |  |
| IN | R | BOOL |  |  |
| IN | REQ | BOOL |  |  |
| IN | R_ID | DWORD |  |  |
| OUT | DONE | BOOL |  |  |
| OUT | ERROR | BOOL |  |  |
| OUT | STATUS | WORD |  |  |
| IN_OUT | LEN | WORD |  |  |
| IN_OUT | SD_1 | ANY |  |  |

> protected – logic not exported
