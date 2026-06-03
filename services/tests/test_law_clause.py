from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_query_resolves_to_a_law_clause_with_a_citation() -> None:
    r = client.get("/law_clause", params={"q": "offside position"})
    assert r.status_code == 200
    body = r.json()
    assert body["found"] is True
    assert body["citation_id"].startswith("Law ")
    assert body["law"] and body["text"]
    assert body["source"].startswith("IFAB Laws")


def test_exact_law_number_lookup() -> None:
    r = client.get("/law_clause", params={"law": "11"})
    body = r.json()
    assert body["found"] is True
    assert body["law"] == "11"
    assert "offside" in body["text"].lower() or "offside" in body["title"].lower()


def test_unknown_law_number_is_not_found() -> None:
    r = client.get("/law_clause", params={"law": "99"})
    assert r.json()["found"] is False
