"""HMI and alarms from a tiadump dump.

Comfort/Advanced: tag tables and screens arrive as Openness XML exports; Unified: as object
model rows in ``dump.json``. PLC alarms and ProDiag supervisions arrive as xlsx. Layout is
dropped; objects keep their tag bindings.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from defusedxml import ElementTree as SafeET

from plcexport.extractors.tia.xlsx import language_of, read_sheets
from plcexport.model import HmiAlarm, HmiDevice, HmiObject, HmiScreen, HmiTag

INHERITED = "### Inherited from Type ###"


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _attr(e: ET.Element, name: str) -> str | None:
    attrs = next((c for c in e if _local(c.tag) == "AttributeList"), None)
    if attrs is None:
        return None
    v = next((c for c in attrs if _local(c.tag) == name), None)
    return v.text if v is not None else None


def _link(e: ET.Element, name: str) -> str | None:
    links = next((c for c in e if _local(c.tag) == "LinkList"), None)
    if links is None:
        return None
    link = next((c for c in links if _local(c.tag) == name), None)
    if link is None:
        return None
    n = next((c for c in link if _local(c.tag) == "Name"), None)
    return n.text if n is not None else None


# ------------------------------------------------------------------ Comfort/Advanced
def comfort_tags(data: bytes, device: str) -> list[HmiTag]:
    root = SafeET.fromstring(data)
    out = []
    for e in root.iter():
        if _local(e.tag) == "Hmi.Tag.Tag":
            name = _attr(e, "Name")
            if name:
                out.append(HmiTag(name, device, _link(e, "ControllerTag")))
    return out


def comfort_screen(data: bytes, device: str) -> HmiScreen:
    root = SafeET.fromstring(data)
    screen = next(e for e in root.iter() if _local(e.tag) == "Hmi.Screen.Screen")
    objects = []
    for e in screen.iter():
        tag = _local(e.tag)
        if not tag.startswith("Hmi.Screen.") or tag in ("Hmi.Screen.Screen", "Hmi.Screen.Property"):
            continue
        if tag in ("Hmi.Screen.ScreenLayer",):
            continue
        name = _attr(e, "ObjectName") or _attr(e, "Name")  # screen items: ObjectName
        if not name:
            continue
        bindings = sorted(
            {
                n.text
                for d in e.iter()
                if _local(d.tag) == "Hmi.Dynamic.TagConnectionDynamic"
                for link in d.iter()
                if _local(link.tag) == "Tag"
                for n in link
                if _local(n.tag) == "Name" and n.text
            }
        )
        objects.append(HmiObject(name, tag.removeprefix("Hmi.Screen."), tuple(bindings)))
    objects.sort(key=lambda o: o.name)
    return HmiScreen(_attr(screen, "Name") or "?", device, tuple(objects))


def comfort_device(
    dev: Mapping[str, Any], dump_dir: Path
) -> tuple[HmiDevice, list[HmiTag], list[HmiScreen]]:
    name = str(dev["name"])
    tags: list[HmiTag] = []
    for f in dev.get("tag_files") or []:
        tags += comfort_tags((dump_dir / f).read_bytes(), name)
    screens = [
        comfort_screen((dump_dir / f).read_bytes(), name) for f in dev.get("screen_files") or []
    ]
    return HmiDevice(name, str(dev.get("hmi_family") or "comfort")), tags, screens


# ------------------------------------------------------------------ Unified
def unified_device(
    dev: Mapping[str, Any],
) -> tuple[HmiDevice, list[HmiTag], list[HmiScreen], list[HmiAlarm]]:
    name = str(dev["name"])
    tags = [
        HmiTag(str(t["name"]), name, t.get("plc_tag"))
        for t in dev.get("tags") or []
        if t.get("name")
    ]
    screens = [
        HmiScreen(
            str(s["name"]),
            name,
            tuple(
                HmiObject(str(o["name"]), "item") for o in s.get("objects") or [] if o.get("name")
            ),
        )
        for s in dev.get("screens") or []
        if s.get("name")
    ]
    alarms = [
        HmiAlarm(
            f"hmi:{name}/{a['name']}",
            a.get("alarm_class"),
            {"und": a["event_text"]} if a.get("event_text") else {},
            a.get("raised_state_tag"),
        )
        for a in dev.get("alarms") or []
        if a.get("name")
    ]
    return HmiDevice(name, "unified"), tags, screens, alarms


# ------------------------------------------------------------------ PLC alarms (S3)
def plc_alarms(data: bytes) -> tuple[list[HmiAlarm], int]:
    """Alarm instance texts → alarms, and the number of texts inherited from the type."""
    sheets = read_sheets(data)
    if not sheets or not sheets[0]:
        return [], 0
    header, *rows = sheets[0]
    text_cols = [
        (i, lang)
        for i, h in enumerate(header)
        if (lang := language_of(h)) and "Event text" in h and not h.startswith("FieldInfo")
    ]
    out: list[HmiAlarm] = []
    inherited = 0
    for r in rows:
        if len(r) < 2 or not r[0]:
            continue
        texts = {}
        for i, lang in text_cols:
            v = r[i] if i < len(r) else ""
            if v == INHERITED:
                inherited += 1
            elif v.strip():
                texts[lang] = v
        cls = r[2] if len(r) > 2 and r[2] != INHERITED else None
        out.append(HmiAlarm(f"plc:{r[0]}/{r[1]}", cls or None, texts, None))
    return out, inherited


def supervisions(data: bytes) -> list[HmiAlarm]:
    """ProDiag supervisions: the supervised tag is the trigger."""
    sheets = read_sheets(data)
    if not sheets or not sheets[0]:
        return []
    header, *rows = sheets[0]
    col = {h: i for i, h in enumerate(header)}
    text_cols = [(i, lang) for i, h in enumerate(header) if (lang := language_of(h))]
    out = []
    for r in rows:

        def cell(name: str, r: list[str] = r) -> str:
            i = col.get(name)
            return r[i] if i is not None and i < len(r) else ""

        if not cell("ID") and not cell("Supervised tag"):
            continue
        texts = {lang: r[i] for i, lang in text_cols if i < len(r) and r[i].strip()}
        out.append(
            HmiAlarm(
                f"prodiag:{cell('ProDiag FB Name')}/{cell('ID')}",
                cell("Category") or None,
                texts,
                cell("Supervised tag") or None,
            )
        )
    return out
