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
