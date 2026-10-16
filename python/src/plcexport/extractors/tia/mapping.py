"""``tiadump`` dump -> ``ExportBundle``.

Pure function of the dump folder and a few settings, so it is tested on recorded fixtures without
TIA Portal. One model per PLC (``project.device``); HMIs that belong to no single PLC and the
hardware of devices without a PLC go into a ``_project`` model, but only when the project has
more than one PLC.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, cast

from plcexport.common import ExtractText, ExtractWarning, IoDirection, Scope, UnitKind
from plcexport.connections_link import link
from plcexport.extractors.tia import comm_calls
from plcexport.extractors.tia import hmi as hmi_
from plcexport.extractors.tia.connections import map_connections, map_couplers
from plcexport.extractors.tia.library import (
    library_ids,
    library_model,
    links,
    project_library_name,
    unique_versions,
)
from plcexport.extractors.tia.sd_ids import stable_text_ids
from plcexport.extractors.tia.simaticml import member_variables, parse_tag_table, parse_unit
from plcexport.model import (
    CATEGORIES,
    CONNECTIONS,
    CategoryCoverage,
    ConnectionsModel,
    ConnectionUse,
    Coverage,
    ExportBundle,
    ExportModel,
    ExportProject,
    ExportUnit,
    ExportVariable,
    Gap,
    HardwareModel,
    HmiAlarm,
    HmiDevice,
    HmiModel,
    HmiScreen,
    HmiTag,
    HwChannel,
    HwController,
    HwModule,
    HwNetwork,
    HwRack,
    NativePart,
    SafetyModel,
    SafetySignature,
    StructDevice,
    StructFolder,
    StructTask,
    Upgrade,
    link_channels,
    link_hmi,
)

PLATFORM = "siemens-tia"
SD_KIND = "siemens-simatic-sd"
SD_ROOT = "sd"
PROJECT_DEVICE = "_project"
HMI_FAMILIES = ("comfort", "advanced", "unified")
SCOPES: dict[str, Scope] = {
    "FB": "fb_interface",
    "FC": "fc_interface",
    "DB": "db_member",
    "IDB": "db_member",
    "UDT": "udt_member",
}
UNIT_KINDS = ("OB", "FB", "FC", "DB", "IDB", "UDT")
# TIA-specific gap reasons
R_INCONSISTENT = "other:inconsistent – not compiled"
R_UNSUPPORTED = "other:not supported by SIMATIC SD and SimaticML"
R_LICENSE = "other:STEP 7 Professional license missing"
R_EXPORT_FAILED = "other:export failed"
R_MISMATCH = "other:completeness mismatch"


def r_missing(package: str) -> str:
    return f"other:missing package {package}"


@dataclass(frozen=True)
class MappingOptions:
    extractor_id: str
    extractor_version: str
    vendor_software: str | None = None  # "TIA Portal V21 Upd1"


@dataclass
class _Acc:
    """What one model collects before it is finished."""

    model: ExportModel
    gaps: list[Gap] = field(default_factory=list)
    hw_devices: list[Mapping[str, Any]] = field(default_factory=list)
    hmi_devices: list[HmiDevice] = field(default_factory=list)
    hmi_tags: list[HmiTag] = field(default_factory=list)
    screens: list[HmiScreen] = field(default_factory=list)
    alarms: list[HmiAlarm] = field(default_factory=list)
    expected: dict[str, int] = field(default_factory=dict)  # category -> count from tiadump
    gapped: dict[str, int] = field(default_factory=dict)  # category -> counted gaps
    hmi_partial: str | None = None


# ------------------------------------------------------------------ program
def _unit_gap_reason(u: Mapping[str, Any]) -> str:
    error = str(u.get("error") or "")
    if u.get("protected"):
        return "protected"
    if error.startswith("compile failed"):
        return R_INCONSISTENT
    if "license missing" in error:
        return R_LICENSE
    if "not supported during import and export" in error:
        return R_UNSUPPORTED
    return R_EXPORT_FAILED


def _io_direction(address: str | None) -> IoDirection | None:
    a = (address or "").lstrip("%").upper()
    if a.startswith("I"):
        return "input"
    if a.startswith("Q"):
        return "output"
    if a.startswith("M"):
        return "memory"
    return None


def _program(acc: _Acc, plc: Mapping[str, Any], dump_dir: Path) -> None:
    m = acc.model
    name = str(plc["name"])
    sd_prefix = f"{SD_ROOT}/{name}/"
    sd_files: dict[str, bytes] = {}
    folders: dict[str, list[str]] = {}
    tasks: list[StructTask] = []
    safety_units: list[str] = []

    if plc.get("missing_package"):
        reason = r_missing(str(plc["missing_package"]))
        acc.gaps.append(Gap("program_units", f"{name} (program)", reason))
        acc.gapped["program_units"] = acc.expected.get("program_units", 0)
        acc.gapped["symbols"] = acc.expected.get("symbols", 0)

    for u in plc.get("units") or []:
        uname, kind = str(u["name"]), cast(UnitKind, u["kind"] if u["kind"] in UNIT_KINDS
                                           else "OTHER")  # fmt: skip
        files: list[str] = []
        for f in u.get("files") or []:
            f = str(f)
            if u["part"] == "sd":
                rel = f.removeprefix(sd_prefix)
                sd_files[rel] = (dump_dir / f).read_bytes()
                files.append(f"{SD_ROOT}/{rel}")
        attrs = {k: str(v) for k, v in (u.get("attributes") or {}).items() if v}
        if u.get("sd_error") and u["part"] == "common":
            attrs["route"] = "simaticml"
        scope = SCOPES.get(kind)
        parse_quality = "full" if u["part"] != "none" else "names_only"
        if u["part"] == "common":
            parsed = parse_unit((dump_dir / str(u["files"][0])).read_bytes())
            m.unit_bodies[uname] = parsed.body
            if parsed.partial:
                parse_quality = "partial"
            for lang, text in sorted(parsed.title.items()):
                m.texts.append(ExtractText(uname, "title", lang, text))
            for lang, text in sorted(parsed.comment.items()):
                m.texts.append(ExtractText(uname, "comment", lang, text))
            if scope:
                m.variables += member_variables(uname, scope, f'"{uname}"', parsed.members)
        elif u["part"] == "none":
            acc.gaps.append(Gap("program_units", uname, _unit_gap_reason(u)))
        if u.get("safety"):
            safety_units.append(uname)
        m.units.append(
            ExportUnit(
                name=uname,
                kind=kind,
                language=None if kind in ("DB", "IDB", "UDT") else u.get("language"),
                files=tuple(files),
                parse_quality=cast(Any, parse_quality),
                number=u.get("number"),
                protected=bool(u.get("protected")),
                attributes=attrs,
                safety=bool(u.get("safety")),
                folder=u.get("folder") or None,
                path_prefix=f'"{uname}"' if scope else None,
                variable_scope=scope,
            )
        )
        folders.setdefault(str(u.get("folder") or ""), []).append(uname)
        if kind == "OB":
            tasks.append(StructTask(uname, "ob", units=(uname,)))

    for t in plc.get("tag_tables") or []:
        table, tags = parse_tag_table((dump_dir / str(t["file"])).read_bytes())
        m.units.append(ExportUnit(table, "TAG_TABLE", None, (), folder=t.get("folder") or None))
        folders.setdefault(str(t.get("folder") or ""), []).append(table)
        for tag in tags:
            m.variables.append(
                ExportVariable(
                    declared_in=table,
                    scope="global_tag",
                    symbolic_path=f'"{tag.name}"',
                    data_type=tag.data_type,
                    section="CONSTANT" if tag.constant else None,
                    io_direction=_io_direction(tag.address),
                    address=tag.address,
                    start_value=tag.value if tag.constant else None,
                    ext_accessible=tag.accessible,
                    ext_visible=tag.visible,
                    ext_writable=tag.writable,
                    comments=dict(tag.comment),
                )
            )

    if sd_files:
        sd_files = stable_text_ids(sd_files)  # TIA makes the text IDs up on every upgrade
        m.native_parts.append(NativePart(SD_KIND, SD_ROOT, sd_files))
    signatures = [
        SafetySignature(name, str(s["value"]), str(s["kind"]))
        for s in (plc.get("safety") or {}).get("signatures") or []
    ]
    m.safety = SafetyModel(units=tuple(sorted(safety_units)), signatures=tuple(signatures))
    m.structure = replace(
        m.structure,
        tasks=tuple(tasks),
        folders=tuple(StructFolder(f, tuple(sorted(us))) for f, us in folders.items() if f),
    )
    _plc_alarms(acc, plc, dump_dir)


def _plc_alarms(acc: _Acc, plc: Mapping[str, Any], dump_dir: Path) -> None:
    alarms = plc.get("alarms") or {}
    if alarms.get("texts_file"):
        found, inherited = hmi_.plc_alarms((dump_dir / alarms["texts_file"]).read_bytes())
        acc.alarms += found
        if inherited:
            acc.model.warnings.append(
                ExtractWarning(
                    "alarm_text_inherited",
                    f"{plc['name']}: {inherited} alarm text(s) are inherited from the alarm "
                    "type; type-level texts are not exported by TIA Openness",
                )
            )
    if alarms.get("supervisions_file"):
        acc.alarms += hmi_.supervisions((dump_dir / alarms["supervisions_file"]).read_bytes())


# ------------------------------------------------------------------ hardware
def _address_range(a: Mapping[str, Any]) -> str:
    """Openness gives the length in bits (a 16-byte module has 128); a range covers whole
    bytes, so a 2-bit module covers one."""
    area = "I" if a["io"] == "input" else "Q"
    last = a["start"] + max(1, (int(a["length"]) + 7) // 8) - 1
    return f"%{area}{a['start']}.0-%{area}{last}.7"


def _hardware(devices: list[Mapping[str, Any]], plc_names: set[str]) -> HardwareModel:
    controllers: list[HwController] = []
    racks: dict[str, HwRack] = {}
    modules: list[HwModule] = []
    networks: list[HwNetwork] = []
    for dev in devices:
        dname = str(dev["name"])
        for it in dev.get("items") or []:
            rack_ref = f"{dname}/{it['rack']}"
            ref = f"{dname}/{it['path']}"
            io = [a for a in it.get("addresses") or [] if a["length"] > 0]
            if it.get("order_no") or io:  # a GSD submodule has addresses but no order no
                racks.setdefault(rack_ref, HwRack(rack_ref, str(it["rack"])))
                modules.append(
                    HwModule(
                        ref=ref,
                        type=str(it["name"]),
                        rack=rack_ref,
                        slot=it.get("slot"),
                        order_no=it.get("order_no"),
                        firmware=it.get("firmware"),
                        address_ranges=tuple(
                            _address_range(a) for a in it.get("addresses") or [] if a["length"] > 0
                        ),
                    )
                )
            if it["name"] in plc_names:
                controllers.append(
                    HwController(f"cpu:{it['name']}", str(it["name"]), None, it.get("order_no"),
                                 it.get("firmware"))
                )  # fmt: skip
            for i in it.get("interfaces") or []:
                networks.append(
                    HwNetwork(f"{dname}/{i['node']}/{i['type']}", str(i["type"]),
                              i.get("address"), i.get("device_name"), i.get("subnet"))
                )  # fmt: skip
    return HardwareModel(tuple(controllers), tuple(racks.values()), tuple(modules), (),
                         tuple(networks))  # fmt: skip


_IO = re.compile(r"^%([IQ])([BWD]?)(\d+)(?:\.\d)?$")
_SIZE = {"": 1, "B": 1, "W": 2, "D": 4}
_RANGE = re.compile(r"^%([IQ])(\d+)\.0-%[IQ](\d+)\.7$")


def _channels(hw: HardwareModel, variables: list[ExportVariable]) -> tuple[HwChannel, ...]:
    """One channel per I/O tag inside a module's address range."""
    ranges = [
        (r.group(1), int(r.group(2)), int(r.group(3)), mod.ref)
        for mod in hw.modules
        for a in mod.address_ranges
        if (r := _RANGE.match(a))
    ]
    out: dict[str, HwChannel] = {}
    for v in variables:
        found = _IO.match((v.address or "").upper()) if v.scope == "global_tag" else None
        if not found:
            continue
        area, byte = found.group(1), int(found.group(3))
        last = byte + _SIZE[found.group(2)] - 1
        for a, lo, hi, module_ref in ranges:
            if a == area and lo <= byte and last <= hi:
                ref = f"{module_ref}/{v.address}"
                out.setdefault(ref, HwChannel(ref, module_ref, str(v.address), v.symbolic_path))
                break
    return tuple(out.values())


# ------------------------------------------------------------------ HMI
def _hmi(acc: _Acc, dev: Mapping[str, Any], dump_dir: Path) -> None:
    name, family = str(dev["name"]), str(dev.get("hmi_family") or "")
    if family not in HMI_FAMILIES:
        acc.hmi_devices.append(HmiDevice(name, family or None))
        acc.gaps.append(Gap("hmi", name, "unsupported"))
        return
    if dev.get("missing_package"):
        acc.hmi_devices.append(HmiDevice(name, family))
        acc.gaps.append(Gap("hmi", name, r_missing(str(dev["missing_package"]))))
        acc.hmi_partial = r_missing(str(dev["missing_package"]))
        return
    if family == "unified":
        device, tags, screens, alarms = hmi_.unified_device(dev)
        acc.alarms += alarms
    else:
        device, tags, screens = hmi_.comfort_device(dev, dump_dir)
    acc.hmi_devices.append(device)
    acc.hmi_tags += tags
    acc.screens += screens
    if tags and not any(t.plc_tag for t in tags):
        acc.model.warnings.append(
            ExtractWarning(
                "hmi_plc_tag_unknown",
                f"{name}: the HMI tag export names the connection but not the PLC tag",
            )
        )


def _hmi_owner(dev: Mapping[str, Any], plcs: list[str], stations: dict[str, str]) -> str:
    """By connection partner, else the single PLC, else ``_project``."""
    partners = set()
    for c in dev.get("connections") or []:
        for key in ("Partner", "Station", "partner", "station"):
            p = str(c.get(key) or "")
            if p in plcs:
                partners.add(p)
            elif p in stations:
                partners.add(stations[p])
    if len(partners) == 1:
        return partners.pop()
    if len(plcs) == 1:
        return plcs[0]
    return PROJECT_DEVICE


# ------------------------------------------------------------------ coverage
def _coverage(acc: _Acc) -> None:
    m = acc.model
    counts = m.item_counts()
    cats: dict[str, CategoryCoverage] = {
        c: CategoryCoverage("delivered") if counts[c] else CategoryCoverage(
            "unavailable", "not_in_project")
        for c in CATEGORIES
    }  # fmt: skip
    for g in acc.gaps:
        if g.reason.startswith("other:missing package") and not counts[g.category]:
            cats[g.category] = CategoryCoverage("unavailable", g.reason)
        elif g.reason.startswith("other:missing package") or g.category == "hmi":
            cats[g.category] = CategoryCoverage("partial", g.reason)
    if acc.hmi_partial and counts["hmi"]:
        cats["hmi"] = CategoryCoverage("partial", acc.hmi_partial)
    if m.safety.units and not m.safety.signatures:
        cats["safety"] = CategoryCoverage("partial", "other:no safety signatures read")
    # exported + gaps == tiadump's own count, per category
    exported = {
        "program_units": sum(
            1 for u in m.units if u.kind in UNIT_KINDS and u.parse_quality != "names_only"
        ),
        "symbols": counts["symbols"],
        "hardware": len(m.hardware.modules),
        "hmi_tags": len(acc.hmi_tags),
        "screens": len(acc.screens),
    }
    gaps = {
        "program_units": sum(
            1 for g in acc.gaps if g.category == "program_units" and g.item in
            {u.name for u in m.units}
        ),
    }  # fmt: skip
    for key, want in acc.expected.items():
        got = exported.get(key, 0) + gaps.get(key, 0) + acc.gapped.get(key, 0)
        if got != want:
            cat = "hmi" if key in ("hmi_tags", "screens") else key
            m.warnings.append(
                ExtractWarning(
                    "completeness_mismatch",
                    f"{cat}: {got} exported or reported, tiadump counted {want} ({key})",
                )
            )
            cats[cat] = CategoryCoverage("partial", R_MISMATCH)
    m.coverage = Coverage(categories=cats, gaps=tuple(acc.gaps))


# ------------------------------------------------------------------ bundle
_STATIC = re.compile(
    r'^\s*("(?:[^"]|"")+"|[A-Za-z_]\w*)\s*(?:\{[^}]*\}\s*)?:\s*"?(GET|PUT|BSEND|BRCV|USEND|URCV)"?\s*;',
    re.IGNORECASE | re.MULTILINE,
)


def _calls(plc: Mapping[str, Any], dump_dir: Path) -> tuple[list[ConnectionUse], list[str]]:
    """the communication calls of the PLC's SD units, unlinked, and the
    know-how protected units whose calls cannot be read."""
    units = [u for u in plc.get("units") or [] if not u.get("missing_package")]
    db_names = {
        int(u["number"]): str(u["name"])
        for u in units
        if u.get("kind") in ("DB", "IDB") and u.get("number") is not None
    }
    calls: list[ConnectionUse] = []
    for u in units:
        if u.get("part") != "sd" or u.get("kind") not in ("OB", "FB", "FC"):
            continue
        safety = str(u.get("language") or "").upper().startswith("F_")
        for f in u.get("files") or []:
            if not str(f).endswith(".s7dcl"):
                continue
            text = (dump_dir / f).read_bytes().decode("utf-8-sig", errors="replace")
            statics = {m.group(1).strip('"'): m.group(2).upper() for m in _STATIC.finditer(text)}
            found = comm_calls.sd_calls(
                str(u["name"]), text, statics=statics, db_number=db_names.get
            )
            calls += [replace(c, safety=safety) for c in found]
    protected = sorted(str(u["name"]) for u in units if u.get("protected"))
    return calls, protected


def _connections(
    m: ExportModel,
    plc: Mapping[str, Any],
    station: str,
    dump_dir: Path,
    hw_devices: list[Mapping[str, Any]],
) -> None:
    """the PLC's configured connections, the calls of its program linked to them (shared
    rules), and the optional coverage category (§3, §6)."""
    name = str(plc["name"])
    owner = f"{station}/{name}"
    module = next((x.ref for x in m.hardware.modules if x.type == name), None)
    conns, findings, warnings = map_connections(
        plc.get("configured_connections") or [],
        station=station,
        plc=name,
        module=module,
        networks={n.ref for n in m.hardware.networks},
    )
    calls, protected = _calls(plc, dump_dir)
    read = () if plc.get("missing_package") else (owner,)
    linked = link(conns, [(owner, c) for c in calls], read_owners=read)
    couplers, coupler_findings, coupler_warnings = map_couplers(
        hw_devices, plc=name, variables=m.variables
    )
    m.connections = ConnectionsModel(
        connections=linked.connections,
        uses=linked.uses,
        couplers=tuple(couplers),
        findings=(*findings, *linked.findings, *coupler_findings),
    )
    m.warnings += warnings + coupler_warnings
    reasons = []
    error = plc.get("configured_connections_error")
    if error:
        reasons.append(f"connections not readable: {error}")
    if protected and m.connections.item_count():
        reasons.append(f"calls in {len(protected)} protected block(s) not readable")
        gaps = tuple(Gap(CONNECTIONS, unit, "protected") for unit in protected)
        m.coverage = replace(m.coverage, gaps=(*m.coverage.gaps, *gaps))
    if reasons:
        cov = CategoryCoverage("partial", "other:" + "; ".join(reasons))
    elif m.connections.item_count():
        cov = CategoryCoverage("delivered")
    else:
        cov = CategoryCoverage("unavailable", "not_in_project")
    m.coverage = replace(m.coverage, categories={**m.coverage.categories, CONNECTIONS: cov})


def _io_controller(device: Mapping[str, Any], plcs: list[str]) -> str | None:
    """The PLC that controls the IO system an item of ``device`` is connected to (the
    first one, so both sides of a coupler stay in one export)."""
    for it in device.get("items") or []:
        controller = (it.get("io_system") or {}).get("controller")
        name = str(controller).rsplit("/", 1)[-1] if controller else None
        if name in plcs:
            return name
    return None


def to_bundle(dump: Mapping[str, Any], dump_dir: Path, opts: MappingOptions) -> ExportBundle:
    tia = dump.get("tia") or {}
    up = tia.get("upgrade")
    upgrade = (
        Upgrade(str(up["from"]), str(up["to"]), opts.vendor_software or f"TIA Portal {up['to']}",
                tuple(str(x) for x in up.get("messages") or []))
        if up else None
    )  # fmt: skip
    langs = tuple((dump.get("languages") or {}).get("project") or ())
    counts: Mapping[str, Mapping[str, int]] = dump.get("counts") or {}
    plcs = [d for d in dump["devices"] if d["kind"] == "plc"]
    plc_names = [str(p["name"]) for p in plcs]
    hw_devices = list((dump.get("hardware") or {}).get("devices") or [])
    # the station of a PLC: the hardware device that holds the CPU item of the same name
    stations = {
        str(d["name"]): str(it["name"])
        for d in hw_devices
        for it in d.get("items") or []
        if it["name"] in plc_names
    }

    plc_station = {plc: station for station, plc in stations.items()}

    def new(device: str, controller: str | None) -> _Acc:
        return _Acc(
            ExportModel(
                project=ExportProject(
                    platform_id=PLATFORM,
                    platform_version=tia.get("version"),
                    controller=controller,
                    line_or_machine=None,
                    extractor_id=opts.extractor_id,
                    extractor_version=opts.extractor_version,
                    languages=langs,
                    upgrade=upgrade,
                    device=device,
                )
            )
        )

    accs: dict[str, _Acc] = {}
    for p in plcs:
        acc = accs[str(p["name"])] = new(str(p["name"]), p.get("order_no"))
        c = counts.get(str(p["name"])) or {}
        acc.expected = {"program_units": int(c.get("units", 0)), "symbols": int(c.get("tags", 0))}
        _program(acc, p, dump_dir)

    def owner(name: str) -> _Acc:
        if name not in accs:
            accs[name] = new(name, None)
        return accs[name]

    for d in hw_devices:
        target = (
            stations.get(str(d["name"]))
            or _io_controller(d, plc_names)  # an IO device belongs to its IO controller
            or (plc_names[0] if len(plc_names) == 1 else PROJECT_DEVICE)
        )
        owner(target).hw_devices.append(d)
    for d in dump["devices"]:
        if d["kind"] != "hmi":
            continue
        acc = owner(_hmi_owner(d, plc_names, stations))
        c = counts.get(str(d["name"])) or {}
        if not d.get("missing_package"):
            for key in ("hmi_tags", "screens"):
                acc.expected[key] = acc.expected.get(key, 0) + int(c.get(key, 0))
        _hmi(acc, d, dump_dir)

    for e in dump.get("errors") or []:
        where, kind = str(e.get("where") or ""), str(e.get("kind") or "")
        plc_acc = accs.get(where.split("/", 1)[0])
        hmi_target = next((a for a in accs.values() if any(h.name == where for h in a.hmi_devices)),
                          None)  # fmt: skip
        if kind == "unsupported" and hmi_target is not None:
            hmi_target.gaps.append(Gap("hmi", f"{where} alarms", "unsupported"))
            continue
        if kind in (
            "protected",
            "unsupported",
            "compile_failed",
            "export_failed",
            "missing_package",
        ) and (plc_acc or hmi_target):
            continue  # already a gap of its unit or device
        (plc_acc or hmi_target or next(iter(accs.values()))).model.warnings.append(
            ExtractWarning(f"tiadump_{kind or 'error'}", f"{where}: {e.get('message')}")
        )  # fmt: skip

    if not accs:  # an empty project (no device at all) is still one export that says so
        owner(PROJECT_DEVICE)
    hw_expected = int((counts.get("_hardware") or {}).get("modules", 0))
    proj_lib, lib_duplicates = unique_versions(dump.get("project_library") or {})
    if proj_lib.get("name"):
        upgrade = (dump.get("tia") or {}).get("upgrade")
        proj_lib["name"] = project_library_name(str(proj_lib["name"]), upgrade)
    models = []
    for acc in accs.values():
        m = acc.model
        m.hardware = _hardware(acc.hw_devices, set(plc_names))
        m.hardware = replace(m.hardware, channels=_channels(m.hardware, m.variables))
        m.hmi = HmiModel(
            devices=tuple(acc.hmi_devices),
            screens=tuple(acc.screens),
            alarms=tuple(acc.alarms),
            hmi_tags=tuple(acc.hmi_tags),
        )
        m.structure = replace(
            m.structure,
            devices=tuple(StructDevice(str(d["name"]), None) for d in acc.hw_devices),
        )
        m.platform = {
            "tia_version": tia.get("version"),
            "saved_version": (dump.get("source") or {}).get("saved_version"),
            "compiled_units": sorted(
                x.split("/", 1)[1] for x in dump.get("compiled_units") or []
                if x.split("/", 1)[0] == m.project.device
            ),
            "missing_packages": sorted(str(p["name"]) for p in dump.get("missing_packages") or []),
            "tiadump": (dump.get("tool") or {}).get("version"),
        }  # fmt: skip
        if dump.get("used_products"):  # what the project needs, for routing
            m.platform["used_products"] = sorted(
                f"{u['name']} {u['version']}".strip() for u in dump["used_products"]
            )
        # the project library in every PLC export, link facts per PLC
        plc_dev = next((p for p in plcs if p["name"] == m.project.device), None)
        link_rows = list(plc_dev.get("library_links") or []) if plc_dev else []
        has_lib = bool(proj_lib.get("types") or proj_lib.get("master_copies"))
        if has_lib and (plc_dev is not None or not plcs):
            m.library = library_model(proj_lib)
            m.warnings += lib_duplicates
        m.library_links = links(plc_dev) if plc_dev else []
        if m.library is not None or link_rows:
            m.platform_files["library_ids.json"] = library_ids(proj_lib, link_rows)
        link_hmi(m)
        link_channels(m)
        _coverage(acc)
        if plc_dev is not None and "configured_connections" in plc_dev:
            station = plc_station.get(str(plc_dev["name"])) or "-"
            _connections(m, plc_dev, station, dump_dir, acc.hw_devices)
        models.append(m)
    # hardware modules are counted for the whole project
    got = sum(len(m.hardware.modules) for m in models)
    if got != hw_expected:
        for m in models:
            m.warnings.append(
                ExtractWarning("completeness_mismatch",
                               f"hardware: {got} modules exported, tiadump counted {hw_expected}")
            )  # fmt: skip
            cats = dict(m.coverage.categories)
            cats["hardware"] = CategoryCoverage("partial", R_MISMATCH)
            m.coverage = replace(m.coverage, categories=cats)
    models.sort(key=lambda m: (m.project.device == PROJECT_DEVICE, m.project.device or ""))
    return ExportBundle([m.sorted() for m in models])
