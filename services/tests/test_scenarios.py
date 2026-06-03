import json
import pathlib

from fastapi.testclient import TestClient

from app import scenarios
from app.geometry import compute_offside
from app.llm.guardian import GuardianVerdict, cites_law_clause
from app.main import app
from app.pipeline import explanation_stages

FIX = pathlib.Path(__file__).parent / "fixtures"


class FakeGranite:
    def explain_offside(self, *, margin_meters, is_offside, law_text, language="English"):
        state = "offside" if is_offside else "onside"
        return f"Under Law 11, the attacker was {state} by {abs(margin_meters):.2f} meters."


class FakeGuardian:
    def check(self, explanation, *, law_context=""):
        c = cites_law_clause(explanation)
        return GuardianVerdict(safe=c, cites_law=c, grounded=True, model_answer="No")


def test_three_real_scenarios_reproduce_their_computed_verdict() -> None:
    """Each scenario is a real StatsBomb 360 frame; the geometry RE-DERIVES the stored
    verdict/margin, proving they were computed, not hardcoded."""
    expected = {"offside": True, "onside": False, "tight": True}
    for name in scenarios.scenario_names():
        data = json.loads((FIX / f"wc2022_{name}_frame.json").read_text())
        res = compute_offside(scenarios.load_frame(name))
        assert res.is_offside == data["expected_is_offside"]
        assert round(res.margin_meters, 2) == round(data["expected_margin_meters"], 2)
        assert res.is_offside == expected[name]


def test_verdicts_actually_differ() -> None:
    """The engine returns DIFFERENT real answers across scenarios (not one fixed offside)."""
    assert compute_offside(scenarios.load_frame("offside")).is_offside is True
    assert compute_offside(scenarios.load_frame("onside")).is_offside is False
    tight = compute_offside(scenarios.load_frame("tight"))
    assert abs(tight.margin_meters) <= 0.2  # the razor-tight VAR call


def test_trigger_meta_carries_world_cup_byline() -> None:
    m = scenarios.trigger_meta("onside")
    assert m["scenario"] == "onside"
    assert m["match_name"] == "Canada vs Morocco"
    assert m["competition"] == "FIFA World Cup 2022"
    assert m["year"] == 2022
    assert m["expected_is_offside"] is False


def test_unknown_scenario_falls_back_to_default() -> None:
    assert scenarios.trigger_meta("bogus")["scenario"] == scenarios.DEFAULT_SCENARIO
    assert scenarios.load_frame("bogus")  # no error, returns the default frame


def test_trigger_stage_includes_scenario_meta() -> None:
    frame = scenarios.load_frame("tight")
    trigger = next(
        s
        for s in explanation_stages(
            frame,
            granite=FakeGranite(),
            guardian=FakeGuardian(),
            trigger_meta=scenarios.trigger_meta("tight"),
        )
        if s["stage"] == "trigger"
    )
    assert trigger["scenario"] == "tight"
    assert trigger["source"] == "StatsBomb 360 (canned)"
    assert trigger["match_name"] == "Canada vs Morocco"


def test_scenarios_endpoint_lists_three() -> None:
    client = TestClient(app)
    resp = client.get("/scenarios")
    assert resp.status_code == 200
    items = resp.json()["scenarios"]
    assert {s["scenario"] for s in items} == {"offside", "onside", "tight"}
    assert all(s["match_name"] == "Canada vs Morocco" for s in items)
