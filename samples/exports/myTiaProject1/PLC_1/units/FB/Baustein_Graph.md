---
name: Baustein_Graph
kind: FB
number: 2
language: ntn
original_language: GRAPH
protected: false
parse_quality: full
folder: Programmbausteine
attributes:
  route: simaticml
  version: '0.1'
path_prefix: '"Baustein_Graph"'
variable_scope: fb_interface
interface:
- {name: ACK_EF, type: Bool, section: IN, start: 'false', retain: false, comment: {de-DE: Alle Fehler und Störungen quittieren}, accessible: false, visible: false, writable: false}
- {name: INIT_SQ, type: Bool, section: IN, start: 'false', retain: false, comment: {de-DE: Kette in Initialzustand versetzen}, accessible: false, visible: false, writable: false}
- {name: OFF_SQ, type: Bool, section: IN, start: 'false', retain: false, comment: {de-DE: Kette ausschalten}, accessible: false, visible: false, writable: false}
- {name: SW_AUTO, type: Bool, section: IN, start: 'false', retain: false, comment: {de-DE: Automatischer Betrieb}, accessible: false, visible: false, writable: false}
- {name: SW_MAN, type: Bool, section: IN, start: 'false', retain: false, comment: {de-DE: Handbetrieb}, accessible: false, visible: false, writable: false}
- {name: SW_TAP, type: Bool, section: IN, start: 'false', retain: false, comment: {de-DE: Halbautomatisch/Weiterschalten mit Transition}, accessible: false, visible: false, writable: false}
- {name: SW_TOP, type: Bool, section: IN, start: 'false', retain: false, comment: {de-DE: Halbautomatisch/Ignoriere Transition}, accessible: false, visible: false, writable: false}
- {name: S_NEXT, type: Bool, section: IN, start: 'false', retain: false, comment: {de-DE: Nächsten Schritt am Parameter S_NO anzeigen}, accessible: false, visible: false, writable: false}
- {name: S_OFF, type: Bool, section: IN, start: 'false', retain: false, comment: {de-DE: 'Schritt deaktivieren, der an Parameter S_NO anliegt'}, accessible: false, visible: false, writable: false}
- {name: S_ON, type: Bool, section: IN, start: 'false', retain: false, comment: {de-DE: 'Schritt aktivieren, der an Parameter S_NO anliegt'}, accessible: false, visible: false, writable: false}
- {name: S_PREV, type: Bool, section: IN, start: 'false', retain: false, comment: {de-DE: Vorherigen Schritt am Parameter S_NO ausgeben}, accessible: false, visible: false, writable: false}
- {name: S_SEL, type: Int, section: IN, start: '0', retain: false, comment: {de-DE: 'Schritt auswählen, der an S_NO ausgegeben werden soll'}, accessible: false, visible: false, writable: false}
- {name: T_PUSH, type: Bool, section: IN, start: 'false', retain: false, comment: {de-DE: Schaltfreigabe für Transition im halbautomatischen Betrieb}, accessible: false, visible: false, writable: false}
- {name: AUTO_ON, type: Bool, section: OUT, start: 'false', retain: false, comment: {de-DE: Automatischer Betrieb eingeschaltet}, accessible: false, visible: false, writable: false}
- {name: ERR_FLT, type: Bool, section: OUT, start: 'false', retain: false, comment: {de-DE: Sammelfehler Interlock oder Supervision}, accessible: false, visible: false, writable: false}
- {name: MAN_ON, type: Bool, section: OUT, start: 'false', retain: false, comment: {de-DE: Handbetrieb eingeschaltet}, accessible: false, visible: false, writable: false}
- {name: S_ACTIVE, type: Bool, section: OUT, start: 'false', retain: false, comment: {de-DE: 'Schritt, der an Parameter S_NO angezeigt wird, ist aktiv'}, accessible: false, visible: false, writable: false}
- {name: S_MORE, type: Bool, section: OUT, start: 'false', retain: false, comment: {de-DE: Weitere Schritte sind vorhanden und können in S_NO angezeigt werden.}, accessible: false, visible: false, writable: false}
- {name: S_NO, type: Int, section: OUT, start: '0', retain: false, comment: {de-DE: Schrittnummer}, accessible: false, visible: false, writable: false}
- {name: TAP_ON, type: Bool, section: OUT, start: 'false', retain: false, comment: {de-DE: Halbautomatischer Betrieb/Schritt mit Transition eingeschaltet}, accessible: false, visible: false, writable: false}
- {name: TOP_ON, type: Bool, section: OUT, start: 'false', retain: false, comment: {de-DE: Halbautomatischer Betrieb/Ignoriere Transition eingeschaltet}, accessible: false, visible: false, writable: false}
- {name: RT_DATA, type: G7_RTDataPlus_V6, section: STATIC, retain: false, comment: {de-DE: Interner Datenbereich}, accessible: false, visible: false, writable: false, members: [{name: AS_MSG, type: Byte, section: STATIC, start: 16#65}, {name: EXEC_BITS, type: 'Array[0..249] of Bool', section: STATIC}, {name: GC_FLAGS, type: G7_GCFlagsPlus_V6, section: STATIC, members: [{name: ACK_REQ, type: Bool, section: STATIC, start: 'true'}, {name: COND_ED, type: USInt, section: STATIC, start: 16#E3}, {name: CRIT_ON, type: Bool, section: STATIC}, {name: ILP_MAN, type: Bool, section: STATIC}, {name: IL_CAT, type: USInt, section: STATIC, start: '1'}, {name: IL_SUBCAT_1, type: USInt, section: STATIC}, {name: IL_SUBCAT_2, type: USInt, section: STATIC}, {name: REACT_CAT, type: USInt, section: STATIC, start: '1'}, {name: REACT_SUBCAT_1, type: USInt, section: STATIC}, {name: REACT_SUBCAT_2, type: USInt, section: STATIC}, {name: SET_ENO, type: Bool, section: STATIC}, {name: SSKIP_ON, type: Bool, section: STATIC}, {name: SWM_LOCKED, type: Bool, section: STATIC}, {name: WARN_CAT, type: USInt, section: STATIC, start: '2'}, {name: WARN_SUBCAT_1, type: USInt, section: STATIC}, {name: WARN_SUBCAT_2, type: USInt, section: STATIC}]}, {name: LOCK_CNT, type: USInt, section: STATIC}, {name: MAX_SACT, type: USInt, section: STATIC, start: '1'}, {name: MAX_TVAL, type: USInt, section: STATIC, start: '3'}, {name: MOP, type: G7_MOPPlus_V6, section: STATIC, members: [{name: ACK, type: Bool, section: STATIC}, {name: ACKREQ, type: Bool, section: STATIC, start: 'true'}, {name: ACK_S, type: Bool, section: STATIC}, {name: AUTO, type: Bool, section: STATIC, start: 'true'}, {name: HALT, type: Bool, section: STATIC}, {name: ILP_MAN, type: Bool, section: STATIC}, {name: IL_PERM, type: Bool, section: STATIC}, {name: INIT, type: Bool, section: STATIC, start: 'true'}, {name: LMODE, type: Bool, section: STATIC}, {name: LOCK, type: Bool, section: STATIC, start: 'true'}, {name: MAN, type: Bool, section: STATIC}, {name: 'OFF', type: Bool, section: STATIC}, {name: OPS_ZERO, type: Bool, section: STATIC}, {name: REG, type: Bool, section: STATIC}, {name: REG_S, type: Bool, section: STATIC}, {name: RESET_CRIT, type: Bool, section: STATIC}, {name: SACT_DISP, type: Bool, section: STATIC, start: 'true'}, {name: SALL_DISP, type: Bool, section: STATIC}, {name: SEF_DISP, type: Bool, section: STATIC}, {name: SSKIP, type: Bool, section: STATIC}, {name: SUP, type: Bool, section: STATIC, start: 'true'}, {name: S_NEXT, type: Bool, section: STATIC}, {name: S_OFF, type: Bool, section: STATIC}, {name: S_ON, type: Bool, section: STATIC}, {name: S_PREV, type: Bool, section: STATIC}, {name: S_SELOK, type: Bool, section: STATIC}, {name: TAP, type: Bool, section: STATIC}, {name: TMS_HALT, type: Bool, section: STATIC}, {name: TOP, type: Bool, section: STATIC}, {name: T_NEXT, type: Bool, section: STATIC}, {name: T_PERM, type: Bool, section: STATIC}, {name: T_PREV, type: Bool, section: STATIC}, {name: T_PUSH, type: Bool, section: STATIC}]}, {name: MOP_EDGE, type: G7_MOPPlus_V6, section: STATIC, members: [{name: ACK, type: Bool, section: STATIC}, {name: ACKREQ, type: Bool, section: STATIC}, {name: ACK_S, type: Bool, section: STATIC}, {name: AUTO, type: Bool, section: STATIC}, {name: HALT, type: Bool, section: STATIC}, {name: ILP_MAN, type: Bool, section: STATIC}, {name: IL_PERM, type: Bool, section: STATIC}, {name: INIT, type: Bool, section: STATIC}, {name: LMODE, type: Bool, section: STATIC}, {name: LOCK, type: Bool, section: STATIC}, {name: MAN, type: Bool, section: STATIC}, {name: 'OFF', type: Bool, section: STATIC}, {name: OPS_ZERO, type: Bool, section: STATIC}, {name: REG, type: Bool, section: STATIC}, {name: REG_S, type: Bool, section: STATIC}, {name: RESET_CRIT, type: Bool, section: STATIC}, {name: SACT_DISP, type: Bool, section: STATIC}, {name: SALL_DISP, type: Bool, section: STATIC}, {name: SEF_DISP, type: Bool, section: STATIC}, {name: SSKIP, type: Bool, section: STATIC}, {name: SUP, type: Bool, section: STATIC}, {name: S_NEXT, type: Bool, section: STATIC}, {name: S_OFF, type: Bool, section: STATIC}, {name: S_ON, type: Bool, section: STATIC}, {name: S_PREV, type: Bool, section: STATIC}, {name: S_SELOK, type: Bool, section: STATIC}, {name: TAP, type: Bool, section: STATIC}, {name: TMS_HALT, type: Bool, section: STATIC}, {name: TOP, type: Bool, section: STATIC}, {name: T_NEXT, type: Bool, section: STATIC}, {name: T_PERM, type: Bool, section: STATIC}, {name: T_PREV, type: Bool, section: STATIC}, {name: T_PUSH, type: Bool, section: STATIC}]}, {name: OFFSETS, type: G7_OffsetsPlus_V6, section: STATIC, members: [{name: ASSB_OFFSET, type: UInt, section: STATIC, start: '43'}, {name: ASSJ_OFFSET, type: UInt, section: STATIC, start: '37'}, {name: ATAB_OFFSET, type: UInt, section: STATIC, start: '16'}, {name: ATAJ_OFFSET, type: UInt, section: STATIC, start: '9'}, {name: LSTT_OFFSET, type: UInt, section: STATIC, start: '2'}, {name: NSTT_OFFSET, type: UInt, section: STATIC, start: '30'}, {name: NTTS_OFFSET, type: UInt, section: STATIC, start: '55'}, {name: PSTT_OFFSET, type: UInt, section: STATIC, start: '23'}, {name: PTTS_OFFSET, type: UInt, section: STATIC, start: '49'}, {name: S00X_OFFSET, type: UInt, section: STATIC, start: '79'}, {name: S0X_OFFSET, type: UInt, section: STATIC, start: '101'}, {name: S1X_OFFSET, type: UInt, section: STATIC, start: '108'}, {name: SAX_OFFSET, type: UInt, section: STATIC, start: '85'}, {name: SERRX_OFFSET, type: UInt, section: STATIC, start: '87'}, {name: SINI_OFFSET, type: UInt, section: STATIC}, {name: SMX_OFFSET, type: UInt, section: STATIC, start: '94'}, {name: SOFFX_OFFSET, type: UInt, section: STATIC, start: '81'}, {name: SONX_OFFSET, type: UInt, section: STATIC, start: '83'}, {name: SWITCH_OFFSET, type: UInt, section: STATIC, start: '67'}, {name: SW_SQTS_OFFSET, type: UInt, section: STATIC, start: '61'}, {name: TSX_OFFSET, type: UInt, section: STATIC, start: '77'}, {name: TTX_OFFSET, type: UInt, section: STATIC, start: '73'}, {name: TVX_OFFSET, type: UInt, section: STATIC, start: '69'}]}, {name: POST_CNT, type: USInt, section: STATIC, start: '1'}, {name: PRE_CNT, type: USInt, section: STATIC, start: '1'}, {name: SQ_CNT, type: USInt, section: STATIC, start: '1'}, {name: SQ_FLAGS, type: G7_SQFlagsPlus_V6, section: STATIC, members: [{name: AS_MSG, type: Bool, section: STATIC, start: 'true'}, {name: CYC_OP, type: Bool, section: STATIC}, {name: ERROR, type: Bool, section: STATIC}, {name: ERR_FLT, type: Bool, section: STATIC}, {name: FAULT, type: Bool, section: STATIC}, {name: NF_OFL, type: Bool, section: STATIC}, {name: NO_SNO, type: Bool, section: STATIC}, {name: NO_SWI, type: Bool, section: STATIC}, {name: RT_FAIL, type: Bool, section: STATIC}, {name: SA_BUSY, type: Bool, section: STATIC}, {name: SA_OFL, type: Bool, section: STATIC}, {name: SQ_BUSY, type: Bool, section: STATIC}, {name: TV_OFL, type: Bool, section: STATIC}]}, {name: SQ_PART_CNT, type: USInt, section: STATIC, start: '4'}, {name: SUP_CNT, type: USInt, section: STATIC}, {name: S_CNT, type: USInt, section: STATIC, start: '6'}, {name: S_DISPIDX, type: USInt, section: STATIC, start: '255'}, {name: S_DISPLAY, type: Int, section: STATIC}, {name: S_SEL_OLD, type: Int, section: STATIC}, {name: THRESHOLD_SUP, type: USInt, section: STATIC}, {name: THRESHOLD_WARN, type: USInt, section: STATIC}, {name: TIME_DELTA, type: Time, section: STATIC}, {name: T_CNT, type: USInt, section: STATIC, start: '7'}, {name: T_DISPIDX, type: USInt, section: STATIC, start: '255'}, {name: VERSION, type: 'String[10]', section: STATIC, start: '''V6.0'''}]}
- {name: Step1, type: G7_StepPlus_V6, section: STATIC, retain: false, comment: {de-DE: Schrittstruktur}, accessible: false, visible: false, writable: false, members: [{name: A1, type: Bool, section: STATIC}, {name: AA, type: Bool, section: STATIC}, {name: CRIT_LOC, type: DWord, section: STATIC}, {name: CRIT_LOC_ERR, type: DWord, section: STATIC}, {name: H_IL_ERR, type: Byte, section: STATIC}, {name: H_SV_FLT, type: Byte, section: STATIC, start: 16#04}, {name: L0, type: Bool, section: STATIC}, {name: L1, type: Bool, section: STATIC}, {name: LA, type: Bool, section: STATIC}, {name: LS, type: Bool, section: STATIC}, {name: R1, type: Bool, section: STATIC}, {name: RA, type: Bool, section: STATIC}, {name: S0, type: Bool, section: STATIC}, {name: S1, type: Bool, section: STATIC}, {name: SM, type: Bool, section: STATIC}, {name: SNO, type: Int, section: STATIC, start: '1'}, {name: SS, type: Bool, section: STATIC}, {name: T, type: Time, section: STATIC}, {name: T_MAX, type: Time, section: STATIC, start: T#10S}, {name: T_WARN, type: Time, section: STATIC, start: T#7S}, {name: U, type: Time, section: STATIC}, {name: V0, type: Bool, section: STATIC}, {name: V1, type: Bool, section: STATIC}, {name: VA, type: Bool, section: STATIC}, {name: VS, type: Bool, section: STATIC}, {name: X, type: Bool, section: STATIC}]}
- {name: Step2, type: G7_StepPlus_V6, section: STATIC, retain: false, comment: {de-DE: Schrittstruktur}, accessible: false, visible: false, writable: false, members: [{name: A1, type: Bool, section: STATIC}, {name: AA, type: Bool, section: STATIC}, {name: CRIT_LOC, type: DWord, section: STATIC}, {name: CRIT_LOC_ERR, type: DWord, section: STATIC}, {name: H_IL_ERR, type: Byte, section: STATIC}, {name: H_SV_FLT, type: Byte, section: STATIC, start: 16#04}, {name: L0, type: Bool, section: STATIC}, {name: L1, type: Bool, section: STATIC}, {name: LA, type: Bool, section: STATIC}, {name: LS, type: Bool, section: STATIC}, {name: R1, type: Bool, section: STATIC}, {name: RA, type: Bool, section: STATIC}, {name: S0, type: Bool, section: STATIC}, {name: S1, type: Bool, section: STATIC}, {name: SM, type: Bool, section: STATIC}, {name: SNO, type: Int, section: STATIC, start: '2'}, {name: SS, type: Bool, section: STATIC}, {name: T, type: Time, section: STATIC}, {name: T_MAX, type: Time, section: STATIC, start: T#10S}, {name: T_WARN, type: Time, section: STATIC, start: T#7S}, {name: U, type: Time, section: STATIC}, {name: V0, type: Bool, section: STATIC}, {name: V1, type: Bool, section: STATIC}, {name: VA, type: Bool, section: STATIC}, {name: VS, type: Bool, section: STATIC}, {name: X, type: Bool, section: STATIC}]}
- {name: Step3, type: G7_StepPlus_V6, section: STATIC, retain: false, comment: {de-DE: Schrittstruktur}, accessible: false, visible: false, writable: false, members: [{name: A1, type: Bool, section: STATIC}, {name: AA, type: Bool, section: STATIC}, {name: CRIT_LOC, type: DWord, section: STATIC}, {name: CRIT_LOC_ERR, type: DWord, section: STATIC}, {name: H_IL_ERR, type: Byte, section: STATIC}, {name: H_SV_FLT, type: Byte, section: STATIC, start: 16#04}, {name: L0, type: Bool, section: STATIC}, {name: L1, type: Bool, section: STATIC}, {name: LA, type: Bool, section: STATIC}, {name: LS, type: Bool, section: STATIC}, {name: R1, type: Bool, section: STATIC}, {name: RA, type: Bool, section: STATIC}, {name: S0, type: Bool, section: STATIC}, {name: S1, type: Bool, section: STATIC}, {name: SM, type: Bool, section: STATIC}, {name: SNO, type: Int, section: STATIC, start: '3'}, {name: SS, type: Bool, section: STATIC}, {name: T, type: Time, section: STATIC}, {name: T_MAX, type: Time, section: STATIC, start: T#10S}, {name: T_WARN, type: Time, section: STATIC, start: T#7S}, {name: U, type: Time, section: STATIC}, {name: V0, type: Bool, section: STATIC}, {name: V1, type: Bool, section: STATIC}, {name: VA, type: Bool, section: STATIC}, {name: VS, type: Bool, section: STATIC}, {name: X, type: Bool, section: STATIC}]}
- {name: Step4, type: G7_StepPlus_V6, section: STATIC, retain: false, comment: {de-DE: Schrittstruktur}, accessible: false, visible: false, writable: false, members: [{name: A1, type: Bool, section: STATIC}, {name: AA, type: Bool, section: STATIC}, {name: CRIT_LOC, type: DWord, section: STATIC}, {name: CRIT_LOC_ERR, type: DWord, section: STATIC}, {name: H_IL_ERR, type: Byte, section: STATIC}, {name: H_SV_FLT, type: Byte, section: STATIC, start: 16#04}, {name: L0, type: Bool, section: STATIC}, {name: L1, type: Bool, section: STATIC}, {name: LA, type: Bool, section: STATIC}, {name: LS, type: Bool, section: STATIC}, {name: R1, type: Bool, section: STATIC}, {name: RA, type: Bool, section: STATIC}, {name: S0, type: Bool, section: STATIC}, {name: S1, type: Bool, section: STATIC}, {name: SM, type: Bool, section: STATIC}, {name: SNO, type: Int, section: STATIC, start: '4'}, {name: SS, type: Bool, section: STATIC}, {name: T, type: Time, section: STATIC}, {name: T_MAX, type: Time, section: STATIC, start: T#10S}, {name: T_WARN, type: Time, section: STATIC, start: T#7S}, {name: U, type: Time, section: STATIC}, {name: V0, type: Bool, section: STATIC}, {name: V1, type: Bool, section: STATIC}, {name: VA, type: Bool, section: STATIC}, {name: VS, type: Bool, section: STATIC}, {name: X, type: Bool, section: STATIC}]}
- {name: Step5, type: G7_StepPlus_V6, section: STATIC, retain: false, comment: {de-DE: Schrittstruktur}, accessible: false, visible: false, writable: false, members: [{name: A1, type: Bool, section: STATIC}, {name: AA, type: Bool, section: STATIC}, {name: CRIT_LOC, type: DWord, section: STATIC}, {name: CRIT_LOC_ERR, type: DWord, section: STATIC}, {name: H_IL_ERR, type: Byte, section: STATIC}, {name: H_SV_FLT, type: Byte, section: STATIC, start: 16#04}, {name: L0, type: Bool, section: STATIC}, {name: L1, type: Bool, section: STATIC}, {name: LA, type: Bool, section: STATIC}, {name: LS, type: Bool, section: STATIC}, {name: R1, type: Bool, section: STATIC}, {name: RA, type: Bool, section: STATIC}, {name: S0, type: Bool, section: STATIC}, {name: S1, type: Bool, section: STATIC}, {name: SM, type: Bool, section: STATIC}, {name: SNO, type: Int, section: STATIC, start: '5'}, {name: SS, type: Bool, section: STATIC}, {name: T, type: Time, section: STATIC}, {name: T_MAX, type: Time, section: STATIC, start: T#10S}, {name: T_WARN, type: Time, section: STATIC, start: T#7S}, {name: U, type: Time, section: STATIC}, {name: V0, type: Bool, section: STATIC}, {name: V1, type: Bool, section: STATIC}, {name: VA, type: Bool, section: STATIC}, {name: VS, type: Bool, section: STATIC}, {name: X, type: Bool, section: STATIC}]}
- {name: Step6, type: G7_StepPlus_V6, section: STATIC, retain: false, comment: {de-DE: Schrittstruktur}, accessible: false, visible: false, writable: false, members: [{name: A1, type: Bool, section: STATIC}, {name: AA, type: Bool, section: STATIC}, {name: CRIT_LOC, type: DWord, section: STATIC}, {name: CRIT_LOC_ERR, type: DWord, section: STATIC}, {name: H_IL_ERR, type: Byte, section: STATIC}, {name: H_SV_FLT, type: Byte, section: STATIC, start: 16#04}, {name: L0, type: Bool, section: STATIC}, {name: L1, type: Bool, section: STATIC}, {name: LA, type: Bool, section: STATIC}, {name: LS, type: Bool, section: STATIC}, {name: R1, type: Bool, section: STATIC}, {name: RA, type: Bool, section: STATIC}, {name: S0, type: Bool, section: STATIC}, {name: S1, type: Bool, section: STATIC}, {name: SM, type: Bool, section: STATIC}, {name: SNO, type: Int, section: STATIC, start: '6'}, {name: SS, type: Bool, section: STATIC}, {name: T, type: Time, section: STATIC}, {name: T_MAX, type: Time, section: STATIC, start: T#10S}, {name: T_WARN, type: Time, section: STATIC, start: T#7S}, {name: U, type: Time, section: STATIC}, {name: V0, type: Bool, section: STATIC}, {name: V1, type: Bool, section: STATIC}, {name: VA, type: Bool, section: STATIC}, {name: VS, type: Bool, section: STATIC}, {name: X, type: Bool, section: STATIC}]}
- {name: Trans1, type: G7_TransitionPlus_V6, section: STATIC, retain: false, comment: {de-DE: Transitionsstruktur}, accessible: false, visible: false, writable: false, members: [{name: CRIT, type: DWord, section: STATIC}, {name: CRIT_FLT, type: DWord, section: STATIC}, {name: CRIT_OLD, type: DWord, section: STATIC}, {name: TNO, type: Int, section: STATIC, start: '1'}, {name: TS, type: Bool, section: STATIC}, {name: TT, type: Bool, section: STATIC}, {name: TV, type: Bool, section: STATIC}]}
- {name: Trans2, type: G7_TransitionPlus_V6, section: STATIC, retain: false, comment: {de-DE: Transitionsstruktur}, accessible: false, visible: false, writable: false, members: [{name: CRIT, type: DWord, section: STATIC}, {name: CRIT_FLT, type: DWord, section: STATIC}, {name: CRIT_OLD, type: DWord, section: STATIC}, {name: TNO, type: Int, section: STATIC, start: '2'}, {name: TS, type: Bool, section: STATIC}, {name: TT, type: Bool, section: STATIC}, {name: TV, type: Bool, section: STATIC}]}
- {name: Trans3, type: G7_TransitionPlus_V6, section: STATIC, retain: false, comment: {de-DE: Transitionsstruktur}, accessible: false, visible: false, writable: false, members: [{name: CRIT, type: DWord, section: STATIC}, {name: CRIT_FLT, type: DWord, section: STATIC}, {name: CRIT_OLD, type: DWord, section: STATIC}, {name: TNO, type: Int, section: STATIC, start: '3'}, {name: TS, type: Bool, section: STATIC}, {name: TT, type: Bool, section: STATIC}, {name: TV, type: Bool, section: STATIC}]}
- {name: Trans4, type: G7_TransitionPlus_V6, section: STATIC, retain: false, comment: {de-DE: Transitionsstruktur}, accessible: false, visible: false, writable: false, members: [{name: CRIT, type: DWord, section: STATIC}, {name: CRIT_FLT, type: DWord, section: STATIC}, {name: CRIT_OLD, type: DWord, section: STATIC}, {name: TNO, type: Int, section: STATIC, start: '4'}, {name: TS, type: Bool, section: STATIC}, {name: TT, type: Bool, section: STATIC}, {name: TV, type: Bool, section: STATIC}]}
- {name: Trans5, type: G7_TransitionPlus_V6, section: STATIC, retain: false, comment: {de-DE: Transitionsstruktur}, accessible: false, visible: false, writable: false, members: [{name: CRIT, type: DWord, section: STATIC}, {name: CRIT_FLT, type: DWord, section: STATIC}, {name: CRIT_OLD, type: DWord, section: STATIC}, {name: TNO, type: Int, section: STATIC, start: '5'}, {name: TS, type: Bool, section: STATIC}, {name: TT, type: Bool, section: STATIC}, {name: TV, type: Bool, section: STATIC}]}
- {name: Trans6, type: G7_TransitionPlus_V6, section: STATIC, retain: false, comment: {de-DE: Transitionsstruktur}, accessible: false, visible: false, writable: false, members: [{name: CRIT, type: DWord, section: STATIC}, {name: CRIT_FLT, type: DWord, section: STATIC}, {name: CRIT_OLD, type: DWord, section: STATIC}, {name: TNO, type: Int, section: STATIC, start: '6'}, {name: TS, type: Bool, section: STATIC}, {name: TT, type: Bool, section: STATIC}, {name: TV, type: Bool, section: STATIC}]}
- {name: Trans7, type: G7_TransitionPlus_V6, section: STATIC, retain: false, comment: {de-DE: Transitionsstruktur}, accessible: false, visible: false, writable: false, members: [{name: CRIT, type: DWord, section: STATIC}, {name: CRIT_FLT, type: DWord, section: STATIC}, {name: CRIT_OLD, type: DWord, section: STATIC}, {name: TNO, type: Int, section: STATIC, start: '7'}, {name: TS, type: Bool, section: STATIC}, {name: TT, type: Bool, section: STATIC}, {name: TV, type: Bool, section: STATIC}]}
networks:
- {'no': 1, line_start: 444, line_end: 461}
---

# Baustein_Graph

## Interface
| Section | Name | Type | Start | Comment |
|---|---|---|---|---|
| IN | ACK_EF | Bool | false | de-DE: Alle Fehler und Störungen quittieren |
| IN | INIT_SQ | Bool | false | de-DE: Kette in Initialzustand versetzen |
| IN | OFF_SQ | Bool | false | de-DE: Kette ausschalten |
| IN | SW_AUTO | Bool | false | de-DE: Automatischer Betrieb |
| IN | SW_MAN | Bool | false | de-DE: Handbetrieb |
| IN | SW_TAP | Bool | false | de-DE: Halbautomatisch/Weiterschalten mit Transition |
| IN | SW_TOP | Bool | false | de-DE: Halbautomatisch/Ignoriere Transition |
| IN | S_NEXT | Bool | false | de-DE: Nächsten Schritt am Parameter S_NO anzeigen |
| IN | S_OFF | Bool | false | de-DE: Schritt deaktivieren, der an Parameter S_NO anliegt |
| IN | S_ON | Bool | false | de-DE: Schritt aktivieren, der an Parameter S_NO anliegt |
| IN | S_PREV | Bool | false | de-DE: Vorherigen Schritt am Parameter S_NO ausgeben |
| IN | S_SEL | Int | 0 | de-DE: Schritt auswählen, der an S_NO ausgegeben werden soll |
| IN | T_PUSH | Bool | false | de-DE: Schaltfreigabe für Transition im halbautomatischen Betrieb |
| OUT | AUTO_ON | Bool | false | de-DE: Automatischer Betrieb eingeschaltet |
| OUT | ERR_FLT | Bool | false | de-DE: Sammelfehler Interlock oder Supervision |
| OUT | MAN_ON | Bool | false | de-DE: Handbetrieb eingeschaltet |
| OUT | S_ACTIVE | Bool | false | de-DE: Schritt, der an Parameter S_NO angezeigt wird, ist aktiv |
| OUT | S_MORE | Bool | false | de-DE: Weitere Schritte sind vorhanden und können in S_NO angezeigt werden. |
| OUT | S_NO | Int | 0 | de-DE: Schrittnummer |
| OUT | TAP_ON | Bool | false | de-DE: Halbautomatischer Betrieb/Schritt mit Transition eingeschaltet |
| OUT | TOP_ON | Bool | false | de-DE: Halbautomatischer Betrieb/Ignoriere Transition eingeschaltet |
| STATIC | RT_DATA | G7_RTDataPlus_V6 |  | de-DE: Interner Datenbereich |
| STATIC | RT_DATA.AS_MSG | Byte | 16#65 |  |
| STATIC | RT_DATA.EXEC_BITS | Array[0..249] of Bool |  |  |
| STATIC | RT_DATA.GC_FLAGS | G7_GCFlagsPlus_V6 |  |  |
| STATIC | RT_DATA.GC_FLAGS.ACK_REQ | Bool | true |  |
| STATIC | RT_DATA.GC_FLAGS.COND_ED | USInt | 16#E3 |  |
| STATIC | RT_DATA.GC_FLAGS.CRIT_ON | Bool |  |  |
| STATIC | RT_DATA.GC_FLAGS.ILP_MAN | Bool |  |  |
| STATIC | RT_DATA.GC_FLAGS.IL_CAT | USInt | 1 |  |
| STATIC | RT_DATA.GC_FLAGS.IL_SUBCAT_1 | USInt |  |  |
| STATIC | RT_DATA.GC_FLAGS.IL_SUBCAT_2 | USInt |  |  |
| STATIC | RT_DATA.GC_FLAGS.REACT_CAT | USInt | 1 |  |
| STATIC | RT_DATA.GC_FLAGS.REACT_SUBCAT_1 | USInt |  |  |
| STATIC | RT_DATA.GC_FLAGS.REACT_SUBCAT_2 | USInt |  |  |
| STATIC | RT_DATA.GC_FLAGS.SET_ENO | Bool |  |  |
| STATIC | RT_DATA.GC_FLAGS.SSKIP_ON | Bool |  |  |
| STATIC | RT_DATA.GC_FLAGS.SWM_LOCKED | Bool |  |  |
| STATIC | RT_DATA.GC_FLAGS.WARN_CAT | USInt | 2 |  |
| STATIC | RT_DATA.GC_FLAGS.WARN_SUBCAT_1 | USInt |  |  |
| STATIC | RT_DATA.GC_FLAGS.WARN_SUBCAT_2 | USInt |  |  |
| STATIC | RT_DATA.LOCK_CNT | USInt |  |  |
| STATIC | RT_DATA.MAX_SACT | USInt | 1 |  |
| STATIC | RT_DATA.MAX_TVAL | USInt | 3 |  |
| STATIC | RT_DATA.MOP | G7_MOPPlus_V6 |  |  |
| STATIC | RT_DATA.MOP.ACK | Bool |  |  |
| STATIC | RT_DATA.MOP.ACKREQ | Bool | true |  |
| STATIC | RT_DATA.MOP.ACK_S | Bool |  |  |
| STATIC | RT_DATA.MOP.AUTO | Bool | true |  |
| STATIC | RT_DATA.MOP.HALT | Bool |  |  |
| STATIC | RT_DATA.MOP.ILP_MAN | Bool |  |  |
| STATIC | RT_DATA.MOP.IL_PERM | Bool |  |  |
| STATIC | RT_DATA.MOP.INIT | Bool | true |  |
| STATIC | RT_DATA.MOP.LMODE | Bool |  |  |
| STATIC | RT_DATA.MOP.LOCK | Bool | true |  |
| STATIC | RT_DATA.MOP.MAN | Bool |  |  |
| STATIC | RT_DATA.MOP.OFF | Bool |  |  |
| STATIC | RT_DATA.MOP.OPS_ZERO | Bool |  |  |
| STATIC | RT_DATA.MOP.REG | Bool |  |  |
| STATIC | RT_DATA.MOP.REG_S | Bool |  |  |
| STATIC | RT_DATA.MOP.RESET_CRIT | Bool |  |  |
| STATIC | RT_DATA.MOP.SACT_DISP | Bool | true |  |
| STATIC | RT_DATA.MOP.SALL_DISP | Bool |  |  |
| STATIC | RT_DATA.MOP.SEF_DISP | Bool |  |  |
| STATIC | RT_DATA.MOP.SSKIP | Bool |  |  |
| STATIC | RT_DATA.MOP.SUP | Bool | true |  |
| STATIC | RT_DATA.MOP.S_NEXT | Bool |  |  |
| STATIC | RT_DATA.MOP.S_OFF | Bool |  |  |
| STATIC | RT_DATA.MOP.S_ON | Bool |  |  |
| STATIC | RT_DATA.MOP.S_PREV | Bool |  |  |
| STATIC | RT_DATA.MOP.S_SELOK | Bool |  |  |
| STATIC | RT_DATA.MOP.TAP | Bool |  |  |
| STATIC | RT_DATA.MOP.TMS_HALT | Bool |  |  |
| STATIC | RT_DATA.MOP.TOP | Bool |  |  |
| STATIC | RT_DATA.MOP.T_NEXT | Bool |  |  |
| STATIC | RT_DATA.MOP.T_PERM | Bool |  |  |
| STATIC | RT_DATA.MOP.T_PREV | Bool |  |  |
| STATIC | RT_DATA.MOP.T_PUSH | Bool |  |  |
| STATIC | RT_DATA.MOP_EDGE | G7_MOPPlus_V6 |  |  |
| STATIC | RT_DATA.MOP_EDGE.ACK | Bool |  |  |
| STATIC | RT_DATA.MOP_EDGE.ACKREQ | Bool |  |  |
| STATIC | RT_DATA.MOP_EDGE.ACK_S | Bool |  |  |
| STATIC | RT_DATA.MOP_EDGE.AUTO | Bool |  |  |
| STATIC | RT_DATA.MOP_EDGE.HALT | Bool |  |  |
| STATIC | RT_DATA.MOP_EDGE.ILP_MAN | Bool |  |  |
| STATIC | RT_DATA.MOP_EDGE.IL_PERM | Bool |  |  |
| STATIC | RT_DATA.MOP_EDGE.INIT | Bool |  |  |
| STATIC | RT_DATA.MOP_EDGE.LMODE | Bool |  |  |
| STATIC | RT_DATA.MOP_EDGE.LOCK | Bool |  |  |
| STATIC | RT_DATA.MOP_EDGE.MAN | Bool |  |  |
| STATIC | RT_DATA.MOP_EDGE.OFF | Bool |  |  |
| STATIC | RT_DATA.MOP_EDGE.OPS_ZERO | Bool |  |  |
| STATIC | RT_DATA.MOP_EDGE.REG | Bool |  |  |
| STATIC | RT_DATA.MOP_EDGE.REG_S | Bool |  |  |
| STATIC | RT_DATA.MOP_EDGE.RESET_CRIT | Bool |  |  |
| STATIC | RT_DATA.MOP_EDGE.SACT_DISP | Bool |  |  |
| STATIC | RT_DATA.MOP_EDGE.SALL_DISP | Bool |  |  |
| STATIC | RT_DATA.MOP_EDGE.SEF_DISP | Bool |  |  |
| STATIC | RT_DATA.MOP_EDGE.SSKIP | Bool |  |  |
| STATIC | RT_DATA.MOP_EDGE.SUP | Bool |  |  |
| STATIC | RT_DATA.MOP_EDGE.S_NEXT | Bool |  |  |
| STATIC | RT_DATA.MOP_EDGE.S_OFF | Bool |  |  |
| STATIC | RT_DATA.MOP_EDGE.S_ON | Bool |  |  |
| STATIC | RT_DATA.MOP_EDGE.S_PREV | Bool |  |  |
| STATIC | RT_DATA.MOP_EDGE.S_SELOK | Bool |  |  |
| STATIC | RT_DATA.MOP_EDGE.TAP | Bool |  |  |
| STATIC | RT_DATA.MOP_EDGE.TMS_HALT | Bool |  |  |
| STATIC | RT_DATA.MOP_EDGE.TOP | Bool |  |  |
| STATIC | RT_DATA.MOP_EDGE.T_NEXT | Bool |  |  |
| STATIC | RT_DATA.MOP_EDGE.T_PERM | Bool |  |  |
| STATIC | RT_DATA.MOP_EDGE.T_PREV | Bool |  |  |
| STATIC | RT_DATA.MOP_EDGE.T_PUSH | Bool |  |  |
| STATIC | RT_DATA.OFFSETS | G7_OffsetsPlus_V6 |  |  |
| STATIC | RT_DATA.OFFSETS.ASSB_OFFSET | UInt | 43 |  |
| STATIC | RT_DATA.OFFSETS.ASSJ_OFFSET | UInt | 37 |  |
| STATIC | RT_DATA.OFFSETS.ATAB_OFFSET | UInt | 16 |  |
| STATIC | RT_DATA.OFFSETS.ATAJ_OFFSET | UInt | 9 |  |
| STATIC | RT_DATA.OFFSETS.LSTT_OFFSET | UInt | 2 |  |
| STATIC | RT_DATA.OFFSETS.NSTT_OFFSET | UInt | 30 |  |
| STATIC | RT_DATA.OFFSETS.NTTS_OFFSET | UInt | 55 |  |
| STATIC | RT_DATA.OFFSETS.PSTT_OFFSET | UInt | 23 |  |
| STATIC | RT_DATA.OFFSETS.PTTS_OFFSET | UInt | 49 |  |
| STATIC | RT_DATA.OFFSETS.S00X_OFFSET | UInt | 79 |  |
| STATIC | RT_DATA.OFFSETS.S0X_OFFSET | UInt | 101 |  |
| STATIC | RT_DATA.OFFSETS.S1X_OFFSET | UInt | 108 |  |
| STATIC | RT_DATA.OFFSETS.SAX_OFFSET | UInt | 85 |  |
| STATIC | RT_DATA.OFFSETS.SERRX_OFFSET | UInt | 87 |  |
| STATIC | RT_DATA.OFFSETS.SINI_OFFSET | UInt |  |  |
| STATIC | RT_DATA.OFFSETS.SMX_OFFSET | UInt | 94 |  |
| STATIC | RT_DATA.OFFSETS.SOFFX_OFFSET | UInt | 81 |  |
| STATIC | RT_DATA.OFFSETS.SONX_OFFSET | UInt | 83 |  |
| STATIC | RT_DATA.OFFSETS.SWITCH_OFFSET | UInt | 67 |  |
| STATIC | RT_DATA.OFFSETS.SW_SQTS_OFFSET | UInt | 61 |  |
| STATIC | RT_DATA.OFFSETS.TSX_OFFSET | UInt | 77 |  |
| STATIC | RT_DATA.OFFSETS.TTX_OFFSET | UInt | 73 |  |
| STATIC | RT_DATA.OFFSETS.TVX_OFFSET | UInt | 69 |  |
| STATIC | RT_DATA.POST_CNT | USInt | 1 |  |
| STATIC | RT_DATA.PRE_CNT | USInt | 1 |  |
| STATIC | RT_DATA.SQ_CNT | USInt | 1 |  |
| STATIC | RT_DATA.SQ_FLAGS | G7_SQFlagsPlus_V6 |  |  |
| STATIC | RT_DATA.SQ_FLAGS.AS_MSG | Bool | true |  |
| STATIC | RT_DATA.SQ_FLAGS.CYC_OP | Bool |  |  |
| STATIC | RT_DATA.SQ_FLAGS.ERROR | Bool |  |  |
| STATIC | RT_DATA.SQ_FLAGS.ERR_FLT | Bool |  |  |
| STATIC | RT_DATA.SQ_FLAGS.FAULT | Bool |  |  |
| STATIC | RT_DATA.SQ_FLAGS.NF_OFL | Bool |  |  |
| STATIC | RT_DATA.SQ_FLAGS.NO_SNO | Bool |  |  |
| STATIC | RT_DATA.SQ_FLAGS.NO_SWI | Bool |  |  |
| STATIC | RT_DATA.SQ_FLAGS.RT_FAIL | Bool |  |  |
| STATIC | RT_DATA.SQ_FLAGS.SA_BUSY | Bool |  |  |
| STATIC | RT_DATA.SQ_FLAGS.SA_OFL | Bool |  |  |
| STATIC | RT_DATA.SQ_FLAGS.SQ_BUSY | Bool |  |  |
| STATIC | RT_DATA.SQ_FLAGS.TV_OFL | Bool |  |  |
| STATIC | RT_DATA.SQ_PART_CNT | USInt | 4 |  |
| STATIC | RT_DATA.SUP_CNT | USInt |  |  |
| STATIC | RT_DATA.S_CNT | USInt | 6 |  |
| STATIC | RT_DATA.S_DISPIDX | USInt | 255 |  |
| STATIC | RT_DATA.S_DISPLAY | Int |  |  |
| STATIC | RT_DATA.S_SEL_OLD | Int |  |  |
| STATIC | RT_DATA.THRESHOLD_SUP | USInt |  |  |
| STATIC | RT_DATA.THRESHOLD_WARN | USInt |  |  |
| STATIC | RT_DATA.TIME_DELTA | Time |  |  |
| STATIC | RT_DATA.T_CNT | USInt | 7 |  |
| STATIC | RT_DATA.T_DISPIDX | USInt | 255 |  |
| STATIC | RT_DATA.VERSION | String[10] | 'V6.0' |  |
| STATIC | Step1 | G7_StepPlus_V6 |  | de-DE: Schrittstruktur |
| STATIC | Step1.A1 | Bool |  |  |
| STATIC | Step1.AA | Bool |  |  |
| STATIC | Step1.CRIT_LOC | DWord |  |  |
| STATIC | Step1.CRIT_LOC_ERR | DWord |  |  |
| STATIC | Step1.H_IL_ERR | Byte |  |  |
| STATIC | Step1.H_SV_FLT | Byte | 16#04 |  |
| STATIC | Step1.L0 | Bool |  |  |
| STATIC | Step1.L1 | Bool |  |  |
| STATIC | Step1.LA | Bool |  |  |
| STATIC | Step1.LS | Bool |  |  |
| STATIC | Step1.R1 | Bool |  |  |
| STATIC | Step1.RA | Bool |  |  |
| STATIC | Step1.S0 | Bool |  |  |
| STATIC | Step1.S1 | Bool |  |  |
| STATIC | Step1.SM | Bool |  |  |
| STATIC | Step1.SNO | Int | 1 |  |
| STATIC | Step1.SS | Bool |  |  |
| STATIC | Step1.T | Time |  |  |
| STATIC | Step1.T_MAX | Time | T#10S |  |
| STATIC | Step1.T_WARN | Time | T#7S |  |
| STATIC | Step1.U | Time |  |  |
| STATIC | Step1.V0 | Bool |  |  |
| STATIC | Step1.V1 | Bool |  |  |
| STATIC | Step1.VA | Bool |  |  |
| STATIC | Step1.VS | Bool |  |  |
| STATIC | Step1.X | Bool |  |  |
| STATIC | Step2 | G7_StepPlus_V6 |  | de-DE: Schrittstruktur |
| STATIC | Step2.A1 | Bool |  |  |
| STATIC | Step2.AA | Bool |  |  |
| STATIC | Step2.CRIT_LOC | DWord |  |  |
| STATIC | Step2.CRIT_LOC_ERR | DWord |  |  |
| STATIC | Step2.H_IL_ERR | Byte |  |  |
| STATIC | Step2.H_SV_FLT | Byte | 16#04 |  |
| STATIC | Step2.L0 | Bool |  |  |
| STATIC | Step2.L1 | Bool |  |  |
| STATIC | Step2.LA | Bool |  |  |
| STATIC | Step2.LS | Bool |  |  |
| STATIC | Step2.R1 | Bool |  |  |
| STATIC | Step2.RA | Bool |  |  |
| STATIC | Step2.S0 | Bool |  |  |
| STATIC | Step2.S1 | Bool |  |  |
| STATIC | Step2.SM | Bool |  |  |
| STATIC | Step2.SNO | Int | 2 |  |
| STATIC | Step2.SS | Bool |  |  |
| STATIC | Step2.T | Time |  |  |
| STATIC | Step2.T_MAX | Time | T#10S |  |
| STATIC | Step2.T_WARN | Time | T#7S |  |
| STATIC | Step2.U | Time |  |  |
| STATIC | Step2.V0 | Bool |  |  |
| STATIC | Step2.V1 | Bool |  |  |
| STATIC | Step2.VA | Bool |  |  |
| STATIC | Step2.VS | Bool |  |  |
| STATIC | Step2.X | Bool |  |  |
| STATIC | Step3 | G7_StepPlus_V6 |  | de-DE: Schrittstruktur |
| STATIC | Step3.A1 | Bool |  |  |
| STATIC | Step3.AA | Bool |  |  |
| STATIC | Step3.CRIT_LOC | DWord |  |  |
| STATIC | Step3.CRIT_LOC_ERR | DWord |  |  |
| STATIC | Step3.H_IL_ERR | Byte |  |  |
| STATIC | Step3.H_SV_FLT | Byte | 16#04 |  |
| STATIC | Step3.L0 | Bool |  |  |
| STATIC | Step3.L1 | Bool |  |  |
| STATIC | Step3.LA | Bool |  |  |
| STATIC | Step3.LS | Bool |  |  |
| STATIC | Step3.R1 | Bool |  |  |
| STATIC | Step3.RA | Bool |  |  |
| STATIC | Step3.S0 | Bool |  |  |
| STATIC | Step3.S1 | Bool |  |  |
| STATIC | Step3.SM | Bool |  |  |
| STATIC | Step3.SNO | Int | 3 |  |
| STATIC | Step3.SS | Bool |  |  |
| STATIC | Step3.T | Time |  |  |
| STATIC | Step3.T_MAX | Time | T#10S |  |
| STATIC | Step3.T_WARN | Time | T#7S |  |
| STATIC | Step3.U | Time |  |  |
| STATIC | Step3.V0 | Bool |  |  |
| STATIC | Step3.V1 | Bool |  |  |
| STATIC | Step3.VA | Bool |  |  |
| STATIC | Step3.VS | Bool |  |  |
| STATIC | Step3.X | Bool |  |  |
| STATIC | Step4 | G7_StepPlus_V6 |  | de-DE: Schrittstruktur |
| STATIC | Step4.A1 | Bool |  |  |
| STATIC | Step4.AA | Bool |  |  |
| STATIC | Step4.CRIT_LOC | DWord |  |  |
| STATIC | Step4.CRIT_LOC_ERR | DWord |  |  |
| STATIC | Step4.H_IL_ERR | Byte |  |  |
| STATIC | Step4.H_SV_FLT | Byte | 16#04 |  |
| STATIC | Step4.L0 | Bool |  |  |
| STATIC | Step4.L1 | Bool |  |  |
| STATIC | Step4.LA | Bool |  |  |
| STATIC | Step4.LS | Bool |  |  |
| STATIC | Step4.R1 | Bool |  |  |
| STATIC | Step4.RA | Bool |  |  |
| STATIC | Step4.S0 | Bool |  |  |
| STATIC | Step4.S1 | Bool |  |  |
| STATIC | Step4.SM | Bool |  |  |
| STATIC | Step4.SNO | Int | 4 |  |
| STATIC | Step4.SS | Bool |  |  |
| STATIC | Step4.T | Time |  |  |
| STATIC | Step4.T_MAX | Time | T#10S |  |
| STATIC | Step4.T_WARN | Time | T#7S |  |
| STATIC | Step4.U | Time |  |  |
| STATIC | Step4.V0 | Bool |  |  |
| STATIC | Step4.V1 | Bool |  |  |
| STATIC | Step4.VA | Bool |  |  |
| STATIC | Step4.VS | Bool |  |  |
| STATIC | Step4.X | Bool |  |  |
| STATIC | Step5 | G7_StepPlus_V6 |  | de-DE: Schrittstruktur |
| STATIC | Step5.A1 | Bool |  |  |
| STATIC | Step5.AA | Bool |  |  |
| STATIC | Step5.CRIT_LOC | DWord |  |  |
| STATIC | Step5.CRIT_LOC_ERR | DWord |  |  |
| STATIC | Step5.H_IL_ERR | Byte |  |  |
| STATIC | Step5.H_SV_FLT | Byte | 16#04 |  |
| STATIC | Step5.L0 | Bool |  |  |
| STATIC | Step5.L1 | Bool |  |  |
| STATIC | Step5.LA | Bool |  |  |
| STATIC | Step5.LS | Bool |  |  |
| STATIC | Step5.R1 | Bool |  |  |
| STATIC | Step5.RA | Bool |  |  |
| STATIC | Step5.S0 | Bool |  |  |
| STATIC | Step5.S1 | Bool |  |  |
| STATIC | Step5.SM | Bool |  |  |
| STATIC | Step5.SNO | Int | 5 |  |
| STATIC | Step5.SS | Bool |  |  |
| STATIC | Step5.T | Time |  |  |
| STATIC | Step5.T_MAX | Time | T#10S |  |
| STATIC | Step5.T_WARN | Time | T#7S |  |
| STATIC | Step5.U | Time |  |  |
| STATIC | Step5.V0 | Bool |  |  |
| STATIC | Step5.V1 | Bool |  |  |
| STATIC | Step5.VA | Bool |  |  |
| STATIC | Step5.VS | Bool |  |  |
| STATIC | Step5.X | Bool |  |  |
| STATIC | Step6 | G7_StepPlus_V6 |  | de-DE: Schrittstruktur |
| STATIC | Step6.A1 | Bool |  |  |
| STATIC | Step6.AA | Bool |  |  |
| STATIC | Step6.CRIT_LOC | DWord |  |  |
| STATIC | Step6.CRIT_LOC_ERR | DWord |  |  |
| STATIC | Step6.H_IL_ERR | Byte |  |  |
| STATIC | Step6.H_SV_FLT | Byte | 16#04 |  |
| STATIC | Step6.L0 | Bool |  |  |
| STATIC | Step6.L1 | Bool |  |  |
| STATIC | Step6.LA | Bool |  |  |
| STATIC | Step6.LS | Bool |  |  |
| STATIC | Step6.R1 | Bool |  |  |
| STATIC | Step6.RA | Bool |  |  |
| STATIC | Step6.S0 | Bool |  |  |
| STATIC | Step6.S1 | Bool |  |  |
| STATIC | Step6.SM | Bool |  |  |
| STATIC | Step6.SNO | Int | 6 |  |
| STATIC | Step6.SS | Bool |  |  |
| STATIC | Step6.T | Time |  |  |
| STATIC | Step6.T_MAX | Time | T#10S |  |
| STATIC | Step6.T_WARN | Time | T#7S |  |
| STATIC | Step6.U | Time |  |  |
| STATIC | Step6.V0 | Bool |  |  |
| STATIC | Step6.V1 | Bool |  |  |
| STATIC | Step6.VA | Bool |  |  |
| STATIC | Step6.VS | Bool |  |  |
| STATIC | Step6.X | Bool |  |  |
| STATIC | Trans1 | G7_TransitionPlus_V6 |  | de-DE: Transitionsstruktur |
| STATIC | Trans1.CRIT | DWord |  |  |
| STATIC | Trans1.CRIT_FLT | DWord |  |  |
| STATIC | Trans1.CRIT_OLD | DWord |  |  |
| STATIC | Trans1.TNO | Int | 1 |  |
| STATIC | Trans1.TS | Bool |  |  |
| STATIC | Trans1.TT | Bool |  |  |
| STATIC | Trans1.TV | Bool |  |  |
| STATIC | Trans2 | G7_TransitionPlus_V6 |  | de-DE: Transitionsstruktur |
| STATIC | Trans2.CRIT | DWord |  |  |
| STATIC | Trans2.CRIT_FLT | DWord |  |  |
| STATIC | Trans2.CRIT_OLD | DWord |  |  |
| STATIC | Trans2.TNO | Int | 2 |  |
| STATIC | Trans2.TS | Bool |  |  |
| STATIC | Trans2.TT | Bool |  |  |
| STATIC | Trans2.TV | Bool |  |  |
| STATIC | Trans3 | G7_TransitionPlus_V6 |  | de-DE: Transitionsstruktur |
| STATIC | Trans3.CRIT | DWord |  |  |
| STATIC | Trans3.CRIT_FLT | DWord |  |  |
| STATIC | Trans3.CRIT_OLD | DWord |  |  |
| STATIC | Trans3.TNO | Int | 3 |  |
| STATIC | Trans3.TS | Bool |  |  |
| STATIC | Trans3.TT | Bool |  |  |
| STATIC | Trans3.TV | Bool |  |  |
| STATIC | Trans4 | G7_TransitionPlus_V6 |  | de-DE: Transitionsstruktur |
| STATIC | Trans4.CRIT | DWord |  |  |
| STATIC | Trans4.CRIT_FLT | DWord |  |  |
| STATIC | Trans4.CRIT_OLD | DWord |  |  |
| STATIC | Trans4.TNO | Int | 4 |  |
| STATIC | Trans4.TS | Bool |  |  |
| STATIC | Trans4.TT | Bool |  |  |
| STATIC | Trans4.TV | Bool |  |  |
| STATIC | Trans5 | G7_TransitionPlus_V6 |  | de-DE: Transitionsstruktur |
| STATIC | Trans5.CRIT | DWord |  |  |
| STATIC | Trans5.CRIT_FLT | DWord |  |  |
| STATIC | Trans5.CRIT_OLD | DWord |  |  |
| STATIC | Trans5.TNO | Int | 5 |  |
| STATIC | Trans5.TS | Bool |  |  |
| STATIC | Trans5.TT | Bool |  |  |
| STATIC | Trans5.TV | Bool |  |  |
| STATIC | Trans6 | G7_TransitionPlus_V6 |  | de-DE: Transitionsstruktur |
| STATIC | Trans6.CRIT | DWord |  |  |
| STATIC | Trans6.CRIT_FLT | DWord |  |  |
| STATIC | Trans6.CRIT_OLD | DWord |  |  |
| STATIC | Trans6.TNO | Int | 6 |  |
| STATIC | Trans6.TS | Bool |  |  |
| STATIC | Trans6.TT | Bool |  |  |
| STATIC | Trans6.TV | Bool |  |  |
| STATIC | Trans7 | G7_TransitionPlus_V6 |  | de-DE: Transitionsstruktur |
| STATIC | Trans7.CRIT | DWord |  |  |
| STATIC | Trans7.CRIT_FLT | DWord |  |  |
| STATIC | Trans7.CRIT_OLD | DWord |  |  |
| STATIC | Trans7.TNO | Int | 7 |  |
| STATIC | Trans7.TS | Bool |  |  |
| STATIC | Trans7.TT | Bool |  |  |
| STATIC | Trans7.TV | Bool |  |  |

## NW 1

```ntn
INITIAL STEP Step1;
STEP Step2;
  ACTION S { "Datenbaustein_1".write.bool1 }
STEP Step3;
STEP Step4;
STEP Step5;
STEP Step6;
TRANSITION Step1 -> Step2 WHEN TRUE; // Trans1
TRANSITION Step2 -> Step3 WHEN TRUE; // Trans2
TRANSITION Step3 -> Step5 WHEN TRUE; // Trans3
TRANSITION Step3 -> Step4 WHEN TRUE; // Trans4
TRANSITION Step4 -> Step6 WHEN TRUE; // Trans5
TRANSITION Step5 -> Step6 WHEN TRUE; // Trans6
TRANSITION Step6 -> END WHEN TRUE; // Trans7
```
