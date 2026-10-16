# tiadump fixtures

Recorded output of `tiadump project` (TIA Portal V21, Openness) for the Python TIA tests. They
are **generated, never hand-written**: each folder is the `--out` tree of a real run, copied with
`anonymize.py` (personal names → `Author A`, e-mail addresses → `author@example.invalid`).
Everything else is byte-exact as TIA wrote it (SD and SimaticML files: UTF-8 with BOM, CRLF);
`.gitattributes` keeps Git from converting line endings here.

`stub_tiadump.py` stands in for `tiadump` in tests: a source file whose text is
`fixture: <folder>` gets that folder copied to `--out`; `exit:<n>` simulates an exit code.

| Fixture | Source sample (`samples/tia-portal/`) | What it covers |
|---|---|---|
| `step7_v21` | `24-openness-code-snippets/Step7.zap21` (V21, no upgrade) | 3 S7-1500 PLCs, F-blocks (F_FBD/F_DB), know-how protected blocks, motion technology alarms, missing optional products (STEP 7 Safety) |
| `tank_v19` | `28-edge-tank-application/tia-tank-application.zap19` (V19 → V21) | upgrade, GRAPH FB and ProDiag via compile + SimaticML, ProDiag FB/OB unsupported, Program_Alarm, supervisions, Comfort HMI, Unified HMI skipped (missing product) |
| `pid_v19` | `26-openpid-scl/LLCCA_PID_0_3_1.zap19` (V19 → V21) | SCL/FBD with comments in `.s7res`, Comfort HMI with 100 tags and 4 screens |
| `conn_v21` | `myTiaProject1/` (V21, the project owner's own sample, with a GRAPH block) | S7 connections incl. SIMATIC ACC between two PLCs of the project, BSEND/BRCV calls, PN/PN and DP/DP couplers, the GRAPH FB `Baustein_Graph` with an alternative branch (SimaticML); owner-confirmed reference values in `specs/010-tia-connections/research.md` R1 and R8 |

## Sources and licenses

| Fixture | Repository | License |
|---|---|---|
| `step7_v21` | https://github.com/siemens/tia-portal-openness-code-snippets | Siemens royalty-free software license; MIT for the source code portions (repository `LICENSE.md`) |
| `tank_v19` | https://github.com/industrial-edge/miscellaneous (`tank application/`) | Siemens royalty-free software license; MIT for the source code portions (repository `LICENSE.md`) |
| `pid_v19` | https://github.com/LCC-Automation/OpenPID-TIA-SCL | MIT, © LCC Automation AB (the notice is kept in the exported comments) |
| `conn_v21` | none: made by the project owner for these tests | the owner's own work |

Recorded last on 2026-10-14 with the finished `tiadump project`; since then the dumps
also hold the project library, its counts and the library links of the units. Text IDs
(`MLC_…`) and `<Created>` time stamps differ with every recording of an upgraded project; the
export does not depend on them.

Only these GitHub samples are recorded here (decision 2026-10-09). Dumps of SIOS downloads
(e.g. the LBCFC library) stay local.

Re-record after changes to `tiadump` (on the TIA host):

```powershell
tools\tiadump\publish\tiadump.exe project C:\tiaw\x\Step7.zap21 --work C:\tiaw\x --out C:\tiaw\x-out
uv run python tests/fixtures/tiadump/anonymize.py C:\tiaw\x-out step7_v21
```
