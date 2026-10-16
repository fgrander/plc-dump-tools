"""SimaticML (TIA Portal Openness XML) → units, interfaces, bodies.

Used for the units that SIMATIC SD cannot export (GRAPH, S7-300/400, …) and for PLC
tag tables. Graphical logic becomes Network Text Notation (docs/common-format.md §6):
LAD/FBD ``FlgNet`` networks are evaluated as power flow into expressions and statements, GRAPH
sequences into §6.1 steps, actions and transitions. Elements this parser does not know are
rendered generically (``Name(pin := …)``) and lower ``parse_quality`` to ``partial``; nothing is
dropped silently.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any, cast

from defusedxml import ElementTree as SafeET

from plcexport.common import Scope
from plcexport.format import ntn
from plcexport.model import BodyLanguage, BodyNetwork, ExportVariable, UnitBody

_COMPARE = {"Eq": "=", "Ne": "<>", "Gt": ">", "Ge": ">=", "Lt": "<", "Le": "<="}
_SECTIONS = {
    "Input": "IN", "Output": "OUT", "InOut": "IN_OUT", "Static": "STATIC", "Temp": "TEMP",
    "Constant": "CONSTANT", "Return": "RETURN",
}  # fmt: skip
_KINDS = {
    "SW.Blocks.OB": "OB", "SW.Blocks.FB": "FB", "SW.Blocks.FC": "FC", "SW.Blocks.GlobalDB": "DB",
    "SW.Blocks.ArrayDB": "DB", "SW.Blocks.InstanceDB": "IDB", "SW.Types.PlcStruct": "UDT",
}  # fmt: skip


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _child(e: ET.Element, name: str) -> ET.Element | None:
    return next((c for c in e if _local(c.tag) == name), None)


def _children(e: ET.Element, name: str) -> Iterator[ET.Element]:
    return (c for c in e if _local(c.tag) == name)


def _items(e: ET.Element | None) -> list[ET.Element]:
    """Children of an optional element (an element's truth value is deprecated)."""
    return list(e) if e is not None else []


def _text(e: ET.Element | None, name: str) -> str | None:
    c = _child(e, name) if e is not None else None
    return c.text if c is not None and c.text is not None else None


# ------------------------------------------------------------------ texts
def multilingual(owner: ET.Element, composition: str) -> dict[str, str]:
    """``<MultilingualText CompositionName="Title">`` → ``{culture: text}``, empty texts dropped."""
    out: dict[str, str] = {}
    obj = _child(owner, "ObjectList")
    for mt in _children(obj, "MultilingualText") if obj is not None else ():
        if mt.get("CompositionName") != composition:
            continue
        items = _child(mt, "ObjectList")
        for item in _children(items, "MultilingualTextItem") if items is not None else ():
            attrs = _child(item, "AttributeList")
            culture, text = _text(attrs, "Culture"), _text(attrs, "Text")
            if culture and text and text.strip():
                out[culture] = text
    return out


def _member_comment(m: ET.Element) -> dict[str, str]:
    c = _child(m, "Comment")
    if c is None:
        return {}
    return {
        t.get("Lang", ""): t.text
        for t in _children(c, "MultiLanguageText")
        if t.text and t.text.strip()
    }


# ------------------------------------------------------------------ interface
@dataclass
class Member:
    name: str
    data_type: str
    section: str
    start_value: str | None = None
    comment: dict[str, str] = field(default_factory=dict)
    retain: bool | None = None
    accessible: bool | None = None
    visible: bool | None = None
    writable: bool | None = None
    members: list[Member] = field(default_factory=list)


def _bool_attrs(m: ET.Element) -> dict[str, bool]:
    out = {}
    attrs = _child(m, "AttributeList")
    for b in _children(attrs, "BooleanAttribute") if attrs is not None else ():
        if b.text in ("true", "false"):
            out[b.get("Name", "")] = b.text == "true"
    return out


def _members(parent: ET.Element, section: str) -> list[Member]:
    out = []
    for m in _children(parent, "Member"):
        flags = _bool_attrs(m)
        start = _child(m, "StartValue")
        nested = list(_members(m, section))
        sections = _child(m, "Sections")  # multi-instance / UDT instance members
        for s in _children(sections, "Section") if sections is not None else ():
            nested += _members(s, _SECTIONS.get(s.get("Name", ""), section))
        retain = m.get("Remanence")
        out.append(
            Member(
                name=m.get("Name", "?"),
                data_type=m.get("Datatype", "?"),
                section=section,
                start_value=start.text if start is not None else None,
                comment=_member_comment(m),
                retain=None if retain is None else retain == "Retain",
                accessible=flags.get("ExternalAccessible"),
                visible=flags.get("ExternalVisible"),
                writable=flags.get("ExternalWritable"),
                members=nested,
            )
        )
    return out


def interface(block_attrs: ET.Element) -> list[Member]:
    itf = _child(block_attrs, "Interface")
    sections = None
    if itf is not None:
        sections = next((e for e in itf.iter() if _local(e.tag) == "Sections"), None)
    out: list[Member] = []
    for s in _children(sections, "Section") if sections is not None else ():
        sec = _SECTIONS.get(s.get("Name", ""))
        if sec is None:  # "None" section of UDTs/global DBs: plain members
            sec = "STATIC"
        out += _members(s, sec)
    return out


# ------------------------------------------------------------------ operands
def operand(access: ET.Element) -> str:
    """``<Access Scope=…>`` → operand text (``#local``, ``"Global".member``, ``%I0.0``, 5)."""
    scope = access.get("Scope", "")
    const = _child(access, "Constant")
    if const is not None:
        value = _text(const, "ConstantValue") or ""
        typ = _text(const, "ConstantType")
        return (
            f"{typ}#{value}"
            if typ and typ not in ("Int", "Bool", "Real", "DInt") and "#" not in value
            else value
        )
    address = _child(access, "Address")
    if address is not None:
        return f"%{address.get('Area', '')}{address.get('BitOffset', '')}"
    symbol = _child(access, "Symbol")
    if symbol is None:
        if _child(access, "Component") is None:
            return f"<{scope}>"
        symbol = access  # e.g. <Instance Scope=…><Component …/></Instance>
    parts = []
    for comp in _children(symbol, "Component"):
        name = comp.get("Name", "?")
        index = [operand(a) for a in _children(comp, "Access")]
        parts.append(f"{name}[{', '.join(index)}]" if index else name)
    if scope in ("GlobalVariable", "GlobalConstant") and parts:
        parts[0] = f'"{parts[0]}"'
    text = ".".join(parts)
    return f"#{text}" if scope in ("LocalVariable", "LocalConstant") else text


# ------------------------------------------------------------------ FlgNet (LAD/FBD) → NTN
class _Net:
    def __init__(self, flgnet: ET.Element) -> None:
        self.parts: dict[str, ET.Element] = {}
        self.access: dict[str, str] = {}
        parts = _child(flgnet, "Parts")
        for p in parts if parts is not None else ():
            uid = p.get("UId", "")
            if _local(p.tag) == "Access":
                self.access[uid] = operand(p)
            else:
                self.parts[uid] = p
        # inputs[(part, pin)] = list of sources: "POWER", ("ident", operand) or ("out", part, pin)
        self.inputs: dict[tuple[str, str], list[Any]] = {}
        self.fanout: dict[tuple[str, str], int] = {}
        wires = _child(flgnet, "Wires")
        for w in wires if wires is not None else ():
            ends = list(w)
            sources: list[Any] = []
            sinks: list[tuple[str, str]] = []
            for e in ends:
                tag = _local(e.tag)
                if tag == "Powerrail":
                    sources.append("POWER")
                elif tag == "IdentCon":
                    sources.append(("ident", self.access.get(e.get("UId", ""), "?")))
                elif tag == "OpenCon":
                    continue
                elif tag == "NameCon":
                    uid, pin = e.get("UId", ""), e.get("Name", "")
                    part = self.parts.get(uid)
                    if part is not None and _is_output(part, pin):
                        sources.append(("out", uid, pin))
                    else:
                        sinks.append((uid, pin))
            for s in sinks:
                self.inputs.setdefault(s, []).extend(sources)
            for src in sources:
                if isinstance(src, tuple) and src[0] == "out":
                    key = (src[1], src[2])
                    self.fanout[key] = self.fanout.get(key, 0) + len(sinks)
        self.partial = False
        # operands written by box outputs: wires NameCon(box, outpin) + IdentCon(operand)
        self.writes: dict[tuple[str, str], list[str]] = {}
        for w in wires if wires is not None else ():
            names = [e for e in w if _local(e.tag) == "NameCon"]
            idents = [e for e in w if _local(e.tag) == "IdentCon"]
            for nc in names:
                part = self.parts.get(nc.get("UId", ""))
                if part is not None and _is_output(part, nc.get("Name", "")):
                    for ic in idents:
                        key = (nc.get("UId", ""), nc.get("Name", ""))
                        self.writes.setdefault(key, []).append(
                            self.access.get(ic.get("UId", ""), "?")
                        )

    def pin(self, uid: str, pin: str) -> str | None:
        sources = self.inputs.get((uid, pin))
        if not sources:
            return None
        exprs = []
        for s in sources:
            if s == "POWER":
                exprs.append("TRUE")
            elif s[0] == "ident":
                exprs.append(s[1])
            else:
                exprs.append(self.out(s[1], s[2]))
        if len(exprs) == 1:
            return exprs[0]
        return ntn.or_(*exprs)

    def flow_in(self, uid: str) -> str | None:
        """Power flow into a part: ``in`` for contacts and coils, ``en`` for boxes."""
        name = self.parts[uid].get("Name", "")
        return self.pin(uid, "in") if name in _FLOW_PARTS else self.pin(uid, "en")

    def out(self, uid: str, pin: str) -> str:
        part = self.parts[uid]
        name = part.get("Name", "")
        if name == "Contact":
            op = self.pin(uid, "operand") or "?"
            if _negated(part, "operand"):
                op = ntn.not_(op)
            flow = self.flow_in(uid)
            return op if flow in (None, "TRUE") else ntn.and_(flow, op)
        if name in _COMPARE:
            left, right = self.pin(uid, "in1") or "?", self.pin(uid, "in2") or "?"
            cmp = ntn.compare(left, _COMPARE[name], right)
            flow = self.pin(uid, "pre")
            return cmp if flow in (None, "TRUE") else ntn.and_(flow, f"({cmp})")
        if name in ("PContact", "NContact"):  # edge contact on the operand
            op = self.pin(uid, "operand") or "?"
            edge = self.pin(uid, "bit") or "?"
            trig = ntn.p_trig(edge, op) if name == "PContact" else ntn.n_trig(edge, op)
            flow = self.flow_in(uid)
            return trig if flow in (None, "TRUE") else ntn.and_(flow, trig)
        if name in ("PBox", "NBox", "P_TRIG", "N_TRIG"):
            edge = self.pin(uid, "bit") or "?"
            flow = self.pin(uid, "in") or self.flow_in(uid) or "TRUE"  # FBD: signal on "in"
            return ntn.p_trig(edge, flow) if name in ("PBox", "P_TRIG") else ntn.n_trig(edge, flow)
        if name in ("And", "A"):
            ins = [self.pin(uid, p) for p in _in_pins(part, self.inputs, uid)]
            return ntn.and_(*[i for i in ins if i]) if any(ins) else "?"
        if name in ("O", "Or"):
            ins = [self.pin(uid, p) for p in _in_pins(part, self.inputs, uid)]
            return ntn.or_(*[i for i in ins if i]) if any(ins) else "?"
        if name in ("NOT", "Not"):
            return ntn.not_(self.flow_in(uid) or "?")
        # boxes with an ENO or a value output: refer to the box output by name
        return f"{name}#{uid}.{pin}"

    def statements(self) -> list[str]:
        out: list[str] = []
        for uid, part in sorted(
            self.parts.items(), key=lambda kv: int(kv[0]) if kv[0].isdigit() else 0
        ):
            name = part.get("Name", "")
            flow = self.flow_in(uid)
            guard = "" if flow in (None, "TRUE") else f"IF {flow} THEN "
            end = "" if not guard else " END_IF;"
            if name == "Coil":
                target = self.pin(uid, "operand") or "?"
                expr = flow or "TRUE"
                out.append(
                    ntn.assign(target, ntn.not_(expr) if _negated(part, "operand") else expr)
                )
            elif name == "SCoil":
                out.append(guard + ntn.set_(self.pin(uid, "operand") or "?") + end)
            elif name == "RCoil":
                out.append(guard + ntn.reset(self.pin(uid, "operand") or "?") + end)
            elif name == "TrCoil":  # GRAPH transition condition
                out.append(f"CONDITION {flow or 'TRUE'};")
            elif name == "Move":
                src = self.pin(uid, "in") or "?"
                dests = self.writes.get((uid, "out1"), []) or ["?"]
                for d in dests:
                    out.append(guard + ntn.move(src, d) + end)
            elif _is_call(part):
                out.append(guard + self._call(uid, part) + end)
            elif name in _EXPRESSION_PARTS or name in _COMPARE:
                continue  # inside expressions
            else:  # any other instruction box: all wired inputs and the operands it writes
                pins = sorted({p for (u, p) in self.inputs if u == uid and p != "en"})
                args = [f"{p} := {v}" for p in pins if (v := self.pin(uid, p)) is not None]
                for (u, p), targets in sorted(self.writes.items()):
                    if u == uid and p != "eno":
                        args += [f"{p} => {t}" for t in targets]
                out.append(f"{guard}{name}({', '.join(args)});{end}")
        return out or [ntn.empty()]

    def _call(self, uid: str, part: ET.Element) -> str:
        info = _child(part, "CallInfo")
        block = info.get("Name", "?") if info is not None else part.get("Name", "?")
        inst = None
        inst_el = _child(info, "Instance") if info is not None else None
        if inst_el is not None:
            comps = [c.get("Name", "?") for c in inst_el.iter() if _local(c.tag) == "Component"]
            if comps:
                inst = ("#" if inst_el.get("Scope") == "LocalVariable" else "") + ".".join(
                    f'"{c}"' if i == 0 and inst_el.get("Scope") == "GlobalVariable" else c
                    for i, c in enumerate(comps)
                )
        inputs: list[ntn.Param] = []
        outputs: list[ntn.Param] = []
        inouts: list[ntn.Param] = []
        params = [
            p for p in (info.iter() if info is not None else ()) if _local(p.tag) == "Parameter"
        ]
        for p in params:
            pname, section = p.get("Name", "?"), p.get("Section", "Input")
            if section == "Output":
                for t in self.writes.get((uid, pname), []):
                    outputs.append((pname, t))
            else:
                v = self.pin(uid, pname)
                if v is not None:
                    (inouts if section == "InOut" else inputs).append((pname, v))
        name = f'"{block}"' if info is not None and info.get("BlockType") in ("FB", "FC") else block
        return ntn.call(name, inst, inputs, outputs, inouts)


def _negated(part: ET.Element, pin: str) -> bool:
    return any(_local(n.tag) == "Negated" and n.get("Name") == pin for n in part)


def _is_call(part: ET.Element) -> bool:
    return _local(part.tag) == "Call" or _child(part, "CallInfo") is not None


def _in_pins(part: ET.Element, inputs: dict[tuple[str, str], list[Any]], uid: str) -> list[str]:
    return sorted(p for (u, p) in inputs if u == uid and p.startswith("in"))


_FLOW_PARTS = frozenset(
    {"Contact", "PContact", "NContact", "Coil", "SCoil", "RCoil", "TrCoil", "PCoil", "NCoil"}
)
_EXPRESSION_PARTS = frozenset(
    {"Contact", "PContact", "NContact", "PBox", "NBox", "P_TRIG", "N_TRIG", "And", "A", "O",
     "Or", "NOT", "Not"}
)  # fmt: skip
_OUTPUT_PINS = re.compile(r"^(out\d*|eno|Q|ET|CV|CU|CD)$")


def _is_output(part: ET.Element, pin: str) -> bool:
    if _is_call(part):
        info = _child(part, "CallInfo")
        for p in info.iter() if info is not None else ():
            if _local(p.tag) == "Parameter" and p.get("Name") == pin:
                return p.get("Section") == "Output"
        return pin in ("eno", "ENO")
    return bool(_OUTPUT_PINS.match(pin))


def flgnet(net: ET.Element) -> tuple[str, bool]:
    """LAD/FBD network → (NTN code, partial)."""
    n = _Net(net)
    return "\n".join(n.statements()), n.partial


# ------------------------------------------------------------------ text languages
def structured_text(st: ET.Element) -> str:
    """SCL ``<StructuredText>`` (tokens, blanks, new lines, accesses, comments) → source text."""
    out: list[str] = []
    for e in st:
        tag = _local(e.tag)
        if tag == "Token":
            out.append(e.get("Text", ""))
        elif tag == "Blank":
            out.append(" " * int(e.get("Num", "1")))
        elif tag == "NewLine":
            out.append("\n" * int(e.get("Num", "1")))
        elif tag == "Access":
            out.append(_scl_call(e) if e.get("Scope") == "Call" else operand(e))
        elif tag in ("LineComment", "Comment"):
            text = "".join(t.text or "" for t in e.iter() if _local(t.tag) in ("Text", "Token"))
            out.append(f"//{text}" if tag == "LineComment" else f"(*{text}*)")
        elif tag == "Text":
            out.append(e.text or "")
    return "".join(out).rstrip()


def _scl_call(access: ET.Element) -> str:
    """SCL call: ``<Access Scope="Call">`` with ``<CallInfo>`` (blocks; FCs name themselves in
    ``<Instance>``) or ``<Instruction>`` (system instructions, nested freely) → ``Name(p := v)``."""
    info = _child(access, "CallInfo")
    instruction = _child(access, "Instruction")
    node = info if info is not None else instruction
    if node is None:
        return "<call>"
    name = node.get("Name", "")
    inst = _child(node, "Instance")
    if inst is not None:
        comps = [c.get("Name", "?") for c in inst.iter() if _local(c.tag) == "Component"]
        scope = inst.get("Scope", "")
        name = ".".join(comps) or name
        if scope == "GlobalVariable":
            name = f'"{name}"'
        elif scope == "LocalVariable":
            name = f"#{name}"
    elif info is not None and info.get("BlockType") in ("FB", "FC"):
        name = f'"{name}"'
    args = []
    for p in _children(node, "Parameter"):
        value = " ".join(structured_text(p).split())
        for arrow in (":=", "=>"):
            if value.startswith(arrow):
                args.append(f"{p.get('Name', '?')} {arrow} {value[len(arrow) :].strip()}")
                break
        else:
            args.append(value)  # positional
    return f"{name or '?'}({', '.join(args)})"


def statement_list(sl: ET.Element) -> str:
    """STL ``<StatementList>`` → one statement per line."""
    lines = []
    for stmt in _children(sl, "StlStatement"):
        words = []
        for e in stmt:
            tag = _local(e.tag)
            if tag == "StlToken":
                words.append(e.get("Text", ""))
            elif tag == "Access":
                words.append(operand(e))
            elif tag == "LabelDeclaration":
                words.insert(0, f"{_text(e, 'Label') or ''}:")
        lines.append(" ".join(w for w in words if w))
    return "\n".join(lines)


def _tokens(e: ET.Element) -> str:
    """An action's token stream as one line: ``//`` comments become ``(* … *)`` so that joining
    the lines cannot turn the following statement into comment text; runs of blanks shrink."""
    text = "".join(t.get("Text", "") for t in e if _local(t.tag) == "Token")
    lines = []
    for line in text.splitlines():
        code, sep, note = line.partition("//")
        line = code + (f"(* {note.strip()} *)" if sep and note.strip() else "")
        lines.append(" ".join(line.split()))
    return " ".join(x for x in lines if x)


# ------------------------------------------------------------------ GRAPH → NTN §6.1
def graph(sequence: ET.Element) -> tuple[str, bool]:
    lines: list[str] = []
    partial = False
    steps = {s.get("Number", ""): s for s in _items(_child(sequence, "Steps"))}
    names = {num: s.get("Name", f"Step{num}") for num, s in steps.items()}
    for num, s in steps.items():
        lines.append(ntn.step(_ident(names[num]), s.get("Init") == "true"))
        actions = _child(s, "Actions")
        for a in _children(actions, "Action") if actions is not None else ():
            q = a.get("Qualifier", "N")
            body = _tokens(a)
            if not body:
                continue  # empty action line in the GRAPH editor
            if q not in ntn.SFC_QUALIFIERS:
                partial = True
                lines.append(f"  ACTION {q} {{ {body} }}")
            elif q in ("L", "D"):
                lines.append(f"  ACTION {q} {{ {body} }}")  # time is part of the statement in GRAPH
            else:
                lines.append(ntn.action(q, body, inline=True))
    transitions: dict[str, tuple[str, str]] = {}
    for t in _items(_child(sequence, "Transitions")):
        net = _child(t, "FlgNet")
        cond = "TRUE"
        if net is not None:
            code, p = flgnet(net)
            partial |= p
            m = re.search(r"CONDITION (.*);", code)
            cond = m.group(1) if m else "TRUE"
        transitions[t.get("Number", "")] = (t.get("Name", ""), cond)
    # the sequence as a graph: steps, transitions, branch nodes (AltBegin/AltEnd, SimBegin/SimEnd)
    # and the end; a transition's steps are found through any branch nodes in between
    succ: dict[tuple[str, str], list[tuple[str, str]]] = {}
    pred: dict[tuple[str, str], list[tuple[str, str]]] = {}
    for c in _items(_child(sequence, "Connections")):
        frm, to = _node(_child(c, "NodeFrom")), _node(_child(c, "NodeTo"))
        if frm is None or to is None:
            continue
        succ.setdefault(frm, []).append(to)
        pred.setdefault(to, []).append(frm)

    def reach(
        start: tuple[str, str], edges: dict[tuple[str, str], list[tuple[str, str]]]
    ) -> list[str]:
        out: list[str] = []
        todo, seen = list(edges.get(start, [])), set()
        while todo:
            node = todo.pop(0)
            if node in seen:
                continue
            seen.add(node)
            if node[0] == "branch":
                todo += edges.get(node, [])
            elif node[0] == "step":
                out.append(names.get(node[1], "?"))
            elif node[0] == "end":
                out.append("END")  # end of the sequence
        return out

    src = {num: reach(("transition", num), pred) for num in transitions}
    dst = {num: reach(("transition", num), succ) for num in transitions}
    for num, (tname, cond) in sorted(
        transitions.items(), key=lambda kv: int(kv[0]) if kv[0].isdigit() else 0
    ):
        frm_steps = [_ident(s) for s in src.get(num) or ["?"]]
        to_steps = [s if s == "END" else _ident(s) for s in dst.get(num) or ["?"]]
        lines.append(
            ntn.comment(
                ntn.transition(
                    frm_steps if len(frm_steps) > 1 else frm_steps[0],
                    to_steps if len(to_steps) > 1 else to_steps[0],
                    cond,
                ),
                tname,
            )
        )
    return "\n".join(lines) or ntn.empty(), partial


def _node(end: ET.Element | None) -> tuple[str, str] | None:
    """A connection end of a GRAPH sequence as (kind, number)."""
    if end is None:
        return None
    for tag, kind in (
        ("StepRef", "step"),
        ("TransitionRef", "transition"),
        ("BranchRef", "branch"),
    ):
        ref = _child(end, tag)
        if ref is not None:
            return kind, ref.get("Number", "")
    return ("end", "") if _child(end, "EndConnection") is not None else None


def _ident(name: str) -> str:
    """GRAPH step names may contain spaces and colons; quote them like other names."""
    return name if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) else f'"{name}"'


# ------------------------------------------------------------------ whole document
@dataclass
class ParsedUnit:
    name: str
    kind: str
    number: int | None
    language: str
    title: dict[str, str]
    comment: dict[str, str]
    members: list[Member]
    body: UnitBody
    partial: bool
    attributes: dict[str, str]


def _body_language(kinds: list[str], text_langs: set[str]) -> BodyLanguage:
    """One language per body: a block made only of SCL (or only STL) networks keeps it; a block
    with graphical networks is NTN (its SCL networks are NTN-compatible statements)."""
    if not kinds:
        return "none"
    if all(k == "text" for k in kinds) and len(text_langs) == 1:
        return "scl" if "scl" in text_langs else "stl"
    return "ntn"


def _block_element(root: ET.Element) -> ET.Element:
    for e in root:
        if _local(e.tag) in _KINDS:
            return e
    # a library type version (``LibraryTypeVersion.Export``) wraps the block:
    # <SW.Blocks.CodeBlockLibraryTypeVersion><ObjectList><SW.Blocks.FB CompositionName=
    # "ContentObject"> (first seen on TIA V21 with the LBCFC library)
    for wrapper in root:
        if not _local(wrapper.tag).endswith("LibraryTypeVersion"):
            continue
        for objects in wrapper:
            if _local(objects.tag) != "ObjectList":
                continue
            for e in objects:
                if _local(e.tag) in _KINDS:
                    return e
    raise ValueError("no block or PLC data type in this SimaticML document")


def parse_unit(data: bytes) -> ParsedUnit:
    root = SafeET.fromstring(data)  # untrusted project data: no entities, no DTDs
    blk = _block_element(root)
    attrs = _child(blk, "AttributeList")
    assert attrs is not None
    language = _text(attrs, "ProgrammingLanguage") or (
        "UDT" if _local(blk.tag) == "SW.Types.PlcStruct" else "DB"
    )
    networks: list[BodyNetwork] = []
    partial = False
    text_langs: set[str] = set()
    kinds: list[str] = []
    objects = _child(blk, "ObjectList")
    units = [
        c
        for c in (objects if objects is not None else [])
        if _local(c.tag) == "SW.Blocks.CompileUnit"
    ]
    for i, cu in enumerate(units, start=1):
        cu_attrs = _child(cu, "AttributeList")
        source = _child(cu_attrs, "NetworkSource") if cu_attrs is not None else None
        lang = _text(cu_attrs, "ProgrammingLanguage") or language
        code = ntn.empty()
        kind = "graph"
        if source is not None:
            inner = next(iter(source), None)
            tag = _local(inner.tag) if inner is not None else ""
            if tag == "FlgNet" and inner is not None:
                code, p = flgnet(inner)
                partial |= p
            elif tag == "StructuredText" and inner is not None:
                code = structured_text(inner)
                text_langs.add("scl")
                kind = "text"
            elif tag == "StatementList" and inner is not None:
                code = statement_list(inner)
                text_langs.add("stl")
                kind = "text"
            elif tag == "Graph" and inner is not None:
                seq = next((e for e in inner.iter() if _local(e.tag) == "Sequence"), None)
                if seq is not None:
                    code, p = graph(seq)
                    partial |= p
            elif inner is not None:
                partial = True
                code = f"// {tag} network ({lang}) not rendered"
        kinds.append(kind)
        networks.append(
            BodyNetwork(i, code, multilingual(cu, "Title"), multilingual(cu, "Comment"))
        )
    number = _text(attrs, "Number")
    attributes = {
        k: v
        for k, v in (
            ("family", _text(attrs, "HeaderFamily")),
            ("version", _text(attrs, "HeaderVersion")),
            ("author", _text(attrs, "HeaderAuthor")),
        )
        if v
    }
    return ParsedUnit(
        name=_text(attrs, "Name") or "?",
        kind=_KINDS[_local(blk.tag)],
        number=int(number) if number and number.isdigit() else None,
        language=language,
        title=multilingual(blk, "Title"),
        comment=multilingual(blk, "Comment"),
        members=interface(attrs),
        body=UnitBody(_body_language(kinds, text_langs), tuple(networks)),
        partial=partial,
        attributes=attributes,
    )


# ------------------------------------------------------------------ tag tables
@dataclass
class Tag:
    name: str
    data_type: str
    address: str | None
    comment: dict[str, str]
    constant: bool = False
    value: str | None = None
    accessible: bool | None = None
    visible: bool | None = None
    writable: bool | None = None


def parse_tag_table(data: bytes) -> tuple[str, list[Tag]]:
    root = SafeET.fromstring(data)  # untrusted project data: no entities, no DTDs
    table = next(e for e in root if _local(e.tag) == "SW.Tags.PlcTagTable")
    name = _text(_child(table, "AttributeList"), "Name") or "?"
    tags: list[Tag] = []
    objects = _child(table, "ObjectList")
    for t in objects if objects is not None else []:
        kind = _local(t.tag)
        if kind not in ("SW.Tags.PlcTag", "SW.Tags.PlcUserConstant"):
            continue
        a = _child(t, "AttributeList")

        def flag(n: str, a: ET.Element | None = a) -> bool | None:
            v = _text(a, n)
            return None if v is None else v == "true"

        tags.append(
            Tag(
                name=_text(a, "Name") or "?",
                data_type=_text(a, "DataTypeName") or "?",
                address=_text(a, "LogicalAddress"),
                comment=multilingual(t, "Comment"),
                constant=kind == "SW.Tags.PlcUserConstant",
                value=_text(a, "Value"),
                accessible=flag("ExternalAccessible"),
                visible=flag("ExternalVisible"),
                writable=flag("ExternalWritable"),
            )
        )
    return name, sorted(tags, key=lambda t: t.name)


# ------------------------------------------------------------------ interface -> variables
def member_variables(
    unit: str, scope: Scope, parent: str, members: list[Member], top: bool = True
) -> list[ExportVariable]:
    """Interface members as variables: ``"<unit>".a``, ``"<unit>".a.b``, …"""
    out: list[ExportVariable] = []
    for mb in members:
        path = f"{parent}.{mb.name}"
        out.append(
            ExportVariable(
                declared_in=unit,
                scope=scope,
                symbolic_path=path,
                data_type=mb.data_type,
                section=cast(Any, mb.section) if mb.section else None,
                parent_path=None if top else parent,
                start_value=mb.start_value,
                retain=mb.retain,
                ext_accessible=mb.accessible,
                ext_visible=mb.visible,
                ext_writable=mb.writable,
                comments=dict(mb.comment),
            )
        )
        out += member_variables(unit, scope, path, mb.members, False)
    return out
