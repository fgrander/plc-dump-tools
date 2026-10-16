---
name: Block_1_DB
kind: IDB
number: 7
language: none
protected: false
parse_quality: full
folder: Programmbausteine
attributes:
  route: simaticml
  version: '0.1'
path_prefix: '"Block_1_DB"'
variable_scope: db_member
interface:
- {name: PC_Flags, type: PC_Flags_V2, section: STATIC, retain: false, accessible: true, visible: true, writable: false, members: [{name: Crit_On, type: Bool, section: STATIC}, {name: Version, type: 'String[10]', section: STATIC}]}
- {name: State, type: SV_FB_State_V2, section: STATIC, retain: false, accessible: true, visible: true, writable: false, members: [{name: A, type: Bool, section: STATIC}, {name: All, type: Bool, section: STATIC}, {name: C1, type: Bool, section: STATIC}, {name: C2, type: Bool, section: STATIC}, {name: C3, type: Bool, section: STATIC}, {name: C4, type: Bool, section: STATIC}, {name: C5, type: Bool, section: STATIC}, {name: C6, type: Bool, section: STATIC}, {name: C7, type: Bool, section: STATIC}, {name: C8, type: Bool, section: STATIC}, {name: Categories, type: Byte, section: STATIC}, {name: I, type: Bool, section: STATIC}, {name: Merr, type: Bool, section: STATIC}, {name: Mtxt, type: Bool, section: STATIC}, {name: O, type: Bool, section: STATIC}, {name: P, type: Bool, section: STATIC}, {name: R, type: Bool, section: STATIC}, {name: Reserved, type: Byte, section: STATIC}, {name: SV_Types, type: Byte, section: STATIC}, {name: Sub_Cat_1, type: DWord, section: STATIC}, {name: Sub_Cat_2, type: DWord, section: STATIC}, {name: Total_Number, type: UInt, section: STATIC}]}
---

# Block_1_DB

## Interface
| Section | Name | Type | Start | Comment |
|---|---|---|---|---|
| STATIC | PC_Flags | PC_Flags_V2 |  |  |
| STATIC | PC_Flags.Crit_On | Bool |  |  |
| STATIC | PC_Flags.Version | String[10] |  |  |
| STATIC | State | SV_FB_State_V2 |  |  |
| STATIC | State.A | Bool |  |  |
| STATIC | State.All | Bool |  |  |
| STATIC | State.C1 | Bool |  |  |
| STATIC | State.C2 | Bool |  |  |
| STATIC | State.C3 | Bool |  |  |
| STATIC | State.C4 | Bool |  |  |
| STATIC | State.C5 | Bool |  |  |
| STATIC | State.C6 | Bool |  |  |
| STATIC | State.C7 | Bool |  |  |
| STATIC | State.C8 | Bool |  |  |
| STATIC | State.Categories | Byte |  |  |
| STATIC | State.I | Bool |  |  |
| STATIC | State.Merr | Bool |  |  |
| STATIC | State.Mtxt | Bool |  |  |
| STATIC | State.O | Bool |  |  |
| STATIC | State.P | Bool |  |  |
| STATIC | State.R | Bool |  |  |
| STATIC | State.Reserved | Byte |  |  |
| STATIC | State.SV_Types | Byte |  |  |
| STATIC | State.Sub_Cat_1 | DWord |  |  |
| STATIC | State.Sub_Cat_2 | DWord |  |  |
| STATIC | State.Total_Number | UInt |  |  |
