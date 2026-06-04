"""Tests for the live-feed robustness layer: normalized schema + adapters, multi-source
fusion confidence, speculative pre-warm, and the honest latency model."""

from app import latency
from app.geometry import FreezeFramePlayer
from app.pipeline import explanation_stages
from app.triggers.fusion import fuse
from app.triggers.prewarm import PreWarmCache, branch_key
from app.triggers.schema import (
    REVIEW_RESOLVED,
    REVIEW_STARTED,
    VARDecisionEvent,
    dedup_and_sort,
    normalize,
    normalize_all,
)
from app.triggers.sportmonks import VarEvent

# --- normalized schema + adapters -------------------------------------------------

def test_normalize_started_withholds_outcome() -> None:
    ev = VarEvent(fixture_id=99, minute=23, type_name="Goal Under Review", detail=None, event_id=10)
    n = normalize(ev, "sportmonks")
    assert n.phase == REVIEW_STARTED
    assert n.outcome is None  # no prediction during the review
    assert n.event_id == "sportmonks:99:10"  # adapter-prefixed
    assert n.transitional is True


def test_normalize_resolved_carries_outcome_and_reason() -> None:
    detail = "Goal disallowed - offside"
    ev = VarEvent(fixture_id=99, minute=23, type_name="Goal Disallowed", detail=detail)
    n = normalize(ev, "api-football")
    assert n.phase == REVIEW_RESOLVED
    assert n.outcome == "Goal disallowed - offside"
    assert n.review_reason == "Offside"
    assert n.source == "api-football"


def test_dedup_on_event_id_and_sort_by_sort_order() -> None:
    a = VarEvent(fixture_id=1, minute=20, type_name="Var", detail="b", event_id=5, sort_order=2)
    b = VarEvent(fixture_id=1, minute=10, type_name="Var", detail="a", event_id=4, sort_order=1)
    dup = VarEvent(fixture_id=1, minute=20, type_name="Var", detail="b", event_id=5, sort_order=2)
    out = dedup_and_sort(normalize_all([a, b, dup], "sportmonks"))
    assert len(out) == 2  # the duplicate id collapsed
    assert [e.sort_order for e in out] == [1, 2]  # sorted by sort_order, NOT minute


# --- multi-source fusion confidence -----------------------------------------------

def _resolved(source: str, outcome: str, fixture: int = 1, minute: int = 23) -> VARDecisionEvent:
    ev = VarEvent(fixture_id=fixture, minute=minute, type_name="Var", detail=outcome)
    return normalize(ev, source)


def test_fusion_single_source_resolved() -> None:
    fused = fuse([_resolved("sportmonks", "Goal Disallowed - offside")])
    assert len(fused) == 1
    assert fused[0].confidence == 0.85
    assert fused[0].conflict is False
    assert "sportmonks" in fused[0].hedge


def test_fusion_two_sources_agree_raises_confidence() -> None:
    fused = fuse(
        [
            _resolved("sportmonks", "Goal Disallowed - offside"),
            _resolved("api-football", "Goal Disallowed - offside"),
        ]
    )
    assert fused[0].confidence == 0.91  # 0.85 + one agreement bonus
    assert fused[0].conflict is False
    assert "multiple feeds" in fused[0].hedge


def test_fusion_conflict_stays_unconfirmed_never_picks() -> None:
    fused = fuse(
        [
            _resolved("sportmonks", "Goal Disallowed - offside"),
            _resolved("api-football", "Goal confirmed"),
        ]
    )
    assert fused[0].conflict is True
    assert fused[0].confidence == 0.50
    assert fused[0].outcome is None  # never adjudicates a contested call
    assert "disagree" in fused[0].hedge


def test_fusion_started_hedges_and_replay_floor_is_full_confidence() -> None:
    started = normalize(
        VarEvent(fixture_id=1, minute=23, type_name="Goal Under Review", detail=None), "sportmonks"
    )
    assert fuse([started])[0].confidence == 0.70
    assert "underway" in fuse([started])[0].hedge
    replay = normalize(
        VarEvent(fixture_id=0, minute=23, type_name="Goal Disallowed", detail="offside"),
        "replay-buffer",
    )
    assert fuse([replay])[0].confidence == 1.0


# --- speculative pre-warm ----------------------------------------------------------

class _CountingRetriever:
    def __init__(self) -> None:
        self.calls = 0

    def retrieve(self, query, **_):
        self.calls += 1
        return type("Chunk", (), {"law": "11", "title": "Offside", "text": "Law 11 text"})()


def _offside_frame() -> list[FreezeFramePlayer]:
    return [
        FreezeFramePlayer(x=100.0, y=40.0, teammate=True),
        FreezeFramePlayer(x=50.0, y=40.0, teammate=True, actor=True),
        FreezeFramePlayer(x=98.0, y=42.0, teammate=False),
        FreezeFramePlayer(x=119.0, y=40.0, teammate=False, keeper=True),
    ]


def test_prewarm_moves_retrieval_off_the_resolved_path() -> None:
    cache = PreWarmCache()
    retr = _CountingRetriever()
    cache.warm("r1", _offside_frame(), retr)
    assert retr.calls == 1  # the retrieval happened during the review gap...
    warm = cache.consume("r1")
    assert warm is not None
    assert warm.law.law == "11"
    assert warm.geometry.is_offside is True
    assert retr.calls == 1  # ...and consuming on resolution does NOT re-retrieve


def test_prewarm_prepares_both_outcome_branches() -> None:
    cache = PreWarmCache()
    warm = cache.warm("r2", _offside_frame(), _CountingRetriever())
    assert set(warm.branches) == {"goal_disallowed", "goal_confirmed"}
    assert warm.select("Goal disallowed - offside")["verdict"] == "offside"
    assert warm.select("Goal confirmed")["verdict"] == "onside"
    assert branch_key("offside") == "goal_disallowed"


def test_prewarmed_law_skips_pipeline_retrieval() -> None:
    from app.pipeline import OFFSIDE_QUERY  # noqa: F401 - import guards the constant exists

    retr = _CountingRetriever()
    warm_chunk = type("Chunk", (), {"law": "11", "title": "Offside", "text": "warmed text"})()

    class _FakeGranite:
        def explain_offside(self, *, margin_meters, is_offside, law_text, language="English", **_):
            return f"Under Law 11, offside by {abs(margin_meters):.2f} meters."

    class _FakeGuardian:
        def check(self, explanation, *, law_context=""):
            from app.llm.guardian import GuardianVerdict

            return GuardianVerdict(safe=True, cites_law=True, grounded=True, model_answer="No")

    stages = list(
        explanation_stages(
            _offside_frame(),
            retriever=retr,
            granite=_FakeGranite(),
            guardian=_FakeGuardian(),
            prewarmed_law=warm_chunk,
        )
    )
    law_stage = next(s for s in stages if s.get("stage") == "law")
    assert law_stage["text"] == "warmed text"  # the pre-warmed Law grounded the explanation
    assert retr.calls == 0  # the resolved path did NOT re-retrieve


# --- honest latency model ----------------------------------------------------------

def test_latency_beats_every_path_within_budget() -> None:
    r = latency.report(5.0)
    assert r.within_budget is True
    assert r.leads_s["ota"] == 13.0  # 18 - 5
    assert r.leads_s["streaming"] == 30.0
    assert "before the over-the-air broadcast" in r.headline


def test_latency_over_budget_and_no_negative_lead() -> None:
    r = latency.report(25.0)
    assert r.within_budget is False
    assert r.leads_s["ota"] == 0.0  # never negative
    assert "in step" in r.headline


def test_latency_payload_carries_sources_and_caveat() -> None:
    p = latency.payload(8.0)
    assert p["budget_s"] == 10.0
    assert "Phenix" in p["sources"]
    assert "field-of-play" in p["caveat"]
    assert p["broadcast_delay_s"]["ota"] == 18.0
    assert p["run"]["within_budget"] is True
