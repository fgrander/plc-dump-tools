---
name: S7-Programm(2)/BSEND
kind: FB
number: 12
language: none
original_language: STL
protected: true
parse_quality: full
folder: S7-Programm(2)
attributes:
  address: FB 12
  author: SIMATIC
  family: CPU_300
  version: '1.2'
path_prefix: '"S7-Programm(2)/BSEND"'
variable_scope: fb_interface
interface:
- {name: ID, type: WORD, section: IN, start: W#16#0}
- {name: R, type: BOOL, section: IN, start: 'False'}
- {name: REQ, type: BOOL, section: IN, start: 'False'}
- {name: R_ID, type: DWORD, section: IN, start: DW#16#0}
- {name: DONE, type: BOOL, section: OUT, start: 'False'}
- {name: ERROR, type: BOOL, section: OUT, start: 'False'}
- {name: STATUS, type: WORD, section: OUT, start: W#16#0}
- {name: LEN, type: WORD, section: IN_OUT, start: W#16#0}
- {name: SD_1, type: ANY, section: IN_OUT}
- {name: BUFFER, type: 'ARRAY [0..119] OF WORD', section: STATIC}
- {name: DS200_BUSY, type: BOOL, section: STATIC, start: 'False'}
- {name: DS_NR, type: BYTE, section: STATIC, start: B#16#0, comment: {de: ' Datensatznummer, SFC Input Parameter'}}
- {name: FB_KENNUNG, type: BYTE, section: STATIC, start: B#16#F1, comment: {de: ' Ab hier STAT für Weiche'}}
- {name: FB_ZUSTAND, type: BYTE, section: STATIC, start: B#16#0, comment: {de: ' FB ZUSTAND MERKERBYTE//  INIT                    0   INIT//  OCRQ'}}
- {name: FC_DATA_LEN, type: WORD, section: STATIC, start: W#16#0, comment: {de: ' Vom Anwender projektrierte Transfer Laenge'}}
- {name: HS_REQ_BYTE, type: STRUCT, section: STATIC, members: [{name: dir, type: BOOL, start: 'False'}, {name: nls, type: BOOL, start: 'False'}, {name: nva, type: BOOL, start: 'False'}, {name: ofs, type: BOOL, start: 'False'}, {name: res, type: BOOL, start: 'False'}, {name: rii, type: BOOL, start: 'False'}, {name: rlo, type: BOOL, start: 'False'}, {name: roc, type: BOOL, start: 'False'}]}
- {name: HS_RESP_BYTE, type: STRUCT, section: STATIC, members: [{name: ads, type: BOOL, start: 'False'}, {name: aii, type: BOOL, start: 'False'}, {name: aoc, type: BOOL, start: 'False'}, {name: cnr, type: BOOL, start: 'False'}, {name: rs1, type: BOOL, start: 'False'}, {name: rs2, type: BOOL, start: 'False'}, {name: sns, type: BOOL, start: 'False'}, {name: sqc, type: BOOL, start: 'False'}]}
- {name: HS_RESP_DSNR, type: BYTE, section: STATIC, start: B#16#0}
- {name: HS_RESP_OFFSET, type: WORD, section: STATIC, start: W#16#0, comment: {de: ' SD_1 ANY Beschreibung'}}
- {name: ID_CLOSE, type: WORD, section: STATIC, start: W#16#0}
- {name: ID_SAVE, type: WORD, section: STATIC, start: W#16#0}
- {name: KANAL_PROBLEM, type: BOOL, section: STATIC, start: 'False'}
- {name: KOMM_PROBLEM, type: BOOL, section: STATIC, start: 'False'}
- {name: LADDR, type: WORD, section: STATIC, start: W#16#0}
- {name: LADDR_PTR, type: DWORD, section: STATIC, start: DW#16#0}
- {name: LEN_SAVE, type: WORD, section: STATIC, start: W#16#0}
- {name: MAX_DATA_LEN, type: WORD, section: STATIC, start: W#16#0}
- {name: MAX_PUFF_LEN_SAVE, type: WORD, section: STATIC, start: W#16#0, comment: {de: ' ZEIT ZAEHLER BOOL'}}
- {name: PARAM_OFFSET, type: BYTE, section: STATIC, start: B#16#0, comment: {de: ' MAX PUFFER LAENGE BACKUP'}}
- {name: REASON_FOR_CLOSE, type: BYTE, section: STATIC, start: B#16#0}
- {name: RECV_STARTED, type: BOOL, section: STATIC, start: 'False'}
- {name: REQ_SAVE, type: BOOL, section: STATIC, start: 'False'}
- {name: RESERVE, type: BYTE, section: STATIC, start: B#16#0}
- {name: RESET_EXECUTED, type: BOOL, section: STATIC, start: 'False'}
- {name: RESET_REQUEST, type: BOOL, section: STATIC, start: 'False'}
- {name: R_ID_SAVE, type: DWORD, section: STATIC, start: DW#16#0}
- {name: R_SAVE, type: BOOL, section: STATIC, start: 'False'}
- {name: SD_1_COUNT, type: WORD, section: STATIC, start: W#16#0}
- {name: SD_1_DBNUMMER, type: WORD, section: STATIC, start: W#16#0}
- {name: SD_1_DWORD6, type: DWORD, section: STATIC, start: DW#16#0}
- {name: SD_1_SAVE0, type: WORD, section: STATIC, start: W#16#0}
- {name: SD_1_SAVE2, type: WORD, section: STATIC, start: W#16#0}
- {name: SD_1_SAVE4, type: WORD, section: STATIC, start: W#16#0}
- {name: SD_1_SAVE6, type: WORD, section: STATIC, start: W#16#0}
- {name: SD_1_SAVE8, type: WORD, section: STATIC, start: W#16#0, comment: {de: ' HANDSHAKE VARIABLEN'}}
- {name: SD_1_TYP, type: BYTE, section: STATIC, start: B#16#0, comment: {de: ' SFC DS WRITE/READ VARIABLEN'}}
- {name: SD_1_WORD0, type: WORD, section: STATIC, start: W#16#0}
- {name: SEND_STARTED, type: BOOL, section: STATIC, start: 'False'}
- {name: SFB_AUFRUF, type: SFB12, section: STATIC}
- {name: SFC_PARAM, type: STRUCT, section: STATIC, members: [{name: DB_NUMMER, type: WORD, start: W#16#0}, {name: LEN, type: WORD, start: W#16#0}, {name: START, type: DWORD, start: DW#16#0}]}
- {name: SLEEP, type: BYTE, section: STATIC, start: B#16#0}
- {name: SLEEP_EXT, type: BYTE, section: STATIC, start: B#16#0}
- {name: TYP_BOOL, type: BOOL, section: STATIC, start: 'False'}
- {name: ZUSTAND_WEICHE, type: BYTE, section: STATIC, start: B#16#0, comment: {de: ' 1 = FB  2 = SFB'}}
- {name: ZUSTAND_WEICHE_1, type: BYTE, section: STATIC, start: B#16#0, comment: {de: ' 101 = FB  202 = SFB'}}
- {name: AR1_STORE, type: DWORD, section: TEMP, start: DW#16#0}
- {name: AUFTRAG_RESET_SAVE, type: BOOL, section: TEMP, start: 'False'}
- {name: BMOVE_CALLER, type: BYTE, section: TEMP, start: B#16#0}
- {name: BUFFER_START, type: DWORD, section: TEMP, start: DW#16#0}
- {name: BUSY_SFC51, type: BOOL, section: TEMP, start: 'False'}
- {name: BYTE_0_3_ANY, type: DWORD, section: TEMP, start: DW#16#0}
- {name: BYTE_4_7_ANY, type: DWORD, section: TEMP, start: DW#16#0}
- {name: BYTE_8_9_ANY, type: WORD, section: TEMP, start: W#16#0, comment: {de: '#######################################################'}}
- {name: DATA_LEN, type: WORD, section: TEMP, start: W#16#0}
- {name: DATA_START, type: DWORD, section: TEMP, start: DW#16#0}
- {name: DEST, type: ANY, section: TEMP}
- {name: DEST_COUNT, type: WORD, section: TEMP, start: W#16#0}
- {name: DEST_DB, type: WORD, section: TEMP, start: W#16#0}
- {name: DEST_OFFSET, type: DWORD, section: TEMP, start: DW#16#0, comment: {de: ' Hilfsmerker für LKPA  ( Länge kontrollieren und Parameter abspeichern )'}}
- {name: DIR, type: BOOL, section: TEMP, start: 'False'}
- {name: DR, type: STRUCT, section: TEMP, members: [{name: LOGADR, type: WORD, start: W#16#0}, {name: RACK_NR, type: BYTE, start: B#16#0}, {name: RES1, type: DWORD, start: DW#16#0}, {name: RES2, type: DWORD, start: DW#16#0}, {name: RES3, type: WORD, start: W#16#0}, {name: SLOT, type: BYTE, start: B#16#0}, {name: STATIONS_NR, type: BYTE, start: B#16#0}, {name: SUB_SLOT, type: BYTE, start: B#16#0}]}
- {name: DUMM, type: WORD, section: TEMP, start: W#16#0}
- {name: FIRST_SEG, type: BOOL, section: TEMP, start: 'False'}
- {name: IKDE_CALLER, type: BYTE, section: TEMP, start: B#16#0}
- {name: IKDE_ERGEBNIS, type: BYTE, section: TEMP, start: B#16#0, comment: {de: ' Hilfsmerker für AR1 Store'}}
- {name: KANAL_NUMMER, type: WORD, section: TEMP, start: W#16#0}
- {name: KOPF_LEN, type: WORD, section: TEMP, start: W#16#0}
- {name: KOPF_START, type: DWORD, section: TEMP, start: DW#16#0}
- {name: LADDR_WEICHE, type: WORD, section: TEMP, start: W#16#0, comment: {de: Ermittelte Baugruppenadresse aus SDB 200}}
- {name: LAST_SEG, type: BOOL, section: TEMP, start: 'False'}
- {name: LBUSY, type: BOOL, section: TEMP, start: 'False', comment: {de: ' SFC READ/WRITE Fertigmeldung'}}
- {name: LKPA_CALLER, type: BYTE, section: TEMP, start: B#16#0}
- {name: LKPA_ERGEBNIS, type: BYTE, section: TEMP, start: B#16#0, comment: {de: ' Hilfsmerker für IKDE  ( ID kontrollieren und DS errechnen )'}}
- {name: LOOP_COUNT, type: WORD, section: TEMP, start: W#16#0, comment: {de: ' NEUE TEMP VARIABLEN'}}
- {name: MAKRO_BREAK, type: BOOL, section: TEMP, start: 'False'}
- {name: MAKRO_CALLER, type: BYTE, section: TEMP, start: B#16#0}
- {name: MAKRO_ERGEBNIS, type: WORD, section: TEMP, start: W#16#0}
- {name: MAKRO_RESET, type: BOOL, section: TEMP, start: 'False'}
- {name: MAKRO_STARTED, type: BOOL, section: TEMP, start: 'False'}
- {name: NEW_REQ, type: BOOL, section: TEMP, start: 'False'}
- {name: NID, type: BOOL, section: TEMP, start: 'False'}
- {name: NORM_OFFSET, type: WORD, section: TEMP, start: W#16#0, comment: {de: Ab hier Temp Var für Weiche}}
- {name: NPAR, type: BOOL, section: TEMP, start: 'False'}
- {name: OBJ_NUMMER, type: WORD, section: TEMP, start: W#16#0}
- {name: OFFSETTING, type: BOOL, section: TEMP, start: 'False'}
- {name: POINTER1, type: DWORD, section: TEMP, start: DW#16#0}
- {name: RET_WT_STORE, type: INT, section: TEMP, start: '0', comment: {de: ' Dynamische Speicher fuer RET_VAL// (Output Par. des SFCs)// Hilfsmerker für Makr'}}
- {name: SD_1_SAVE, type: ANY, section: TEMP}
- {name: SD_1_SFB, type: ANY, section: TEMP}
- {name: SEG_LEN, type: WORD, section: TEMP, start: W#16#0, comment: {de: ' Hilfsmerker für Block Move'}}
- {name: SFC_DATA, type: ANY, section: TEMP}
- {name: SOURCE, type: ANY, section: TEMP}
- {name: SOURCE_COUNT, type: WORD, section: TEMP, start: W#16#0}
- {name: SOURCE_DB, type: WORD, section: TEMP, start: W#16#0}
- {name: SOURCE_OFFSET, type: DWORD, section: TEMP, start: DW#16#0}
- {name: SZL_HEADER, type: STRUCT, section: TEMP, members: [{name: LENGTHDR, type: WORD, start: W#16#0}, {name: NDR, type: WORD, start: W#16#0}]}
- {name: TEMP_Reserve, type: BYTE, section: TEMP, start: B#16#0, comment: {de: Ab hier Temp Var für Weiche}}
- {name: TOTAL_LEN, type: WORD, section: TEMP, start: W#16#0}
- {name: VOIDACTION, type: BOOL, section: TEMP, start: 'False'}
---

# S7-Programm(2)/BSEND

## Interface
| Section | Name | Type | Start | Comment |
|---|---|---|---|---|
| IN | ID | WORD | W#16#0 |  |
| IN | R | BOOL | False |  |
| IN | REQ | BOOL | False |  |
| IN | R_ID | DWORD | DW#16#0 |  |
| OUT | DONE | BOOL | False |  |
| OUT | ERROR | BOOL | False |  |
| OUT | STATUS | WORD | W#16#0 |  |
| IN_OUT | LEN | WORD | W#16#0 |  |
| IN_OUT | SD_1 | ANY |  |  |
| STATIC | BUFFER | ARRAY [0..119] OF WORD |  |  |
| STATIC | DS200_BUSY | BOOL | False |  |
| STATIC | DS_NR | BYTE | B#16#0 | de: Datensatznummer, SFC Input Parameter |
| STATIC | FB_KENNUNG | BYTE | B#16#F1 | de: Ab hier STAT für Weiche |
| STATIC | FB_ZUSTAND | BYTE | B#16#0 | de: FB ZUSTAND MERKERBYTE// INIT 0 INIT// OCRQ |
| STATIC | FC_DATA_LEN | WORD | W#16#0 | de: Vom Anwender projektrierte Transfer Laenge |
| STATIC | HS_REQ_BYTE | STRUCT |  |  |
|  | HS_REQ_BYTE.dir | BOOL | False |  |
|  | HS_REQ_BYTE.nls | BOOL | False |  |
|  | HS_REQ_BYTE.nva | BOOL | False |  |
|  | HS_REQ_BYTE.ofs | BOOL | False |  |
|  | HS_REQ_BYTE.res | BOOL | False |  |
|  | HS_REQ_BYTE.rii | BOOL | False |  |
|  | HS_REQ_BYTE.rlo | BOOL | False |  |
|  | HS_REQ_BYTE.roc | BOOL | False |  |
| STATIC | HS_RESP_BYTE | STRUCT |  |  |
|  | HS_RESP_BYTE.ads | BOOL | False |  |
|  | HS_RESP_BYTE.aii | BOOL | False |  |
|  | HS_RESP_BYTE.aoc | BOOL | False |  |
|  | HS_RESP_BYTE.cnr | BOOL | False |  |
|  | HS_RESP_BYTE.rs1 | BOOL | False |  |
|  | HS_RESP_BYTE.rs2 | BOOL | False |  |
|  | HS_RESP_BYTE.sns | BOOL | False |  |
|  | HS_RESP_BYTE.sqc | BOOL | False |  |
| STATIC | HS_RESP_DSNR | BYTE | B#16#0 |  |
| STATIC | HS_RESP_OFFSET | WORD | W#16#0 | de: SD_1 ANY Beschreibung |
| STATIC | ID_CLOSE | WORD | W#16#0 |  |
| STATIC | ID_SAVE | WORD | W#16#0 |  |
| STATIC | KANAL_PROBLEM | BOOL | False |  |
| STATIC | KOMM_PROBLEM | BOOL | False |  |
| STATIC | LADDR | WORD | W#16#0 |  |
| STATIC | LADDR_PTR | DWORD | DW#16#0 |  |
| STATIC | LEN_SAVE | WORD | W#16#0 |  |
| STATIC | MAX_DATA_LEN | WORD | W#16#0 |  |
| STATIC | MAX_PUFF_LEN_SAVE | WORD | W#16#0 | de: ZEIT ZAEHLER BOOL |
| STATIC | PARAM_OFFSET | BYTE | B#16#0 | de: MAX PUFFER LAENGE BACKUP |
| STATIC | REASON_FOR_CLOSE | BYTE | B#16#0 |  |
| STATIC | RECV_STARTED | BOOL | False |  |
| STATIC | REQ_SAVE | BOOL | False |  |
| STATIC | RESERVE | BYTE | B#16#0 |  |
| STATIC | RESET_EXECUTED | BOOL | False |  |
| STATIC | RESET_REQUEST | BOOL | False |  |
| STATIC | R_ID_SAVE | DWORD | DW#16#0 |  |
| STATIC | R_SAVE | BOOL | False |  |
| STATIC | SD_1_COUNT | WORD | W#16#0 |  |
| STATIC | SD_1_DBNUMMER | WORD | W#16#0 |  |
| STATIC | SD_1_DWORD6 | DWORD | DW#16#0 |  |
| STATIC | SD_1_SAVE0 | WORD | W#16#0 |  |
| STATIC | SD_1_SAVE2 | WORD | W#16#0 |  |
| STATIC | SD_1_SAVE4 | WORD | W#16#0 |  |
| STATIC | SD_1_SAVE6 | WORD | W#16#0 |  |
| STATIC | SD_1_SAVE8 | WORD | W#16#0 | de: HANDSHAKE VARIABLEN |
| STATIC | SD_1_TYP | BYTE | B#16#0 | de: SFC DS WRITE/READ VARIABLEN |
| STATIC | SD_1_WORD0 | WORD | W#16#0 |  |
| STATIC | SEND_STARTED | BOOL | False |  |
| STATIC | SFB_AUFRUF | SFB12 |  |  |
| STATIC | SFC_PARAM | STRUCT |  |  |
|  | SFC_PARAM.DB_NUMMER | WORD | W#16#0 |  |
|  | SFC_PARAM.LEN | WORD | W#16#0 |  |
|  | SFC_PARAM.START | DWORD | DW#16#0 |  |
| STATIC | SLEEP | BYTE | B#16#0 |  |
| STATIC | SLEEP_EXT | BYTE | B#16#0 |  |
| STATIC | TYP_BOOL | BOOL | False |  |
| STATIC | ZUSTAND_WEICHE | BYTE | B#16#0 | de: 1 = FB 2 = SFB |
| STATIC | ZUSTAND_WEICHE_1 | BYTE | B#16#0 | de: 101 = FB 202 = SFB |
| TEMP | AR1_STORE | DWORD | DW#16#0 |  |
| TEMP | AUFTRAG_RESET_SAVE | BOOL | False |  |
| TEMP | BMOVE_CALLER | BYTE | B#16#0 |  |
| TEMP | BUFFER_START | DWORD | DW#16#0 |  |
| TEMP | BUSY_SFC51 | BOOL | False |  |
| TEMP | BYTE_0_3_ANY | DWORD | DW#16#0 |  |
| TEMP | BYTE_4_7_ANY | DWORD | DW#16#0 |  |
| TEMP | BYTE_8_9_ANY | WORD | W#16#0 | de: ####################################################### |
| TEMP | DATA_LEN | WORD | W#16#0 |  |
| TEMP | DATA_START | DWORD | DW#16#0 |  |
| TEMP | DEST | ANY |  |  |
| TEMP | DEST_COUNT | WORD | W#16#0 |  |
| TEMP | DEST_DB | WORD | W#16#0 |  |
| TEMP | DEST_OFFSET | DWORD | DW#16#0 | de: Hilfsmerker für LKPA ( Länge kontrollieren und Parameter abspeichern ) |
| TEMP | DIR | BOOL | False |  |
| TEMP | DR | STRUCT |  |  |
|  | DR.LOGADR | WORD | W#16#0 |  |
|  | DR.RACK_NR | BYTE | B#16#0 |  |
|  | DR.RES1 | DWORD | DW#16#0 |  |
|  | DR.RES2 | DWORD | DW#16#0 |  |
|  | DR.RES3 | WORD | W#16#0 |  |
|  | DR.SLOT | BYTE | B#16#0 |  |
|  | DR.STATIONS_NR | BYTE | B#16#0 |  |
|  | DR.SUB_SLOT | BYTE | B#16#0 |  |
| TEMP | DUMM | WORD | W#16#0 |  |
| TEMP | FIRST_SEG | BOOL | False |  |
| TEMP | IKDE_CALLER | BYTE | B#16#0 |  |
| TEMP | IKDE_ERGEBNIS | BYTE | B#16#0 | de: Hilfsmerker für AR1 Store |
| TEMP | KANAL_NUMMER | WORD | W#16#0 |  |
| TEMP | KOPF_LEN | WORD | W#16#0 |  |
| TEMP | KOPF_START | DWORD | DW#16#0 |  |
| TEMP | LADDR_WEICHE | WORD | W#16#0 | de: Ermittelte Baugruppenadresse aus SDB 200 |
| TEMP | LAST_SEG | BOOL | False |  |
| TEMP | LBUSY | BOOL | False | de: SFC READ/WRITE Fertigmeldung |
| TEMP | LKPA_CALLER | BYTE | B#16#0 |  |
| TEMP | LKPA_ERGEBNIS | BYTE | B#16#0 | de: Hilfsmerker für IKDE ( ID kontrollieren und DS errechnen ) |
| TEMP | LOOP_COUNT | WORD | W#16#0 | de: NEUE TEMP VARIABLEN |
| TEMP | MAKRO_BREAK | BOOL | False |  |
| TEMP | MAKRO_CALLER | BYTE | B#16#0 |  |
| TEMP | MAKRO_ERGEBNIS | WORD | W#16#0 |  |
| TEMP | MAKRO_RESET | BOOL | False |  |
| TEMP | MAKRO_STARTED | BOOL | False |  |
| TEMP | NEW_REQ | BOOL | False |  |
| TEMP | NID | BOOL | False |  |
| TEMP | NORM_OFFSET | WORD | W#16#0 | de: Ab hier Temp Var für Weiche |
| TEMP | NPAR | BOOL | False |  |
| TEMP | OBJ_NUMMER | WORD | W#16#0 |  |
| TEMP | OFFSETTING | BOOL | False |  |
| TEMP | POINTER1 | DWORD | DW#16#0 |  |
| TEMP | RET_WT_STORE | INT | 0 | de: Dynamische Speicher fuer RET_VAL// (Output Par. des SFCs)// Hilfsmerker für Makr |
| TEMP | SD_1_SAVE | ANY |  |  |
| TEMP | SD_1_SFB | ANY |  |  |
| TEMP | SEG_LEN | WORD | W#16#0 | de: Hilfsmerker für Block Move |
| TEMP | SFC_DATA | ANY |  |  |
| TEMP | SOURCE | ANY |  |  |
| TEMP | SOURCE_COUNT | WORD | W#16#0 |  |
| TEMP | SOURCE_DB | WORD | W#16#0 |  |
| TEMP | SOURCE_OFFSET | DWORD | DW#16#0 |  |
| TEMP | SZL_HEADER | STRUCT |  |  |
|  | SZL_HEADER.LENGTHDR | WORD | W#16#0 |  |
|  | SZL_HEADER.NDR | WORD | W#16#0 |  |
| TEMP | TEMP_Reserve | BYTE | B#16#0 | de: Ab hier Temp Var für Weiche |
| TEMP | TOTAL_LEN | WORD | W#16#0 |  |
| TEMP | VOIDACTION | BOOL | False |  |

> protected – logic not exported
