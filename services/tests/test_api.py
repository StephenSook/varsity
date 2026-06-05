import pytest
from fastapi.testclient import TestClient

from app.main import app


def test_health() -> None:
    """Exercises the whole backend import chain (pipeline, llm, rag, triggers) + the app."""
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_rag_eval_receipt_separates_the_bm25_floor_from_the_granite_path() -> None:
    # The retrieval receipt must serve the committed Hit@k/MRR AND clearly label that those numbers
    # are the BM25 offline floor, NOT the Granite-embeddings online path, so the floor is never
    # mis-credited to the embedding model (the project's own faithfulness rule).
    client = TestClient(app)
    body = client.get("/rag_eval").json()
    assert body["scored_retriever"] == "bm25 (offline)"
    assert "Granite" in body["online_retriever"]
    assert body["embedding_model"] == "ibm/granite-embedding-278m-multilingual"
    assert body["scores"]["hit_at_5"] == 1.0 and body["golden_questions"] == 20


def test_trace_returns_the_real_otel_span_tree() -> None:
    # GET /trace runs one canned explanation under OpenTelemetry and returns the real span tree
    # (geometry/law/granite/guardian) with per-stage durations, so a judge sees the instrumentation.
    client = TestClient(app)
    body = client.get("/trace").json()
    names = {s["name"] for s in body["spans"]}
    assert {"geometry", "law", "granite", "guardian"} <= names
    assert body["span_count"] >= 4
    assert all("duration_ms" in s for s in body["spans"])


@pytest.mark.parametrize(
    ("path", "key"),
    [
        ("/latency", "broadcast_delay_s"),
        ("/fusion", "primary_source"),
        ("/corpus_integrity", "verified"),
        ("/diagram_captions", "count"),
        ("/red_team", "structural_caught"),
        ("/faithfulness", "alce_per_decision"),
        ("/uncertainty", "spoken"),
    ],
)
def test_judge_route_returns_200_with_its_invariant_key(path: str, key: str) -> None:
    # The honesty moat is "every claim is a live button"; gate that the routes a judge clicks
    # actually return (these do lazy in-route imports the modules' own unit tests never exercise).
    client = TestClient(app)
    resp = client.get(path)
    assert resp.status_code == 200, f"{path} -> {resp.status_code}"
    assert key in resp.json(), f"{path} missing {key}"


def test_uncertainty_default_margin_speaks_offside_not_onside() -> None:
    # Regression: the default margin (+5.69 m) is an OFFSIDE call; the route must derive is_offside
    # from the margin sign so the spoken line never says "onside" for a positive margin.
    client = TestClient(app)
    assert "offside" in client.get("/uncertainty").json()["spoken"].lower()
    assert "onside" in client.get("/uncertainty?margin_m=-3.0").json()["spoken"].lower()


def test_models_registry_names_the_ibm_models_and_never_returns_the_key() -> None:
    # The 'best use of IBM tech' artifact: every IBM Granite-family model in one place.
    client = TestClient(app)
    body = client.get("/models").json()
    roles = {m["role"]: m["model_id"] for m in body["models"]}
    assert roles["reasoning"].startswith("ibm/granite")
    assert roles["safety"].startswith("ibm/granite-guardian")
    assert roles["embeddings"].startswith("ibm/granite-embedding")
    assert roles["vision"].startswith("ibm/granite-vision")
    assert isinstance(body["watsonx_configured"], bool)
    assert "WATSONX_API_KEY" not in str(body)  # the key value is never returned


def test_live_now_is_honest_without_a_feed_key() -> None:
    # In CI there is no API_FOOTBALL_KEY, so /live/now must report configured=False + the floor
    # note, never crash or fabricate a live match. With a key it returns real live fixtures.
    client = TestClient(app)
    body = client.get("/live/now").json()
    assert isinstance(body["configured"], bool)
    assert body["feed_ok"] is False  # no key -> not ok, the canned floor stands
    assert "fixtures" in body and isinstance(body["fixtures"], list)
    assert "note" in body


def test_live_now_reports_a_feed_failure_distinctly_and_does_not_cache_it(monkeypatch) -> None:
    # A quota / auth / network failure must NOT look like a quiet "no match live" window, and it
    # must NOT be cached, so a recovered feed is re-queried on the next click (the review's HIGH).
    from app import main as m

    class _Boom:
        def live_fixtures(self):
            raise RuntimeError("quota 429")

    m._LIVE_CACHE["data"] = None  # no stale success cache
    monkeypatch.setattr(m, "live_clients", lambda: (None, _Boom()))
    body = TestClient(app).get("/live/now").json()
    assert body["configured"] is True
    assert body["feed_ok"] is False
    assert "unavailable" in body["note"].lower()
    assert m._LIVE_CACHE["data"] is None  # the failure was not cached


def test_live_now_success_truncates_to_20_flags_var_events_and_caches(monkeypatch) -> None:
    # The success branch (feed_ok True, fixtures[:20] truncation, var_events filter,
    # cache-on-success) was untested; pin it with a stub of 25 fixtures, one with a VAR event.
    from app import main as m

    fake = [
        {"league": "L", "home": f"H{i}", "away": f"A{i}", "minute": i, "var_events": []}
        for i in range(25)
    ]
    fake[0]["var_events"] = ["Goal Disallowed - offside"]

    class _Feed:
        def live_fixtures(self):
            return fake

    m._LIVE_CACHE["data"] = None
    monkeypatch.setattr(m, "live_clients", lambda: (None, _Feed()))
    client = TestClient(app)
    body = client.get("/live/now").json()
    assert body["feed_ok"] is True
    assert body["source"] == "api-football"
    assert body["live_count"] == 25
    assert len(body["fixtures"]) == 20  # truncated
    assert len(body["var_events"]) == 1 and body["cached"] is False
    # the success is cached: a second call is served from cache (no second feed hit)
    assert client.get("/live/now").json()["cached"] is True
    m._LIVE_CACHE["data"] = None  # clean up the module cache for other tests


def test_challenge_fit_serves_primary_sourced_facts_with_their_urls() -> None:
    # Challenge Fit must be grounded, not asserted: the WHO and FIFA figures each carry the page
    # they were verified against, so a judge can check them.
    client = TestClient(app)
    body = client.get("/challenge_fit").json()
    assert "2.2 billion" in body["problem"]["stat"]
    assert body["problem"]["url"].startswith("https://www.who.int/")
    assert "104 matches" in body["moment"]["stat"]
    assert body["moment"]["url"].startswith("https://www.fifa.com/")
    assert "2026" in body["transferability"]


def test_trace_spans_carry_the_ibm_model_attributes() -> None:
    # /trace must show WHICH named Granite models ran + what Guardian returned, not just timings.
    client = TestClient(app)
    by_name = {s["name"]: s.get("attributes", {}) for s in client.get("/trace").json()["spans"]}
    assert by_name["granite"]["varsity.model"].startswith("ibm/granite")
    assert by_name["guardian"]["varsity.guardian_model"].startswith("ibm/granite-guardian")
    assert "varsity.safe" in by_name["guardian"]
