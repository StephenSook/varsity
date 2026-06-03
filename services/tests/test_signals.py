from app.geometry import FreezeFramePlayer
from app.llm.guardian import GuardianVerdict, cites_law_clause
from app.pipeline import decision_stages, explanation_stages
from app.signals import referee_signal


class FakeGranite:
    def explain_offside(self, *, margin_meters, is_offside, law_text, language="English"):
        return f"Under Law 11, the attacker was {'offside' if is_offside else 'onside'}."

    def explain_decision(self, *, incident, outcome, law, law_text, language="English"):
        return f"Under Law {law}, the decision was {outcome}."


class FakeGuardian:
    def check(self, explanation, *, law_context=""):
        c = cites_law_clause(explanation)
        return GuardianVerdict(safe=c, cites_law=c, grounded=True, model_answer="No")


def _frame(att_x, def2_x):
    return [
        FreezeFramePlayer(x=att_x, y=40.0, teammate=True),
        FreezeFramePlayer(x=50.0, y=40.0, teammate=True, actor=True),
        FreezeFramePlayer(x=def2_x, y=42.0, teammate=False),
        FreezeFramePlayer(x=119.0, y=40.0, teammate=False, keeper=True),
    ]


def test_referee_signal_maps_decision_to_its_law() -> None:
    assert referee_signal(is_offside=True)["law"] == "6"  # assistant referee, Law 6
    assert referee_signal(is_offside=False)["law"] == "6"
    assert referee_signal(decision_type="penalty")["law"] == "5"  # the referee, Law 5
    assert referee_signal(decision_type="handball")["law"] == "5"
    assert "flag" in referee_signal(is_offside=True)["text"].lower()
    assert "penalty spot" in referee_signal(decision_type="penalty")["text"].lower()


def test_offside_pipeline_emits_a_referee_signal_stage() -> None:
    frame = _frame(100.0, 98.0)
    by = {
        s["stage"]: s
        for s in explanation_stages(frame, granite=FakeGranite(), guardian=FakeGuardian())
    }
    assert "signal" in by
    assert by["signal"]["law"] == "6"
    assert "raises the flag" in by["signal"]["text"]


def test_decision_pipeline_emits_a_referee_signal_stage() -> None:
    by = {
        s["stage"]: s
        for s in decision_stages("penalty", granite=FakeGranite(), guardian=FakeGuardian())
    }
    assert by["signal"]["law"] == "5"
    assert "penalty spot" in by["signal"]["text"]
