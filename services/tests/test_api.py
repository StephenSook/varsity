from fastapi.testclient import TestClient

from app.main import app


def test_health() -> None:
    """Exercises the whole backend import chain (pipeline, llm, rag, triggers) + the app."""
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
