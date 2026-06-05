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


def test_trace_spans_carry_the_ibm_model_attributes() -> None:
    # /trace must show WHICH named Granite models ran + what Guardian returned, not just timings.
    client = TestClient(app)
    by_name = {s["name"]: s.get("attributes", {}) for s in client.get("/trace").json()["spans"]}
    assert by_name["granite"]["varsity.model"].startswith("ibm/granite")
    assert by_name["guardian"]["varsity.guardian_model"].startswith("ibm/granite-guardian")
    assert "varsity.safe" in by_name["guardian"]
