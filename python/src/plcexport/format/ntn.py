"""Network Text Notation (NTN) v1 builders (contracts/common-format.md §6, §6.1, §6.2).

Extractors use these helpers so that every platform renders graphical logic the same way.
Operands are passed through verbatim (quotes, ``#`` for locals, platform address syntax).
"""

from __future__ import annotations

from collections.abc import Sequence

Param = tuple[str, str]  # (formal parameter, actual operand)

SFC_QUALIFIERS = frozenset({"N", "S", "R", "P", "L", "D"})
_TIMED_QUALIFIERS = frozenset({"L", "D"})


# ------------------------------------------------------------------ expressions
def _has_top_level(expr: str, word: str) -> bool:
    """True if ``word`` (e.g. `` OR ``) occurs outside parentheses and quotes."""
    depth, quoted = 0, False
    for i, ch in enumerate(expr):
        if ch == '"':
            quoted = not quoted
        elif quoted:
            continue
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif depth == 0 and expr.startswith(word, i):
            return True
    return False


def _fully_wrapped(expr: str) -> bool:
    if not (expr.startswith("(") and expr.endswith(")")):
        return False
    depth = 0
    for i, ch in enumerate(expr):
        depth += (ch == "(") - (ch == ")")
        if depth == 0 and i < len(expr) - 1:
            return False
    return True


def _atomic(expr: str) -> bool:
    """An operand, a call like ``P_TRIG(..)`` or one fully parenthesized group."""
    return not _has_top_level(expr, " ") or _fully_wrapped(expr)


def and_(*operands: str) -> str:
    """Series connection: ``A AND B``."""
    if not operands:
        raise ValueError("AND needs at least one operand")
    return " AND ".join(f"({o})" if _has_top_level(o, " OR ") else o for o in operands)


def or_(*operands: str) -> str:
    """Parallel branch: ``(A AND B) OR C``."""
    if not operands:
        raise ValueError("OR needs at least one operand")
    return " OR ".join(f"({o})" if _has_top_level(o, " AND ") else o for o in operands)


def not_(operand: str) -> str:
    """Normally-closed contact or negation: ``NOT A`` / ``NOT (A OR B)``."""
    return f"NOT {operand}" if _atomic(operand) else f"NOT ({operand})"


def p_trig(edge_memory: str, expr: str) -> str:
    """Rising edge inside an expression: ``P_TRIG(M_Edge, A)``."""
    return f"P_TRIG({edge_memory}, {expr})"


def n_trig(edge_memory: str, expr: str) -> str:
    """Falling edge inside an expression: ``N_TRIG(M_Edge, A)``."""
    return f"N_TRIG({edge_memory}, {expr})"


def compare(left: str, op: str, right: str) -> str:
    """Comparison box: ``Temp > Limit``."""
    if op not in {"=", "<>", "<", "<=", ">", ">="}:
        raise ValueError(f"unknown comparison {op!r}")
    return f"{left} {op} {right}"


# ------------------------------------------------------------------ statements
def comment(statement: str, text: str | None) -> str:
    """Append an element comment: ``stmt // text`` (newlines folded into spaces)."""
    if not text:
        return statement
    return f"{statement} // {' '.join(text.split())}"


def assign(target: str, expr: str) -> str:
    """Coil: ``Q := A AND NOT B;``."""
    return f"{target} := {expr};"


def set_(target: str) -> str:
    """Set coil: ``S X;``."""
    return f"S {target};"


def reset(target: str) -> str:
    """Reset coil: ``R X;``."""
    return f"R {target};"


def move(src: str, dst: str) -> str:
    """Move box: ``MOVE(Src, Dst);``."""
    return f"MOVE({src}, {dst});"


def _params(inputs: Sequence[Param], outputs: Sequence[Param], inouts: Sequence[Param]) -> str:
    parts = [f"{p} := {a}" for p, a in inputs]
    parts += [f"{p} => {a}" for p, a in outputs]
    parts += [f"{p} <=> {a}" for p, a in inouts]
    return ", ".join(parts)


def call(
    block: str,
    instance: str | None = None,
    inputs: Sequence[Param] = (),
    outputs: Sequence[Param] = (),
    inouts: Sequence[Param] = (),
) -> str:
    """Box or call: ``CALL FB_Valve [#Heater] (Open := #HeaterOn, Position => #ValvePos);``.

    Timers and counters are calls too: ``CALL TON [#T1] (IN := Start, PT := T#5s, Q => Done);``.
    Parameters keep the order given (the order of the block interface).
    """
    inst = f" [{instance}]" if instance else ""
    return f"CALL {block}{inst} ({_params(inputs, outputs, inouts)});"


def jump(label_name: str) -> str:
    """Jump: ``JMP Label;``."""
    return f"JMP {label_name};"


def label(label_name: str) -> str:
    """Jump label: ``Label:``."""
    return f"{label_name}:"


def empty() -> str:
    """Unconnected or empty network."""
    return "// (empty network)"


# ------------------------------------------------------------------ SFC (§6.1)
def step(name: str, initial: bool = False) -> str:
    """``STEP Fill;`` / ``INITIAL STEP Idle;``."""
    return f"{'INITIAL ' if initial else ''}STEP {name};"


def action(qualifier: str, target: str, duration: str | None = None, inline: bool = False) -> str:
    """Step action, indented under its step.

    ``  ACTION N Open_Valve;``, ``  ACTION L T#5s Pulse;``, inline: ``  ACTION N { Q := TRUE; }``.
    """
    if qualifier not in SFC_QUALIFIERS:
        raise ValueError(f"unknown SFC qualifier {qualifier!r}")
    if (qualifier in _TIMED_QUALIFIERS) != (duration is not None):
        raise ValueError(
            f"qualifier {qualifier} {'needs' if duration is None else 'takes no'} time"
        )
    q = f"{qualifier} {duration}" if duration else qualifier
    body = f"{{ {target} }}" if inline else f"{target};"
    return f"  ACTION {q} {body}"


def _steps(steps: str | Sequence[str]) -> str:
    if isinstance(steps, str):
        return steps
    if len(steps) == 1:
        return steps[0]
    return f"({', '.join(steps)})"


def transition(source: str | Sequence[str], target: str | Sequence[str], condition: str) -> str:
    """``TRANSITION Idle -> Fill WHEN cond;``; tuples give simultaneous splits and joins.

    Alternative branches are several transitions from one step, emitted in priority order.
    """
    return f"TRANSITION {_steps(source)} -> {_steps(target)} WHEN {condition};"


# ------------------------------------------------------------------ CFC (§6.2)
def chart_heading(name: str) -> str:
    """Section heading of one CFC chart inside a unit body."""
    return f"## Chart {name}"


def cfc_ref(instance: str, output: str, chart: str | None = None) -> str:
    """Source of a CFC connection: ``inst.out`` or, across charts, ``chart\\inst.out``."""
    ref = f"{instance}.{output}"
    return f"{chart}\\{ref}" if chart else ref


def cfc_call(
    block_type: str,
    instance: str,
    inputs: Sequence[Param],
    seq: int,
    task: str,
    outputs: Sequence[Param] = (),
) -> str:
    """One CFC block in run sequence; unconnected inputs are simply not passed."""
    return comment(call(block_type, instance, inputs, outputs), f"seq {seq}, task {task}")
