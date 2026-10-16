"""every row of contract §6 and §6.1–6.2 (Network Text Notation v1)."""

from __future__ import annotations

import pytest

from plcexport.format import ntn


# ------------------------------------------------------------------ §6
def test_contact_and_coil() -> None:
    assert ntn.assign("Q", ntn.and_("A", ntn.not_("B"))) == "Q := A AND NOT B;"


def test_set_and_reset_coil() -> None:
    assert ntn.set_("X") == "S X;"
    assert ntn.reset("X") == "R X;"


def test_parallel_branch_parenthesizes_series_part() -> None:
    assert ntn.assign("Q", ntn.or_(ntn.and_("A", "B"), "C")) == "Q := (A AND B) OR C;"


def test_branch_inside_series_is_parenthesized() -> None:
    assert ntn.and_(ntn.or_("A", "B"), "C") == "(A OR B) AND C"


def test_not_wraps_compound_but_not_atoms() -> None:
    assert ntn.not_('"I_Stop"') == 'NOT "I_Stop"'
    assert ntn.not_("A OR B") == "NOT (A OR B)"
    assert ntn.not_("(A OR B)") == "NOT (A OR B)"
    assert ntn.not_("(A) AND (B)") == "NOT ((A) AND (B))"
    assert ntn.not_("P_TRIG(M_Edge, A)") == "NOT P_TRIG(M_Edge, A)"


def test_edge_inside_expression() -> None:
    assert ntn.assign("Q", ntn.p_trig("M_Edge", "A")) == "Q := P_TRIG(M_Edge, A);"
    assert ntn.n_trig("M_Edge", "A") == "N_TRIG(M_Edge, A)"


def test_comparison() -> None:
    assert ntn.compare("Temp", ">", "Limit") == "Temp > Limit"
    with pytest.raises(ValueError):
        ntn.compare("a", "=>", "b")


def test_move() -> None:
    assert ntn.move("Src", "Dst") == "MOVE(Src, Dst);"


def test_call_with_instance_and_directions() -> None:
    stmt = ntn.call(
        "FB_Valve", "#Heater", inputs=[("Open", "#HeaterOn")], outputs=[("Position", "#ValvePos")]
    )
    assert stmt == "CALL FB_Valve [#Heater] (Open := #HeaterOn, Position => #ValvePos);"
    assert ntn.call("FC_Scale", inouts=[("Buf", "#b")]) == "CALL FC_Scale (Buf <=> #b);"


def test_timer_is_a_call() -> None:
    stmt = ntn.call("TON", "#T1", inputs=[("IN", "Start"), ("PT", "T#5s")], outputs=[("Q", "Done")])
    assert stmt == "CALL TON [#T1] (IN := Start, PT := T#5s, Q => Done);"


def test_jump_and_label() -> None:
    assert ntn.jump("Label") == "JMP Label;"
    assert ntn.label("Label") == "Label:"


def test_empty_network_and_element_comment() -> None:
    assert ntn.empty() == "// (empty network)"
    assert ntn.comment("S X;", "Start\nlatch") == "S X; // Start latch"
    assert ntn.comment("S X;", None) == "S X;"


def test_operands_are_verbatim() -> None:
    assert ntn.assign('"DB_Recipe".Counter', "%I0.0") == '"DB_Recipe".Counter := %I0.0;'


# ------------------------------------------------------------------ §6.1 SFC
def test_steps() -> None:
    assert ntn.step("Fill") == "STEP Fill;"
    assert ntn.step("Idle", initial=True) == "INITIAL STEP Idle;"


def test_actions_with_qualifiers() -> None:
    assert ntn.action("N", "Open_Valve") == "  ACTION N Open_Valve;"
    assert ntn.action("L", "Pulse", duration="T#5s") == "  ACTION L T#5s Pulse;"
    assert ntn.action("N", "Q_Valve := TRUE;", inline=True) == "  ACTION N { Q_Valve := TRUE; }"
    with pytest.raises(ValueError):
        ntn.action("X", "A")
    with pytest.raises(ValueError):
        ntn.action("D", "A")  # D needs a time
    with pytest.raises(ValueError):
        ntn.action("N", "A", duration="T#1s")


def test_transitions_alternative_simultaneous_and_jump() -> None:
    assert (
        ntn.transition("Idle", "Fill", "I_Start AND NOT I_Fault")
        == "TRANSITION Idle -> Fill WHEN I_Start AND NOT I_Fault;"
    )
    assert ntn.transition("Fill", ("Heat", "Stir"), "Full") == (
        "TRANSITION Fill -> (Heat, Stir) WHEN Full;"
    )
    assert ntn.transition(("Heat", "Stir"), "Drain", "Done") == (
        "TRANSITION (Heat, Stir) -> Drain WHEN Done;"
    )
    assert ntn.transition("Drain", "Idle", "Empty") == "TRANSITION Drain -> Idle WHEN Empty;"


# ------------------------------------------------------------------ §6.2 CFC
def test_cfc_chart_and_calls() -> None:
    assert ntn.chart_heading("Mixer1") == "## Chart Mixer1"
    src = ntn.cfc_ref("PID1", "LMN")
    assert src == "PID1.LMN"
    assert ntn.cfc_ref("AI1", "V", chart="Inputs") == "Inputs\\AI1.V"
    stmt = ntn.cfc_call("CTRL_PID", "PID1", [("PV_IN", "Inputs\\AI1.V")], seq=3, task="OB35")
    assert stmt == "CALL CTRL_PID [PID1] (PV_IN := Inputs\\AI1.V); // seq 3, task OB35"
