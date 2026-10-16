## Platform: Siemens TIA Portal

Exported on a TIA host through TIA Openness (`tiadump`, extractor `tia`). The project is read
from a copy; projects saved with an older TIA Portal are upgraded on that copy only, and the
manifest's `upgrade` says from which version and what TIA reported. A project with several PLCs
gives one export per PLC (`manifest.device`); HMIs shared by several PLCs and hardware without a
PLC are in a `_project` export next to them.

**Two parts.** S7-1200/1500 program units are exported as **SIMATIC SD** files in `sd/`,
unchanged as TIA writes them (`parts/siemens-simatic-sd.json` lists the units and their files,
`index.md` marks them `unit (SD)`). Everything else is in the common format: units SD cannot
export (GRAPH, S7-300/400, see below) in `units/`, tag tables in `symbols.json`, hardware,
safety, HMI and alarms. A unit is in exactly one of the two parts.

**SIMATIC SD.** A unit is a `.s7dcl` file (declaration and code, SCL-like text, also for LAD
and FBD) and a `.s7res` file with its texts by language. Example (`FB_2_Filling`, FBD):

```text
NETWORK
    RUNG #operate.state.FillingTank
        P_Trig( #statFillingTankTrigger )
        Add(
            in1 := #process.batchId,
            in2 := 1,
            out => #process.batchId
        )
    END_RUNG
END_NETWORK
{
    S7_Language := "FBD";
    S7_NetworkTitle := "MLC_3aq"
}
```

`RUNG <condition>` is the power flow into the network; boxes follow in order. Text ids such as
`MLC_3aq` resolve in the `.s7res` file:

```yaml
MultiLingualTexts:
  - id: MLC_3aq
    en-US: Set process values (shifting bottle, number produced)
```

`#name` is a local of the block, `"name"` a global tag or data block. Instance DBs look like
`DATA_BLOCK DB_5_CIP_Simulation_Graph : FB_5_CIP_Simulation_Graph`.

**Common-format units.** Units SD refuses (GRAPH sequences; S7-300/400) are read from
SimaticML: SCL and STL keep their text; LAD and FBD become NTN statements, one network each,
e.g. `IF P_TRIG(#statFillingTankTrigger, #operate.state.FillingTank) THEN Add(in1 :=
#process.batchId, in2 := UDInt#1, out => #process.batchId); END_IF;`. GRAPH becomes steps,
actions and transitions: `TRANSITION "Initial step" -> "Step1: pre-rinse" WHEN #cip.cipStep1;`.
Such units carry the attribute `route: simaticml`.

**Gaps** (`coverage.json`): know-how protected units are listed by name only (`protected`);
ProDiag blocks are `other:not supported by SIMATIC SD and SimaticML`; units that TIA could not
compile on the copy are `other:inconsistent – not compiled`; devices whose TIA product is not
installed on the host are `other:missing package <name>`. `platform/siemens-tia/platform.json`
lists the units compiled on the copy (never in the source project).

**Hardware.** Modules with order number and firmware per device and rack, I/O address ranges
(`%I2.0-%I3.7`), network interfaces with IP address/prefix and subnet (`192.168.112.1/24` on
`PN/IE_1`). I/O tags inside a module's range are linked to it as channels.

**Connections** (`connections.json`, same model as STEP 7). S7 connections carry the local ID
in hex as TIA shows it (`0x0100` for `16#100`), local and partner address, rack/slot and both
TSAPs (`14.01`, or SIMATIC ACC form `SIMATIC-ACC10201`) and the active side; other connection
types are listed with their type only. TIA records no `one_way` and no `sources`. A partner PLC
of the same project is named and paired with it by address and TSAP. GET/PUT/BSEND/BRCV/USEND/
URCV calls in SD units are linked to their connection by ID; data areas are symbolic
(`"Datenbaustein_1".write`) without byte addresses. Couplers (PN/PN, DP/DP) are in the export of
the PLC that controls the side; a side connected to no IO system, or a transfer area whose
length differs from its address, is a finding.

**Safety.** F-units (languages `F_LAD`, `F_FBD`, `F_DB`, …) are marked `safety`; the safety
signatures are copied as TIA reports them, without interpretation.

**Libraries.** A company library is an export of its own (`manifest.kind: library`, path
`libraries/<name>/`). `library.json` lists every type with **every version**, sorted by version
number (`1.10.0` after `1.9.0`): status `released` or `in_work`, author, date, comment. PLC type
versions are units named `<Type>@<version>` (`content_path` points to them); HMI types and
faceplates are metadata only, master copies list their objects. `company: true` marks the
libraries configured as company libraries; a copy found elsewhere names the original in
`duplicate_of`.

A project export has its project library in `library.json` (`kind: project`) and its links in
`library_links.json`: which unit is an instance of which library type and version, as TIA
records it (never guessed from names). After each batch, `relink` compares every link with the
company library: `comparison` is `current`, `outdated` (`newest_released` names the newer
version), `version_not_in_library`, or `not_compared` when the type does not come from a company
library (`origin`: `project_only`, `unknown_library`, `other_library`). `compared_with` names the
library export and its commit.

**Alarms and HMI.** Program alarms (`plc:<instance>/<alarm>`) and ProDiag supervisions
(`prodiag:<FB>/<ID>`, trigger = supervised tag) are in `hmi/hmi.json`. Texts an alarm inherits
from its type are not exported by TIA (warning `alarm_text_inherited`). WinCC Comfort/Advanced
and Unified devices give HMI tags and screens with their objects and tag bindings (layout is
dropped); Comfort/Advanced HMI alarms are not reachable through Openness and are a gap.
