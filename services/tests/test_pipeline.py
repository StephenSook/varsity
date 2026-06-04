from app.geometry import FreezeFramePlayer
from app.llm.guardian import GuardianVerdict, cites_law_clause
from app.pipeline import _confidence, explain_offside_decision, explanation_stages


class FakeGranite:
    def explain_offside(self, *, margin_meters, is_offside, law_text, language="English", **_):
        state = "offside" if is_offside else "onside"
        return f"Under Law 11, the attacker was {state} by {abs(margin_meters):.2f} meters."


class FakeGuardian:
    def check(self, explanation, *, law_context=""):
        cited = cites_law_clause(explanation)
        return GuardianVerdict(safe=cited, cites_law=cited, grounded=True, model_answer="No")


def _frame(att_x, def2_x, keeper_x=119.0):
    return [
        FreezeFramePlayer(x=att_x, y=40.0, teammate=True),
        FreezeFramePlayer(x=50.0, y=40.0, teammate=True, actor=True),
        FreezeFramePlayer(x=def2_x, y=42.0, teammate=False),
        FreezeFramePlayer(x=keeper_x, y=40.0, teammate=False, keeper=True),
    ]


def test_pipeline_offside_end_to_end() -> None:
    res = explain_offside_decision(
        _frame(100.0, 98.0), granite=FakeGranite(), guardian=FakeGuardian()
    )
    assert res.is_offside is True
    assert res.law == "11"
    assert res.law_title == "Offside"
    assert res.safe is True
    assert res.cites_law is True
    assert "Law 11" in res.explanation


def test_stages_order() -> None:
    frame = _frame(100.0, 98.0)
    stages = [
        s["stage"]
        for s in explanation_stages(frame, granite=FakeGranite(), guardian=FakeGuardian())
    ]
    assert stages == [
        "trigger",
        "geometry",
        "uncertainty_budget",
        "geometry_descriptors",
        "discourse",
        "signal",
        "proof",
        "verbalizer",
        "parallax",
        "causal",
        "critical_questions",
        "law",
        "granite",
        "guardian",
        "verification",
        "completeness",
        "provenance",
        "citation_metrics",
        "verdict",
    ]


def test_geometry_stage_carries_pitch_data() -> None:
    frame = _frame(100.0, 98.0)
    geo = next(
        s
        for s in explanation_stages(frame, granite=FakeGranite(), guardian=FakeGuardian())
        if s["stage"] == "geometry"
    )
    assert "offside_line_x" in geo
    assert "attacker_x" in geo
    assert geo["pitch"] == {"length": 120, "width": 80}
    assert geo["players"]
    assert all({"x", "y", "teammate"} <= set(p) for p in geo["players"])
    assert geo["confidence"] in {"clear", "tight", "very tight"}


def test_law_stage_carries_full_text_and_verdict_confidence() -> None:
    frame = _frame(100.0, 98.0)
    stages = {
        s["stage"]: s
        for s in explanation_stages(frame, granite=FakeGranite(), guardian=FakeGuardian())
    }
    assert "offside" in stages["law"]["text"].lower()  # full Law text for Detail mode
    assert stages["verdict"]["law_text"] == stages["law"]["text"]
    assert stages["verdict"]["confidence"] in {"clear", "tight", "very tight"}


def test_confidence_thresholds() -> None:
    assert _confidence(5.45) == "clear"
    assert _confidence(0.2) == "tight"  # between sigma (~0.13 m) and 2 sigma (~0.25 m)
    assert _confidence(0.1) == "very tight"  # within the measurement-noise sigma
    assert _confidence(-0.05) == "very tight"  # absolute value, onside-but-tight
