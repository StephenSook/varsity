"""Tests for the multilingual Terminology-Hit-Rate eval."""

from __future__ import annotations

from verify.multilingual_eval import evaluate


def test_every_floor_uses_the_official_terminology():
    result = evaluate()
    assert result["languages"] == 5
    assert result["overall_term_hit_rate"] == 1.0
    for row in result["rows"]:
        assert row["has_offside_term"] is True
        assert row["has_law_word"] is True
        assert row["term_hit_rate"] == 1.0


def test_multilingual_endpoint_serves_the_receipt():
    from fastapi.testclient import TestClient

    from app.main import app

    res = TestClient(app).get("/multilingual")
    assert res.status_code == 200
    j = res.json()
    assert j["overall_term_hit_rate"] == 1.0
    assert {r["lang"] for r in j["rows"]} == {"en", "es", "fr", "pt", "de"}
