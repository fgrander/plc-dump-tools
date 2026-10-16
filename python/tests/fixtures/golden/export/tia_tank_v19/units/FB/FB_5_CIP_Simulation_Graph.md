---
name: FB_5_CIP_Simulation_Graph
kind: FB
number: 7
language: ntn
original_language: GRAPH
protected: false
parse_quality: full
folder: Programmbausteine
attributes:
  route: simaticml
  version: '0.1'
path_prefix: '"FB_5_CIP_Simulation_Graph"'
variable_scope: fb_interface
interface:
- {name: ACK_EF, type: Bool, section: IN, start: 'false', retain: false, comment: {en-US: Acknowledge all errors and faults}, accessible: false, visible: false, writable: false}
- {name: INIT_SQ, type: Bool, section: IN, start: 'false', retain: false, comment: {en-US: Set sequence to initial state}, accessible: false, visible: false, writable: false}
- {name: OFF_SQ, type: Bool, section: IN, start: 'false', retain: false, comment: {en-US: Turn sequence off}, accessible: false, visible: false, writable: false}
- {name: SW_AUTO, type: Bool, section: IN, start: 'false', retain: false, comment: {en-US: Automatic mode}, accessible: false, visible: false, writable: false}
- {name: SW_MAN, type: Bool, section: IN, start: 'false', retain: false, comment: {en-US: Manual mode}, accessible: false, visible: false, writable: false}
- {name: SW_TAP, type: Bool, section: IN, start: 'false', retain: false, comment: {en-US: Semiautomatic/switch with transition}, accessible: false, visible: false, writable: false}
- {name: SW_TOP, type: Bool, section: IN, start: 'false', retain: false, comment: {en-US: Semiautomatic/ignore transition}, accessible: false, visible: false, writable: false}
- {name: S_NEXT, type: Bool, section: IN, start: 'false', retain: false, comment: {en-US: Indicate next step in parameter S_NO}, accessible: false, visible: false, writable: false}
- {name: S_OFF, type: Bool, section: IN, start: 'false', retain: false, comment: {en-US: Disable step indicated in S_NO}, accessible: false, visible: false, writable: false}
- {name: S_ON, type: Bool, section: IN, start: 'false', retain: false, comment: {en-US: Activate step indicated in S_NO}, accessible: false, visible: false, writable: false}
- {name: S_PREV, type: Bool, section: IN, start: 'false', retain: false, comment: {en-US: Output previous step in parameter S_NO}, accessible: false, visible: false, writable: false}
- {name: S_SEL, type: Int, section: IN, start: '0', retain: false, comment: {en-US: Select step to be output to S_NO}, accessible: false, visible: false, writable: false}
- {name: T_PUSH, type: Bool, section: IN, start: 'false', retain: false, comment: {en-US: Enable transition to switch in semi automatic mode}, accessible: false, visible: false, writable: false}
- {name: AUTO_ON, type: Bool, section: OUT, start: 'false', retain: false, comment: {en-US: Automatic mode is active}, accessible: false, visible: false, writable: false}
- {name: ERR_FLT, type: Bool, section: OUT, start: 'false', retain: false, comment: {en-US: Interlock or supervision group error}, accessible: false, visible: false, writable: false}
- {name: MAN_ON, type: Bool, section: OUT, start: 'false', retain: false, comment: {en-US: Manual mode is active}, accessible: false, visible: false, writable: false}
- {name: S_ACTIVE, type: Bool, section: OUT, start: 'false', retain: false, comment: {en-US: Step indicated in S_NO is active}, accessible: false, visible: false, writable: false}
- {name: S_MORE, type: Bool, section: OUT, start: 'false', retain: false, comment: {en-US: More steps are available and can be shown in S_NO}, accessible: false, visible: false, writable: false}
- {name: S_NO, type: Int, section: OUT, start: '0', retain: false, comment: {en-US: Step number}, accessible: false, visible: false, writable: false}
- {name: TAP_ON, type: Bool, section: OUT, start: 'false', retain: false, comment: {en-US: Semiautomatic mode/step with transition enabled}, accessible: false, visible: false, writable: false}
- {name: TOP_ON, type: Bool, section: OUT, start: 'false', retain: false, comment: {en-US: Semiautomatic mode/ignore transition enabled}, accessible: false, visible: false, writable: false}
- {name: cip, type: '"typeCIP"', section: IN_OUT, members: [{name: cipActive, type: Bool, section: IN_OUT}, {name: cipConcentration, type: Real, section: IN_OUT}, {name: cipFlowrate, type: Real, section: IN_OUT}, {name: cipId, type: Int, section: IN_OUT}, {name: cipProcess, type: String, section: IN_OUT}, {name: cipStartTime, type: Time_Of_Day, section: IN_OUT}, {name: cipStep, type: String, section: IN_OUT}, {name: cipStep1, type: Bool, section: IN_OUT}, {name: cipStep2, type: Bool, section: IN_OUT}, {name: cipStep3, type: Bool, section: IN_OUT}, {name: cipStep4, type: Bool, section: IN_OUT}, {name: cipTemperature, type: Real, section: IN_OUT}]}
- {name: step1Active, type: Bool, section: IN_OUT, retain: false, comment: {en-US: Step 1 is active}, accessible: true, visible: true, writable: true}
- {name: step2Active, type: Bool, section: IN_OUT, retain: false, comment: {en-US: Step 2 is active}, accessible: true, visible: true, writable: true}
- {name: step3Active, type: Bool, section: IN_OUT, retain: false, comment: {en-US: Step 3 is active}, accessible: true, visible: true, writable: true}
- {name: step4Active, type: Bool, section: IN_OUT, retain: false, comment: {en-US: Step 4 is active}, accessible: true, visible: true, writable: true}
- {name: stepInitial, type: Bool, section: IN_OUT, retain: false, comment: {en-US: Initial step is active}, accessible: true, visible: true, writable: true}
- {name: End, type: G7_TransitionPlus_V6, section: STATIC, retain: false, comment: {en-US: Transition structure}, accessible: false, visible: false, writable: false, members: [{name: CRIT, type: DWord, section: STATIC}, {name: CRIT_FLT, type: DWord, section: STATIC}, {name: CRIT_OLD, type: DWord, section: STATIC}, {name: TNO, type: Int, section: STATIC, start: '6'}, {name: TS, type: Bool, section: STATIC}, {name: TT, type: Bool, section: STATIC}, {name: TV, type: Bool, section: STATIC}]}
- {name: Initial step, type: G7_StepPlus_V6, section: STATIC, retain: false, comment: {en-US: Step structure}, accessible: false, visible: false, writable: false, members: [{name: A1, type: Bool, section: STATIC}, {name: AA, type: Bool, section: STATIC}, {name: CRIT_LOC, type: DWord, section: STATIC}, {name: CRIT_LOC_ERR, type: DWord, section: STATIC}, {name: H_IL_ERR, type: Byte, section: STATIC}, {name: H_SV_FLT, type: Byte, section: STATIC, start: 16#04}, {name: L0, type: Bool, section: STATIC}, {name: L1, type: Bool, section: STATIC}, {name: LA, type: Bool, section: STATIC}, {name: LS, type: Bool, section: STATIC}, {name: R1, type: Bool, section: STATIC}, {name: RA, type: Bool, section: STATIC}, {name: S0, type: Bool, section: STATIC}, {name: S1, type: Bool, section: STATIC}, {name: SM, type: Bool, section: STATIC}, {name: SNO, type: Int, section: STATIC, start: '1'}, {name: SS, type: Bool, section: STATIC}, {name: T, type: Time, section: STATIC}, {name: T_MAX, type: Time, section: STATIC, start: T#10S}, {name: T_WARN, type: Time, section: STATIC, start: T#7S}, {name: U, type: Time, section: STATIC}, {name: V0, type: Bool, section: STATIC}, {name: V1, type: Bool, section: STATIC}, {name: VA, type: Bool, section: STATIC}, {name: VS, type: Bool, section: STATIC}, {name: X, type: Bool, section: STATIC}]}
- {name: RT_DATA, type: G7_RTDataPlus_V6, section: STATIC, retain: false, comment: {en-US: Internal data area}, accessible: false, visible: false, writable: false, members: [{name: AS_MSG, type: Byte, section: STATIC, start: 16#65}, {name: EXEC_BITS, type: 'Array[0..249] of Bool', section: STATIC}, {name: GC_FLAGS, type: G7_GCFlagsPlus_V6, section: STATIC, members: [{name: ACK_REQ, type: Bool, section: STATIC, start: 'true'}, {name: COND_ED, type: USInt, section: STATIC, start: 16#E3}, {name: CRIT_ON, type: Bool, section: STATIC}, {name: ILP_MAN, type: Bool, section: STATIC}, {name: IL_CAT, type: USInt, section: STATIC, start: '1'}, {name: IL_SUBCAT_1, type: USInt, section: STATIC}, {name: IL_SUBCAT_2, type: USInt, section: STATIC}, {name: REACT_CAT, type: USInt, section: STATIC, start: '1'}, {name: REACT_SUBCAT_1, type: USInt, section: STATIC}, {name: REACT_SUBCAT_2, type: USInt, section: STATIC}, {name: SET_ENO, type: Bool, section: STATIC}, {name: SSKIP_ON, type: Bool, section: STATIC}, {name: SWM_LOCKED, type: Bool, section: STATIC}, {name: WARN_CAT, type: USInt, section: STATIC, start: '2'}, {name: WARN_SUBCAT_1, type: USInt, section: STATIC}, {name: WARN_SUBCAT_2, type: USInt, section: STATIC}]}, {name: LOCK_CNT, type: USInt, section: STATIC}, {name: MAX_SACT, type: USInt, section: STATIC, start: '1'}, {name: MAX_TVAL, type: USInt, section: STATIC, start: '1'}, {name: MOP, type: G7_MOPPlus_V6, section: STATIC, members: [{name: ACK, type: Bool, section: STATIC}, {name: ACKREQ, type: Bool, section: STATIC, start: 'true'}, {name: ACK_S, type: Bool, section: STATIC}, {name: AUTO, type: Bool, section: STATIC, start: 'true'}, {name: HALT, type: Bool, section: STATIC}, {name: ILP_MAN, type: Bool, section: STATIC}, {name: IL_PERM, type: Bool, section: STATIC}, {name: INIT, type: Bool, section: STATIC, start: 'true'}, {name: LMODE, type: Bool, section: STATIC}, {name: LOCK, type: Bool, section: STATIC, start: 'true'}, {name: MAN, type: Bool, section: STATIC}, {name: 'OFF', type: Bool, section: STATIC}, {name: OPS_ZERO, type: Bool, section: STATIC}, {name: REG, type: Bool, section: STATIC}, {name: REG_S, type: Bool, section: STATIC}, {name: RESET_CRIT, type: Bool, section: STATIC}, {name: SACT_DISP, type: Bool, section: STATIC, start: 'true'}, {name: SALL_DISP, type: Bool, section: STATIC}, {name: SEF_DISP, type: Bool, section: STATIC}, {name: SSKIP, type: Bool, section: STATIC}, {name: SUP, type: Bool, section: STATIC, start: 'true'}, {name: S_NEXT, type: Bool, section: STATIC}, {name: S_OFF, type: Bool, section: STATIC}, {name: S_ON, type: Bool, section: STATIC}, {name: S_PREV, type: Bool, section: STATIC}, {name: S_SELOK, type: Bool, section: STATIC}, {name: TAP, type: Bool, section: STATIC}, {name: TMS_HALT, type: Bool, section: STATIC}, {name: TOP, type: Bool, section: STATIC}, {name: T_NEXT, type: Bool, section: STATIC}, {name: T_PERM, type: Bool, section: STATIC}, {name: T_PREV, type: Bool, section: STATIC}, {name: T_PUSH, type: Bool, section: STATIC}]}, {name: MOP_EDGE, type: G7_MOPPlus_V6, section: STATIC, members: [{name: ACK, type: Bool, section: STATIC}, {name: ACKREQ, type: Bool, section: STATIC}, {name: ACK_S, type: Bool, section: STATIC}, {name: AUTO, type: Bool, section: STATIC}, {name: HALT, type: Bool, section: STATIC}, {name: ILP_MAN, type: Bool, section: STATIC}, {name: IL_PERM, type: Bool, section: STATIC}, {name: INIT, type: Bool, section: STATIC}, {name: LMODE, type: Bool, section: STATIC}, {name: LOCK, type: Bool, section: STATIC}, {name: MAN, type: Bool, section: STATIC}, {name: 'OFF', type: Bool, section: STATIC}, {name: OPS_ZERO, type: Bool, section: STATIC}, {name: REG, type: Bool, section: STATIC}, {name: REG_S, type: Bool, section: STATIC}, {name: RESET_CRIT, type: Bool, section: STATIC}, {name: SACT_DISP, type: Bool, section: STATIC}, {name: SALL_DISP, type: Bool, section: STATIC}, {name: SEF_DISP, type: Bool, section: STATIC}, {name: SSKIP, type: Bool, section: STATIC}, {name: SUP, type: Bool, section: STATIC}, {name: S_NEXT, type: Bool, section: STATIC}, {name: S_OFF, type: Bool, section: STATIC}, {name: S_ON, type: Bool, section: STATIC}, {name: S_PREV, type: Bool, section: STATIC}, {name: S_SELOK, type: Bool, section: STATIC}, {name: TAP, type: Bool, section: STATIC}, {name: TMS_HALT, type: Bool, section: STATIC}, {name: TOP, type: Bool, section: STATIC}, {name: T_NEXT, type: Bool, section: STATIC}, {name: T_PERM, type: Bool, section: STATIC}, {name: T_PREV, type: Bool, section: STATIC}, {name: T_PUSH, type: Bool, section: STATIC}]}, {name: OFFSETS, type: G7_OffsetsPlus_V6, section: STATIC, members: [{name: ASSB_OFFSET, type: UInt, section: STATIC, start: '38'}, {name: ASSJ_OFFSET, type: UInt, section: STATIC, start: '32'}, {name: ATAB_OFFSET, type: UInt, section: STATIC, start: '14'}, {name: ATAJ_OFFSET, type: UInt, section: STATIC, start: '8'}, {name: LSTT_OFFSET, type: UInt, section: STATIC, start: '2'}, {name: NSTT_OFFSET, type: UInt, section: STATIC, start: '26'}, {name: NTTS_OFFSET, type: UInt, section: STATIC, start: '50'}, {name: PSTT_OFFSET, type: UInt, section: STATIC, start: '20'}, {name: PTTS_OFFSET, type: UInt, section: STATIC, start: '44'}, {name: S00X_OFFSET, type: UInt, section: STATIC, start: '69'}, {name: S0X_OFFSET, type: UInt, section: STATIC, start: '91'}, {name: S1X_OFFSET, type: UInt, section: STATIC, start: '98'}, {name: SAX_OFFSET, type: UInt, section: STATIC, start: '75'}, {name: SERRX_OFFSET, type: UInt, section: STATIC, start: '77'}, {name: SINI_OFFSET, type: UInt, section: STATIC}, {name: SMX_OFFSET, type: UInt, section: STATIC, start: '84'}, {name: SOFFX_OFFSET, type: UInt, section: STATIC, start: '71'}, {name: SONX_OFFSET, type: UInt, section: STATIC, start: '73'}, {name: SWITCH_OFFSET, type: UInt, section: STATIC, start: '62'}, {name: SW_SQTS_OFFSET, type: UInt, section: STATIC, start: '56'}, {name: TSX_OFFSET, type: UInt, section: STATIC, start: '67'}, {name: TTX_OFFSET, type: UInt, section: STATIC, start: '65'}, {name: TVX_OFFSET, type: UInt, section: STATIC, start: '63'}]}, {name: POST_CNT, type: USInt, section: STATIC, start: '1'}, {name: PRE_CNT, type: USInt, section: STATIC, start: '1'}, {name: SQ_CNT, type: USInt, section: STATIC, start: '1'}, {name: SQ_FLAGS, type: G7_SQFlagsPlus_V6, section: STATIC, members: [{name: AS_MSG, type: Bool, section: STATIC, start: 'true'}, {name: CYC_OP, type: Bool, section: STATIC}, {name: ERROR, type: Bool, section: STATIC}, {name: ERR_FLT, type: Bool, section: STATIC}, {name: FAULT, type: Bool, section: STATIC}, {name: NF_OFL, type: Bool, section: STATIC}, {name: NO_SNO, type: Bool, section: STATIC}, {name: NO_SWI, type: Bool, section: STATIC}, {name: RT_FAIL, type: Bool, section: STATIC}, {name: SA_BUSY, type: Bool, section: STATIC}, {name: SA_OFL, type: Bool, section: STATIC}, {name: SQ_BUSY, type: Bool, section: STATIC}, {name: TV_OFL, type: Bool, section: STATIC}]}, {name: SQ_PART_CNT, type: USInt, section: STATIC, start: '1'}, {name: SUP_CNT, type: USInt, section: STATIC}, {name: S_CNT, type: USInt, section: STATIC, start: '6'}, {name: S_DISPIDX, type: USInt, section: STATIC, start: '255'}, {name: S_DISPLAY, type: Int, section: STATIC}, {name: S_SEL_OLD, type: Int, section: STATIC}, {name: THRESHOLD_SUP, type: USInt, section: STATIC}, {name: THRESHOLD_WARN, type: USInt, section: STATIC}, {name: TIME_DELTA, type: Time, section: STATIC}, {name: T_CNT, type: USInt, section: STATIC, start: '6'}, {name: T_DISPIDX, type: USInt, section: STATIC, start: '255'}, {name: VERSION, type: 'String[10]', section: STATIC, start: '''V6.0'''}]}
- {name: Reset, type: G7_StepPlus_V6, section: STATIC, retain: false, comment: {en-US: Step structure}, accessible: false, visible: false, writable: false, members: [{name: A1, type: Bool, section: STATIC}, {name: AA, type: Bool, section: STATIC}, {name: CRIT_LOC, type: DWord, section: STATIC}, {name: CRIT_LOC_ERR, type: DWord, section: STATIC}, {name: H_IL_ERR, type: Byte, section: STATIC}, {name: H_SV_FLT, type: Byte, section: STATIC, start: 16#04}, {name: L0, type: Bool, section: STATIC}, {name: L1, type: Bool, section: STATIC}, {name: LA, type: Bool, section: STATIC}, {name: LS, type: Bool, section: STATIC}, {name: R1, type: Bool, section: STATIC}, {name: RA, type: Bool, section: STATIC}, {name: S0, type: Bool, section: STATIC}, {name: S1, type: Bool, section: STATIC}, {name: SM, type: Bool, section: STATIC}, {name: SNO, type: Int, section: STATIC, start: '6'}, {name: SS, type: Bool, section: STATIC}, {name: T, type: Time, section: STATIC}, {name: T_MAX, type: Time, section: STATIC, start: T#10S}, {name: T_WARN, type: Time, section: STATIC, start: T#7S}, {name: U, type: Time, section: STATIC}, {name: V0, type: Bool, section: STATIC}, {name: V1, type: Bool, section: STATIC}, {name: VA, type: Bool, section: STATIC}, {name: VS, type: Bool, section: STATIC}, {name: X, type: Bool, section: STATIC}]}
- {name: Start step 1, type: G7_TransitionPlus_V6, section: STATIC, retain: false, comment: {en-US: Transition structure}, accessible: false, visible: false, writable: false, members: [{name: CRIT, type: DWord, section: STATIC}, {name: CRIT_FLT, type: DWord, section: STATIC}, {name: CRIT_OLD, type: DWord, section: STATIC}, {name: TNO, type: Int, section: STATIC, start: '1'}, {name: TS, type: Bool, section: STATIC}, {name: TT, type: Bool, section: STATIC}, {name: TV, type: Bool, section: STATIC}]}
- {name: Start step 2, type: G7_TransitionPlus_V6, section: STATIC, retain: false, comment: {en-US: Transition structure}, accessible: false, visible: false, writable: false, members: [{name: CRIT, type: DWord, section: STATIC}, {name: CRIT_FLT, type: DWord, section: STATIC}, {name: CRIT_OLD, type: DWord, section: STATIC}, {name: TNO, type: Int, section: STATIC, start: '2'}, {name: TS, type: Bool, section: STATIC}, {name: TT, type: Bool, section: STATIC}, {name: TV, type: Bool, section: STATIC}]}
- {name: Start step 3, type: G7_TransitionPlus_V6, section: STATIC, retain: false, comment: {en-US: Transition structure}, accessible: false, visible: false, writable: false, members: [{name: CRIT, type: DWord, section: STATIC}, {name: CRIT_FLT, type: DWord, section: STATIC}, {name: CRIT_OLD, type: DWord, section: STATIC}, {name: TNO, type: Int, section: STATIC, start: '3'}, {name: TS, type: Bool, section: STATIC}, {name: TT, type: Bool, section: STATIC}, {name: TV, type: Bool, section: STATIC}]}
- {name: Start step 4, type: G7_TransitionPlus_V6, section: STATIC, retain: false, comment: {en-US: Transition structure}, accessible: false, visible: false, writable: false, members: [{name: CRIT, type: DWord, section: STATIC}, {name: CRIT_FLT, type: DWord, section: STATIC}, {name: CRIT_OLD, type: DWord, section: STATIC}, {name: TNO, type: Int, section: STATIC, start: '4'}, {name: TS, type: Bool, section: STATIC}, {name: TT, type: Bool, section: STATIC}, {name: TV, type: Bool, section: STATIC}]}
- {name: 'Step1: pre-rinse', type: G7_StepPlus_V6, section: STATIC, retain: false, comment: {en-US: Step structure}, accessible: false, visible: false, writable: false, members: [{name: A1, type: Bool, section: STATIC}, {name: AA, type: Bool, section: STATIC}, {name: CRIT_LOC, type: DWord, section: STATIC}, {name: CRIT_LOC_ERR, type: DWord, section: STATIC}, {name: H_IL_ERR, type: Byte, section: STATIC}, {name: H_SV_FLT, type: Byte, section: STATIC, start: 16#04}, {name: L0, type: Bool, section: STATIC}, {name: L1, type: Bool, section: STATIC}, {name: LA, type: Bool, section: STATIC}, {name: LS, type: Bool, section: STATIC}, {name: R1, type: Bool, section: STATIC}, {name: RA, type: Bool, section: STATIC}, {name: S0, type: Bool, section: STATIC}, {name: S1, type: Bool, section: STATIC}, {name: SM, type: Bool, section: STATIC}, {name: SNO, type: Int, section: STATIC, start: '2'}, {name: SS, type: Bool, section: STATIC}, {name: T, type: Time, section: STATIC}, {name: T_MAX, type: Time, section: STATIC, start: T#10S}, {name: T_WARN, type: Time, section: STATIC, start: T#7S}, {name: U, type: Time, section: STATIC}, {name: V0, type: Bool, section: STATIC}, {name: V1, type: Bool, section: STATIC}, {name: VA, type: Bool, section: STATIC}, {name: VS, type: Bool, section: STATIC}, {name: X, type: Bool, section: STATIC}]}
- {name: 'Step2: alkali-wash', type: G7_StepPlus_V6, section: STATIC, retain: false, comment: {en-US: Step structure}, accessible: false, visible: false, writable: false, members: [{name: A1, type: Bool, section: STATIC}, {name: AA, type: Bool, section: STATIC}, {name: CRIT_LOC, type: DWord, section: STATIC}, {name: CRIT_LOC_ERR, type: DWord, section: STATIC}, {name: H_IL_ERR, type: Byte, section: STATIC}, {name: H_SV_FLT, type: Byte, section: STATIC, start: 16#04}, {name: L0, type: Bool, section: STATIC}, {name: L1, type: Bool, section: STATIC}, {name: LA, type: Bool, section: STATIC}, {name: LS, type: Bool, section: STATIC}, {name: R1, type: Bool, section: STATIC}, {name: RA, type: Bool, section: STATIC}, {name: S0, type: Bool, section: STATIC}, {name: S1, type: Bool, section: STATIC}, {name: SM, type: Bool, section: STATIC}, {name: SNO, type: Int, section: STATIC, start: '3'}, {name: SS, type: Bool, section: STATIC}, {name: T, type: Time, section: STATIC}, {name: T_MAX, type: Time, section: STATIC, start: T#10S}, {name: T_WARN, type: Time, section: STATIC, start: T#7S}, {name: U, type: Time, section: STATIC}, {name: V0, type: Bool, section: STATIC}, {name: V1, type: Bool, section: STATIC}, {name: VA, type: Bool, section: STATIC}, {name: VS, type: Bool, section: STATIC}, {name: X, type: Bool, section: STATIC}]}
- {name: 'Step3: acid-wash', type: G7_StepPlus_V6, section: STATIC, retain: false, comment: {en-US: Step structure}, accessible: false, visible: false, writable: false, members: [{name: A1, type: Bool, section: STATIC}, {name: AA, type: Bool, section: STATIC}, {name: CRIT_LOC, type: DWord, section: STATIC}, {name: CRIT_LOC_ERR, type: DWord, section: STATIC}, {name: H_IL_ERR, type: Byte, section: STATIC}, {name: H_SV_FLT, type: Byte, section: STATIC, start: 16#04}, {name: L0, type: Bool, section: STATIC}, {name: L1, type: Bool, section: STATIC}, {name: LA, type: Bool, section: STATIC}, {name: LS, type: Bool, section: STATIC}, {name: R1, type: Bool, section: STATIC}, {name: RA, type: Bool, section: STATIC}, {name: S0, type: Bool, section: STATIC}, {name: S1, type: Bool, section: STATIC}, {name: SM, type: Bool, section: STATIC}, {name: SNO, type: Int, section: STATIC, start: '4'}, {name: SS, type: Bool, section: STATIC}, {name: T, type: Time, section: STATIC}, {name: T_MAX, type: Time, section: STATIC, start: T#10S}, {name: T_WARN, type: Time, section: STATIC, start: T#7S}, {name: U, type: Time, section: STATIC}, {name: V0, type: Bool, section: STATIC}, {name: V1, type: Bool, section: STATIC}, {name: VA, type: Bool, section: STATIC}, {name: VS, type: Bool, section: STATIC}, {name: X, type: Bool, section: STATIC}]}
- {name: 'Step4: final-rinse', type: G7_StepPlus_V6, section: STATIC, retain: false, comment: {en-US: Step structure}, accessible: false, visible: false, writable: false, members: [{name: A1, type: Bool, section: STATIC}, {name: AA, type: Bool, section: STATIC}, {name: CRIT_LOC, type: DWord, section: STATIC}, {name: CRIT_LOC_ERR, type: DWord, section: STATIC}, {name: H_IL_ERR, type: Byte, section: STATIC}, {name: H_SV_FLT, type: Byte, section: STATIC, start: 16#04}, {name: L0, type: Bool, section: STATIC}, {name: L1, type: Bool, section: STATIC}, {name: LA, type: Bool, section: STATIC}, {name: LS, type: Bool, section: STATIC}, {name: R1, type: Bool, section: STATIC}, {name: RA, type: Bool, section: STATIC}, {name: S0, type: Bool, section: STATIC}, {name: S1, type: Bool, section: STATIC}, {name: SM, type: Bool, section: STATIC}, {name: SNO, type: Int, section: STATIC, start: '5'}, {name: SS, type: Bool, section: STATIC}, {name: T, type: Time, section: STATIC}, {name: T_MAX, type: Time, section: STATIC, start: T#10S}, {name: T_WARN, type: Time, section: STATIC, start: T#7S}, {name: U, type: Time, section: STATIC}, {name: V0, type: Bool, section: STATIC}, {name: V1, type: Bool, section: STATIC}, {name: VA, type: Bool, section: STATIC}, {name: VS, type: Bool, section: STATIC}, {name: X, type: Bool, section: STATIC}]}
- {name: Trans8, type: G7_TransitionPlus_V6, section: STATIC, retain: false, comment: {en-US: Transition structure}, accessible: false, visible: false, writable: false, members: [{name: CRIT, type: DWord, section: STATIC}, {name: CRIT_FLT, type: DWord, section: STATIC}, {name: CRIT_OLD, type: DWord, section: STATIC}, {name: TNO, type: Int, section: STATIC, start: '8'}, {name: TS, type: Bool, section: STATIC}, {name: TT, type: Bool, section: STATIC}, {name: TV, type: Bool, section: STATIC}]}
- {name: statAbnomaly, type: Real, section: STATIC, retain: false, accessible: true, visible: true, writable: true}
- {name: statConcentration, type: Real, section: STATIC, retain: false, accessible: true, visible: true, writable: true}
- {name: statTemperature, type: Real, section: STATIC, retain: false, accessible: true, visible: true, writable: true}
- {name: tempRandomAbnomaly, type: Real, section: TEMP}
- {name: tempRandomFlowrate, type: Int, section: TEMP}
- {name: tempRet, type: Int, section: TEMP}
networks:
- {'no': 1, line_start: 471, line_end: 518}
---

# FB_5_CIP_Simulation_Graph

## Interface
| Section | Name | Type | Start | Comment |
|---|---|---|---|---|
| IN | ACK_EF | Bool | false | en-US: Acknowledge all errors and faults |
| IN | INIT_SQ | Bool | false | en-US: Set sequence to initial state |
| IN | OFF_SQ | Bool | false | en-US: Turn sequence off |
| IN | SW_AUTO | Bool | false | en-US: Automatic mode |
| IN | SW_MAN | Bool | false | en-US: Manual mode |
| IN | SW_TAP | Bool | false | en-US: Semiautomatic/switch with transition |
| IN | SW_TOP | Bool | false | en-US: Semiautomatic/ignore transition |
| IN | S_NEXT | Bool | false | en-US: Indicate next step in parameter S_NO |
| IN | S_OFF | Bool | false | en-US: Disable step indicated in S_NO |
| IN | S_ON | Bool | false | en-US: Activate step indicated in S_NO |
| IN | S_PREV | Bool | false | en-US: Output previous step in parameter S_NO |
| IN | S_SEL | Int | 0 | en-US: Select step to be output to S_NO |
| IN | T_PUSH | Bool | false | en-US: Enable transition to switch in semi automatic mode |
| OUT | AUTO_ON | Bool | false | en-US: Automatic mode is active |
| OUT | ERR_FLT | Bool | false | en-US: Interlock or supervision group error |
| OUT | MAN_ON | Bool | false | en-US: Manual mode is active |
| OUT | S_ACTIVE | Bool | false | en-US: Step indicated in S_NO is active |
| OUT | S_MORE | Bool | false | en-US: More steps are available and can be shown in S_NO |
| OUT | S_NO | Int | 0 | en-US: Step number |
| OUT | TAP_ON | Bool | false | en-US: Semiautomatic mode/step with transition enabled |
| OUT | TOP_ON | Bool | false | en-US: Semiautomatic mode/ignore transition enabled |
| IN_OUT | cip | "typeCIP" |  |  |
| IN_OUT | cip.cipActive | Bool |  |  |
| IN_OUT | cip.cipConcentration | Real |  |  |
| IN_OUT | cip.cipFlowrate | Real |  |  |
| IN_OUT | cip.cipId | Int |  |  |
| IN_OUT | cip.cipProcess | String |  |  |
| IN_OUT | cip.cipStartTime | Time_Of_Day |  |  |
| IN_OUT | cip.cipStep | String |  |  |
| IN_OUT | cip.cipStep1 | Bool |  |  |
| IN_OUT | cip.cipStep2 | Bool |  |  |
| IN_OUT | cip.cipStep3 | Bool |  |  |
| IN_OUT | cip.cipStep4 | Bool |  |  |
| IN_OUT | cip.cipTemperature | Real |  |  |
| IN_OUT | step1Active | Bool |  | en-US: Step 1 is active |
| IN_OUT | step2Active | Bool |  | en-US: Step 2 is active |
| IN_OUT | step3Active | Bool |  | en-US: Step 3 is active |
| IN_OUT | step4Active | Bool |  | en-US: Step 4 is active |
| IN_OUT | stepInitial | Bool |  | en-US: Initial step is active |
| STATIC | End | G7_TransitionPlus_V6 |  | en-US: Transition structure |
| STATIC | End.CRIT | DWord |  |  |
| STATIC | End.CRIT_FLT | DWord |  |  |
| STATIC | End.CRIT_OLD | DWord |  |  |
| STATIC | End.TNO | Int | 6 |  |
| STATIC | End.TS | Bool |  |  |
| STATIC | End.TT | Bool |  |  |
| STATIC | End.TV | Bool |  |  |
| STATIC | Initial step | G7_StepPlus_V6 |  | en-US: Step structure |
| STATIC | Initial step.A1 | Bool |  |  |
| STATIC | Initial step.AA | Bool |  |  |
| STATIC | Initial step.CRIT_LOC | DWord |  |  |
| STATIC | Initial step.CRIT_LOC_ERR | DWord |  |  |
| STATIC | Initial step.H_IL_ERR | Byte |  |  |
| STATIC | Initial step.H_SV_FLT | Byte | 16#04 |  |
| STATIC | Initial step.L0 | Bool |  |  |
| STATIC | Initial step.L1 | Bool |  |  |
| STATIC | Initial step.LA | Bool |  |  |
| STATIC | Initial step.LS | Bool |  |  |
| STATIC | Initial step.R1 | Bool |  |  |
| STATIC | Initial step.RA | Bool |  |  |
| STATIC | Initial step.S0 | Bool |  |  |
| STATIC | Initial step.S1 | Bool |  |  |
| STATIC | Initial step.SM | Bool |  |  |
| STATIC | Initial step.SNO | Int | 1 |  |
| STATIC | Initial step.SS | Bool |  |  |
| STATIC | Initial step.T | Time |  |  |
| STATIC | Initial step.T_MAX | Time | T#10S |  |
| STATIC | Initial step.T_WARN | Time | T#7S |  |
| STATIC | Initial step.U | Time |  |  |
| STATIC | Initial step.V0 | Bool |  |  |
| STATIC | Initial step.V1 | Bool |  |  |
| STATIC | Initial step.VA | Bool |  |  |
| STATIC | Initial step.VS | Bool |  |  |
| STATIC | Initial step.X | Bool |  |  |
| STATIC | RT_DATA | G7_RTDataPlus_V6 |  | en-US: Internal data area |
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
| STATIC | RT_DATA.MAX_TVAL | USInt | 1 |  |
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
| STATIC | RT_DATA.OFFSETS.ASSB_OFFSET | UInt | 38 |  |
| STATIC | RT_DATA.OFFSETS.ASSJ_OFFSET | UInt | 32 |  |
| STATIC | RT_DATA.OFFSETS.ATAB_OFFSET | UInt | 14 |  |
| STATIC | RT_DATA.OFFSETS.ATAJ_OFFSET | UInt | 8 |  |
| STATIC | RT_DATA.OFFSETS.LSTT_OFFSET | UInt | 2 |  |
| STATIC | RT_DATA.OFFSETS.NSTT_OFFSET | UInt | 26 |  |
| STATIC | RT_DATA.OFFSETS.NTTS_OFFSET | UInt | 50 |  |
| STATIC | RT_DATA.OFFSETS.PSTT_OFFSET | UInt | 20 |  |
| STATIC | RT_DATA.OFFSETS.PTTS_OFFSET | UInt | 44 |  |
| STATIC | RT_DATA.OFFSETS.S00X_OFFSET | UInt | 69 |  |
| STATIC | RT_DATA.OFFSETS.S0X_OFFSET | UInt | 91 |  |
| STATIC | RT_DATA.OFFSETS.S1X_OFFSET | UInt | 98 |  |
| STATIC | RT_DATA.OFFSETS.SAX_OFFSET | UInt | 75 |  |
| STATIC | RT_DATA.OFFSETS.SERRX_OFFSET | UInt | 77 |  |
| STATIC | RT_DATA.OFFSETS.SINI_OFFSET | UInt |  |  |
| STATIC | RT_DATA.OFFSETS.SMX_OFFSET | UInt | 84 |  |
| STATIC | RT_DATA.OFFSETS.SOFFX_OFFSET | UInt | 71 |  |
| STATIC | RT_DATA.OFFSETS.SONX_OFFSET | UInt | 73 |  |
| STATIC | RT_DATA.OFFSETS.SWITCH_OFFSET | UInt | 62 |  |
| STATIC | RT_DATA.OFFSETS.SW_SQTS_OFFSET | UInt | 56 |  |
| STATIC | RT_DATA.OFFSETS.TSX_OFFSET | UInt | 67 |  |
| STATIC | RT_DATA.OFFSETS.TTX_OFFSET | UInt | 65 |  |
| STATIC | RT_DATA.OFFSETS.TVX_OFFSET | UInt | 63 |  |
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
| STATIC | RT_DATA.SQ_PART_CNT | USInt | 1 |  |
| STATIC | RT_DATA.SUP_CNT | USInt |  |  |
| STATIC | RT_DATA.S_CNT | USInt | 6 |  |
| STATIC | RT_DATA.S_DISPIDX | USInt | 255 |  |
| STATIC | RT_DATA.S_DISPLAY | Int |  |  |
| STATIC | RT_DATA.S_SEL_OLD | Int |  |  |
| STATIC | RT_DATA.THRESHOLD_SUP | USInt |  |  |
| STATIC | RT_DATA.THRESHOLD_WARN | USInt |  |  |
| STATIC | RT_DATA.TIME_DELTA | Time |  |  |
| STATIC | RT_DATA.T_CNT | USInt | 6 |  |
| STATIC | RT_DATA.T_DISPIDX | USInt | 255 |  |
| STATIC | RT_DATA.VERSION | String[10] | 'V6.0' |  |
| STATIC | Reset | G7_StepPlus_V6 |  | en-US: Step structure |
| STATIC | Reset.A1 | Bool |  |  |
| STATIC | Reset.AA | Bool |  |  |
| STATIC | Reset.CRIT_LOC | DWord |  |  |
| STATIC | Reset.CRIT_LOC_ERR | DWord |  |  |
| STATIC | Reset.H_IL_ERR | Byte |  |  |
| STATIC | Reset.H_SV_FLT | Byte | 16#04 |  |
| STATIC | Reset.L0 | Bool |  |  |
| STATIC | Reset.L1 | Bool |  |  |
| STATIC | Reset.LA | Bool |  |  |
| STATIC | Reset.LS | Bool |  |  |
| STATIC | Reset.R1 | Bool |  |  |
| STATIC | Reset.RA | Bool |  |  |
| STATIC | Reset.S0 | Bool |  |  |
| STATIC | Reset.S1 | Bool |  |  |
| STATIC | Reset.SM | Bool |  |  |
| STATIC | Reset.SNO | Int | 6 |  |
| STATIC | Reset.SS | Bool |  |  |
| STATIC | Reset.T | Time |  |  |
| STATIC | Reset.T_MAX | Time | T#10S |  |
| STATIC | Reset.T_WARN | Time | T#7S |  |
| STATIC | Reset.U | Time |  |  |
| STATIC | Reset.V0 | Bool |  |  |
| STATIC | Reset.V1 | Bool |  |  |
| STATIC | Reset.VA | Bool |  |  |
| STATIC | Reset.VS | Bool |  |  |
| STATIC | Reset.X | Bool |  |  |
| STATIC | Start step 1 | G7_TransitionPlus_V6 |  | en-US: Transition structure |
| STATIC | Start step 1.CRIT | DWord |  |  |
| STATIC | Start step 1.CRIT_FLT | DWord |  |  |
| STATIC | Start step 1.CRIT_OLD | DWord |  |  |
| STATIC | Start step 1.TNO | Int | 1 |  |
| STATIC | Start step 1.TS | Bool |  |  |
| STATIC | Start step 1.TT | Bool |  |  |
| STATIC | Start step 1.TV | Bool |  |  |
| STATIC | Start step 2 | G7_TransitionPlus_V6 |  | en-US: Transition structure |
| STATIC | Start step 2.CRIT | DWord |  |  |
| STATIC | Start step 2.CRIT_FLT | DWord |  |  |
| STATIC | Start step 2.CRIT_OLD | DWord |  |  |
| STATIC | Start step 2.TNO | Int | 2 |  |
| STATIC | Start step 2.TS | Bool |  |  |
| STATIC | Start step 2.TT | Bool |  |  |
| STATIC | Start step 2.TV | Bool |  |  |
| STATIC | Start step 3 | G7_TransitionPlus_V6 |  | en-US: Transition structure |
| STATIC | Start step 3.CRIT | DWord |  |  |
| STATIC | Start step 3.CRIT_FLT | DWord |  |  |
| STATIC | Start step 3.CRIT_OLD | DWord |  |  |
| STATIC | Start step 3.TNO | Int | 3 |  |
| STATIC | Start step 3.TS | Bool |  |  |
| STATIC | Start step 3.TT | Bool |  |  |
| STATIC | Start step 3.TV | Bool |  |  |
| STATIC | Start step 4 | G7_TransitionPlus_V6 |  | en-US: Transition structure |
| STATIC | Start step 4.CRIT | DWord |  |  |
| STATIC | Start step 4.CRIT_FLT | DWord |  |  |
| STATIC | Start step 4.CRIT_OLD | DWord |  |  |
| STATIC | Start step 4.TNO | Int | 4 |  |
| STATIC | Start step 4.TS | Bool |  |  |
| STATIC | Start step 4.TT | Bool |  |  |
| STATIC | Start step 4.TV | Bool |  |  |
| STATIC | Step1: pre-rinse | G7_StepPlus_V6 |  | en-US: Step structure |
| STATIC | Step1: pre-rinse.A1 | Bool |  |  |
| STATIC | Step1: pre-rinse.AA | Bool |  |  |
| STATIC | Step1: pre-rinse.CRIT_LOC | DWord |  |  |
| STATIC | Step1: pre-rinse.CRIT_LOC_ERR | DWord |  |  |
| STATIC | Step1: pre-rinse.H_IL_ERR | Byte |  |  |
| STATIC | Step1: pre-rinse.H_SV_FLT | Byte | 16#04 |  |
| STATIC | Step1: pre-rinse.L0 | Bool |  |  |
| STATIC | Step1: pre-rinse.L1 | Bool |  |  |
| STATIC | Step1: pre-rinse.LA | Bool |  |  |
| STATIC | Step1: pre-rinse.LS | Bool |  |  |
| STATIC | Step1: pre-rinse.R1 | Bool |  |  |
| STATIC | Step1: pre-rinse.RA | Bool |  |  |
| STATIC | Step1: pre-rinse.S0 | Bool |  |  |
| STATIC | Step1: pre-rinse.S1 | Bool |  |  |
| STATIC | Step1: pre-rinse.SM | Bool |  |  |
| STATIC | Step1: pre-rinse.SNO | Int | 2 |  |
| STATIC | Step1: pre-rinse.SS | Bool |  |  |
| STATIC | Step1: pre-rinse.T | Time |  |  |
| STATIC | Step1: pre-rinse.T_MAX | Time | T#10S |  |
| STATIC | Step1: pre-rinse.T_WARN | Time | T#7S |  |
| STATIC | Step1: pre-rinse.U | Time |  |  |
| STATIC | Step1: pre-rinse.V0 | Bool |  |  |
| STATIC | Step1: pre-rinse.V1 | Bool |  |  |
| STATIC | Step1: pre-rinse.VA | Bool |  |  |
| STATIC | Step1: pre-rinse.VS | Bool |  |  |
| STATIC | Step1: pre-rinse.X | Bool |  |  |
| STATIC | Step2: alkali-wash | G7_StepPlus_V6 |  | en-US: Step structure |
| STATIC | Step2: alkali-wash.A1 | Bool |  |  |
| STATIC | Step2: alkali-wash.AA | Bool |  |  |
| STATIC | Step2: alkali-wash.CRIT_LOC | DWord |  |  |
| STATIC | Step2: alkali-wash.CRIT_LOC_ERR | DWord |  |  |
| STATIC | Step2: alkali-wash.H_IL_ERR | Byte |  |  |
| STATIC | Step2: alkali-wash.H_SV_FLT | Byte | 16#04 |  |
| STATIC | Step2: alkali-wash.L0 | Bool |  |  |
| STATIC | Step2: alkali-wash.L1 | Bool |  |  |
| STATIC | Step2: alkali-wash.LA | Bool |  |  |
| STATIC | Step2: alkali-wash.LS | Bool |  |  |
| STATIC | Step2: alkali-wash.R1 | Bool |  |  |
| STATIC | Step2: alkali-wash.RA | Bool |  |  |
| STATIC | Step2: alkali-wash.S0 | Bool |  |  |
| STATIC | Step2: alkali-wash.S1 | Bool |  |  |
| STATIC | Step2: alkali-wash.SM | Bool |  |  |
| STATIC | Step2: alkali-wash.SNO | Int | 3 |  |
| STATIC | Step2: alkali-wash.SS | Bool |  |  |
| STATIC | Step2: alkali-wash.T | Time |  |  |
| STATIC | Step2: alkali-wash.T_MAX | Time | T#10S |  |
| STATIC | Step2: alkali-wash.T_WARN | Time | T#7S |  |
| STATIC | Step2: alkali-wash.U | Time |  |  |
| STATIC | Step2: alkali-wash.V0 | Bool |  |  |
| STATIC | Step2: alkali-wash.V1 | Bool |  |  |
| STATIC | Step2: alkali-wash.VA | Bool |  |  |
| STATIC | Step2: alkali-wash.VS | Bool |  |  |
| STATIC | Step2: alkali-wash.X | Bool |  |  |
| STATIC | Step3: acid-wash | G7_StepPlus_V6 |  | en-US: Step structure |
| STATIC | Step3: acid-wash.A1 | Bool |  |  |
| STATIC | Step3: acid-wash.AA | Bool |  |  |
| STATIC | Step3: acid-wash.CRIT_LOC | DWord |  |  |
| STATIC | Step3: acid-wash.CRIT_LOC_ERR | DWord |  |  |
| STATIC | Step3: acid-wash.H_IL_ERR | Byte |  |  |
| STATIC | Step3: acid-wash.H_SV_FLT | Byte | 16#04 |  |
| STATIC | Step3: acid-wash.L0 | Bool |  |  |
| STATIC | Step3: acid-wash.L1 | Bool |  |  |
| STATIC | Step3: acid-wash.LA | Bool |  |  |
| STATIC | Step3: acid-wash.LS | Bool |  |  |
| STATIC | Step3: acid-wash.R1 | Bool |  |  |
| STATIC | Step3: acid-wash.RA | Bool |  |  |
| STATIC | Step3: acid-wash.S0 | Bool |  |  |
| STATIC | Step3: acid-wash.S1 | Bool |  |  |
| STATIC | Step3: acid-wash.SM | Bool |  |  |
| STATIC | Step3: acid-wash.SNO | Int | 4 |  |
| STATIC | Step3: acid-wash.SS | Bool |  |  |
| STATIC | Step3: acid-wash.T | Time |  |  |
| STATIC | Step3: acid-wash.T_MAX | Time | T#10S |  |
| STATIC | Step3: acid-wash.T_WARN | Time | T#7S |  |
| STATIC | Step3: acid-wash.U | Time |  |  |
| STATIC | Step3: acid-wash.V0 | Bool |  |  |
| STATIC | Step3: acid-wash.V1 | Bool |  |  |
| STATIC | Step3: acid-wash.VA | Bool |  |  |
| STATIC | Step3: acid-wash.VS | Bool |  |  |
| STATIC | Step3: acid-wash.X | Bool |  |  |
| STATIC | Step4: final-rinse | G7_StepPlus_V6 |  | en-US: Step structure |
| STATIC | Step4: final-rinse.A1 | Bool |  |  |
| STATIC | Step4: final-rinse.AA | Bool |  |  |
| STATIC | Step4: final-rinse.CRIT_LOC | DWord |  |  |
| STATIC | Step4: final-rinse.CRIT_LOC_ERR | DWord |  |  |
| STATIC | Step4: final-rinse.H_IL_ERR | Byte |  |  |
| STATIC | Step4: final-rinse.H_SV_FLT | Byte | 16#04 |  |
| STATIC | Step4: final-rinse.L0 | Bool |  |  |
| STATIC | Step4: final-rinse.L1 | Bool |  |  |
| STATIC | Step4: final-rinse.LA | Bool |  |  |
| STATIC | Step4: final-rinse.LS | Bool |  |  |
| STATIC | Step4: final-rinse.R1 | Bool |  |  |
| STATIC | Step4: final-rinse.RA | Bool |  |  |
| STATIC | Step4: final-rinse.S0 | Bool |  |  |
| STATIC | Step4: final-rinse.S1 | Bool |  |  |
| STATIC | Step4: final-rinse.SM | Bool |  |  |
| STATIC | Step4: final-rinse.SNO | Int | 5 |  |
| STATIC | Step4: final-rinse.SS | Bool |  |  |
| STATIC | Step4: final-rinse.T | Time |  |  |
| STATIC | Step4: final-rinse.T_MAX | Time | T#10S |  |
| STATIC | Step4: final-rinse.T_WARN | Time | T#7S |  |
| STATIC | Step4: final-rinse.U | Time |  |  |
| STATIC | Step4: final-rinse.V0 | Bool |  |  |
| STATIC | Step4: final-rinse.V1 | Bool |  |  |
| STATIC | Step4: final-rinse.VA | Bool |  |  |
| STATIC | Step4: final-rinse.VS | Bool |  |  |
| STATIC | Step4: final-rinse.X | Bool |  |  |
| STATIC | Trans8 | G7_TransitionPlus_V6 |  | en-US: Transition structure |
| STATIC | Trans8.CRIT | DWord |  |  |
| STATIC | Trans8.CRIT_FLT | DWord |  |  |
| STATIC | Trans8.CRIT_OLD | DWord |  |  |
| STATIC | Trans8.TNO | Int | 8 |  |
| STATIC | Trans8.TS | Bool |  |  |
| STATIC | Trans8.TT | Bool |  |  |
| STATIC | Trans8.TV | Bool |  |  |
| STATIC | statAbnomaly | Real |  |  |
| STATIC | statConcentration | Real |  |  |
| STATIC | statTemperature | Real |  |  |
| TEMP | tempRandomAbnomaly | Real |  |  |
| TEMP | tempRandomFlowrate | Int |  |  |
| TEMP | tempRet | Int |  |  |

## NW 1

```ntn
INITIAL STEP "Initial step";
  ACTION N { #statTemperature := 0 }
  ACTION N { #statConcentration := 0 }
STEP "Step1: pre-rinse";
  ACTION N { #statTemperature := #statTemperature + 1.0E-08 }
  ACTION N { #cip.cipTemperature := #cip.cipTemperature + #statTemperature }
  ACTION N { #cip.cipTemperature := #cip.cipTemperature * #statAbnomaly }
  ACTION N { #cip.cipConcentration := 1.0E-10 }
  ACTION N { CALL "FC_1_Random_Number" (Min :=400 Max := 599 RandomNumber => #tempRandomFlowrate ) }
  ACTION N { (* Simulate random abnomalies *) }
  ACTION N { #cip.cipFlowrate := #tempRandomFlowrate * #statAbnomaly }
STEP "Step2: alkali-wash";
  ACTION N { #statTemperature := #statTemperature + 8.0E-09 }
  ACTION N { #cip.cipTemperature := #cip.cipTemperature + #statTemperature }
  ACTION N { #cip.cipTemperature := #cip.cipTemperature * #statAbnomaly }
  ACTION N { #statConcentration := #statConcentration + 5.0E-07 }
  ACTION N { #cip.cipConcentration := #cip.cipConcentration + #statConcentration }
  ACTION N { CALL "FC_1_Random_Number" (Min :=1013 Max := 1049 RandomNumber => #tempRandomFlowrate ) }
  ACTION N { (* Simulate random abnomalies *) #cip.cipFlowrate := #tempRandomFlowrate * #statAbnomaly }
STEP "Step3: acid-wash";
  ACTION N { #statTemperature := #statTemperature + 1.0E-07 }
  ACTION N { #cip.cipTemperature := #cip.cipTemperature + #statTemperature }
  ACTION N { #cip.cipTemperature := #cip.cipTemperature * #statAbnomaly }
  ACTION N { #statConcentration := #statConcentration + 1.0E-07 }
  ACTION N { #cip.cipConcentration := #cip.cipConcentration + #statConcentration }
  ACTION N { CALL "FC_1_Random_Number" (Min :=710 Max := 799 RandomNumber => #tempRandomFlowrate ) }
  ACTION N { (* Simulate random abnomalies *) #cip.cipFlowrate := #tempRandomFlowrate * #statAbnomaly }
STEP "Step4: final-rinse";
  ACTION N { #statTemperature := #statTemperature + 0.0001 }
  ACTION N { #cip.cipTemperature := #cip.cipTemperature + #statTemperature }
  ACTION N { #cip.cipTemperature := #cip.cipTemperature * #statAbnomaly }
  ACTION N { #statConcentration := #statConcentration + 1.0E-06 }
  ACTION N { #cip.cipConcentration := #cip.cipConcentration + #statConcentration }
  ACTION N { CALL "FC_1_Random_Number" (Min :=1500 Max := 1588 RandomNumber => #tempRandomFlowrate ) }
  ACTION N { #cip.cipFlowrate := #tempRandomFlowrate * #statAbnomaly }
STEP Reset;
  ACTION N { #statConcentration := 0.0 }
  ACTION N { #statTemperature := 0.0 }
TRANSITION "Initial step" -> "Step1: pre-rinse" WHEN #cip.cipStep1; // Start step 1
TRANSITION "Step1: pre-rinse" -> "Step2: alkali-wash" WHEN #cip.cipStep2; // Start step 2
TRANSITION "Step2: alkali-wash" -> "Step3: acid-wash" WHEN #cip.cipStep3; // Start step 3
TRANSITION "Step3: acid-wash" -> "Step4: final-rinse" WHEN #cip.cipStep4; // Start step 4
TRANSITION "Step4: final-rinse" -> Reset WHEN NOT #cip.cipActive; // End
TRANSITION Reset -> END WHEN TRUE; // Trans8
```
