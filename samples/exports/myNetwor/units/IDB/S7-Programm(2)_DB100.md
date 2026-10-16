---
name: S7-Programm(2)/DB100
kind: IDB
number: 100
language: none
protected: false
parse_quality: full
folder: S7-Programm(2)
instance_of: FB41
attributes:
  address: DB 100
path_prefix: '"S7-Programm(2)/DB100"'
variable_scope: db_member
interface:
- {offset: '0.0', name: COM_RST, type: BOOL, section: IN, start: 'False', comment: {de: complete restart}}
- {offset: '0.1', name: MAN_ON, type: BOOL, section: IN, start: 'True', comment: {de: manual value on}}
- {offset: '0.2', name: PVPER_ON, type: BOOL, section: IN, start: 'False', comment: {de: process variable peripherie on}}
- {offset: '0.3', name: P_SEL, type: BOOL, section: IN, start: 'True', comment: {de: proportional action on}}
- {offset: '0.4', name: I_SEL, type: BOOL, section: IN, start: 'True', comment: {de: integral action on}}
- {offset: '0.5', name: INT_HOLD, type: BOOL, section: IN, start: 'False', comment: {de: integral action hold}}
- {offset: '0.6', name: I_ITL_ON, type: BOOL, section: IN, start: 'False', comment: {de: initialization of the integral action}}
- {offset: '0.7', name: D_SEL, type: BOOL, section: IN, start: 'False', comment: {de: derivative action on}}
- {offset: '2.0', name: CYCLE, type: TIME, section: IN, start: T#1S, comment: {de: sample time}}
- {offset: '6.0', name: SP_INT, type: REAL, section: IN, start: '0.000000e+000', comment: {de: internal setpoint}}
- {offset: '10.0', name: PV_IN, type: REAL, section: IN, start: '0.000000e+000', comment: {de: process variable in}}
- {offset: '14.0', name: PV_PER, type: WORD, section: IN, start: W#16#0, comment: {de: process variable peripherie}}
- {offset: '16.0', name: MAN, type: REAL, section: IN, start: '0.000000e+000', comment: {de: manual value}}
- {offset: '20.0', name: GAIN, type: REAL, section: IN, start: '2.000000e+006', comment: {de: proportional gain}}
- {offset: '24.0', name: TI, type: TIME, section: IN, start: T#20S, comment: {de: reset time}}
- {offset: '28.0', name: TD, type: TIME, section: IN, start: T#10S, comment: {de: derivative time}}
- {offset: '32.0', name: TM_LAG, type: TIME, section: IN, start: T#2S, comment: {de: time lag of the derivative action}}
- {offset: '36.0', name: DEADB_W, type: REAL, section: IN, start: '0.000000e+000', comment: {de: dead band width}}
- {offset: '40.0', name: LMN_HLM, type: REAL, section: IN, start: '1.000000e+008', comment: {de: manipulated value high limit}}
- {offset: '44.0', name: LMN_LLM, type: REAL, section: IN, start: '0.000000e+000', comment: {de: manipulated value low limit}}
- {offset: '48.0', name: PV_FAC, type: REAL, section: IN, start: '1.000000e+006', comment: {de: process variable factor}}
- {offset: '52.0', name: PV_OFF, type: REAL, section: IN, start: '0.000000e+000', comment: {de: process variable offset}}
- {offset: '56.0', name: LMN_FAC, type: REAL, section: IN, start: '1.000000e+006', comment: {de: manipulated value factor}}
- {offset: '60.0', name: LMN_OFF, type: REAL, section: IN, start: '0.000000e+000', comment: {de: manipulated value offset}}
- {offset: '64.0', name: I_ITLVAL, type: REAL, section: IN, start: '0.000000e+000', comment: {de: initialization value of the integral action}}
- {offset: '68.0', name: DISV, type: REAL, section: IN, start: '0.000000e+000', comment: {de: disturbance variable}}
- {offset: '72.0', name: LMN, type: REAL, section: OUT, start: '0.000000e+000', comment: {de: manipulated value}}
- {offset: '76.0', name: LMN_PER, type: WORD, section: OUT, start: W#16#0, comment: {de: manipulated value peripherie}}
- {offset: '78.0', name: QLMN_HLM, type: BOOL, section: OUT, start: 'False', comment: {de: high limit of manipulated value reached}}
- {offset: '78.1', name: QLMN_LLM, type: BOOL, section: OUT, start: 'False', comment: {de: low limit of manipulated value reached}}
- {offset: '80.0', name: LMN_P, type: REAL, section: OUT, start: '0.000000e+000', comment: {de: proportionality component}}
- {offset: '84.0', name: LMN_I, type: REAL, section: OUT, start: '0.000000e+000', comment: {de: integral component}}
- {offset: '88.0', name: LMN_D, type: REAL, section: OUT, start: '0.000000e+000', comment: {de: derivative component}}
- {offset: '92.0', name: PV, type: REAL, section: OUT, start: '0.000000e+000', comment: {de: process variable}}
- {offset: '96.0', name: ER, type: REAL, section: OUT, start: '0.000000e+000', comment: {de: error signal}}
- {offset: '100.0', name: sInvAlt, type: REAL, section: STATIC, start: '0.000000e+000'}
- {offset: '104.0', name: sIanteilAlt, type: REAL, section: STATIC, start: '0.000000e+000'}
- {offset: '108.0', name: sRestInt, type: REAL, section: STATIC, start: '0.000000e+000'}
- {offset: '112.0', name: sRestDif, type: REAL, section: STATIC, start: '0.000000e+000'}
- {offset: '116.0', name: sRueck, type: REAL, section: STATIC, start: '0.000000e+000'}
- {offset: '120.0', name: sLmn, type: REAL, section: STATIC, start: '0.000000e+000'}
- {offset: '124.0', name: sbArwHLmOn, type: BOOL, section: STATIC, start: 'False'}
- {offset: '124.1', name: sbArwLLmOn, type: BOOL, section: STATIC, start: 'False'}
- {offset: '124.2', name: sbILimOn, type: BOOL, section: STATIC, start: 'True'}
---

# S7-Programm(2)/DB100

Instance of `FB41`.

## Interface
| Offset | Section | Name | Type | Start | Comment |
|---|---|---|---|---|---|
| 0.0 | IN | COM_RST | BOOL | False | de: complete restart |
| 0.1 | IN | MAN_ON | BOOL | True | de: manual value on |
| 0.2 | IN | PVPER_ON | BOOL | False | de: process variable peripherie on |
| 0.3 | IN | P_SEL | BOOL | True | de: proportional action on |
| 0.4 | IN | I_SEL | BOOL | True | de: integral action on |
| 0.5 | IN | INT_HOLD | BOOL | False | de: integral action hold |
| 0.6 | IN | I_ITL_ON | BOOL | False | de: initialization of the integral action |
| 0.7 | IN | D_SEL | BOOL | False | de: derivative action on |
| 2.0 | IN | CYCLE | TIME | T#1S | de: sample time |
| 6.0 | IN | SP_INT | REAL | 0.000000e+000 | de: internal setpoint |
| 10.0 | IN | PV_IN | REAL | 0.000000e+000 | de: process variable in |
| 14.0 | IN | PV_PER | WORD | W#16#0 | de: process variable peripherie |
| 16.0 | IN | MAN | REAL | 0.000000e+000 | de: manual value |
| 20.0 | IN | GAIN | REAL | 2.000000e+006 | de: proportional gain |
| 24.0 | IN | TI | TIME | T#20S | de: reset time |
| 28.0 | IN | TD | TIME | T#10S | de: derivative time |
| 32.0 | IN | TM_LAG | TIME | T#2S | de: time lag of the derivative action |
| 36.0 | IN | DEADB_W | REAL | 0.000000e+000 | de: dead band width |
| 40.0 | IN | LMN_HLM | REAL | 1.000000e+008 | de: manipulated value high limit |
| 44.0 | IN | LMN_LLM | REAL | 0.000000e+000 | de: manipulated value low limit |
| 48.0 | IN | PV_FAC | REAL | 1.000000e+006 | de: process variable factor |
| 52.0 | IN | PV_OFF | REAL | 0.000000e+000 | de: process variable offset |
| 56.0 | IN | LMN_FAC | REAL | 1.000000e+006 | de: manipulated value factor |
| 60.0 | IN | LMN_OFF | REAL | 0.000000e+000 | de: manipulated value offset |
| 64.0 | IN | I_ITLVAL | REAL | 0.000000e+000 | de: initialization value of the integral action |
| 68.0 | IN | DISV | REAL | 0.000000e+000 | de: disturbance variable |
| 72.0 | OUT | LMN | REAL | 0.000000e+000 | de: manipulated value |
| 76.0 | OUT | LMN_PER | WORD | W#16#0 | de: manipulated value peripherie |
| 78.0 | OUT | QLMN_HLM | BOOL | False | de: high limit of manipulated value reached |
| 78.1 | OUT | QLMN_LLM | BOOL | False | de: low limit of manipulated value reached |
| 80.0 | OUT | LMN_P | REAL | 0.000000e+000 | de: proportionality component |
| 84.0 | OUT | LMN_I | REAL | 0.000000e+000 | de: integral component |
| 88.0 | OUT | LMN_D | REAL | 0.000000e+000 | de: derivative component |
| 92.0 | OUT | PV | REAL | 0.000000e+000 | de: process variable |
| 96.0 | OUT | ER | REAL | 0.000000e+000 | de: error signal |
| 100.0 | STATIC | sInvAlt | REAL | 0.000000e+000 |  |
| 104.0 | STATIC | sIanteilAlt | REAL | 0.000000e+000 |  |
| 108.0 | STATIC | sRestInt | REAL | 0.000000e+000 |  |
| 112.0 | STATIC | sRestDif | REAL | 0.000000e+000 |  |
| 116.0 | STATIC | sRueck | REAL | 0.000000e+000 |  |
| 120.0 | STATIC | sLmn | REAL | 0.000000e+000 |  |
| 124.0 | STATIC | sbArwHLmOn | BOOL | False |  |
| 124.1 | STATIC | sbArwLLmOn | BOOL | False |  |
| 124.2 | STATIC | sbILimOn | BOOL | True |  |
