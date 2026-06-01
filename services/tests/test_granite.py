import app.llm.granite as granite_mod
from app.llm.granite import GraniteClient


def test_explain_offside_retries_then_returns_good(monkeypatch) -> None:
    calls = {"n": 0}

    def fake_gen(model_id, prompt, **kwargs):
        calls["n"] += 1
        if calls["n"] < 2:
            return ""  # first attempt empty
        return "Under Law 11, the attacker was offside by 5.45 meters."

    monkeypatch.setattr(granite_mod._watsonx, "generate", fake_gen)
    out = GraniteClient().explain_offside(
        margin_meters=5.45, is_offside=True, law_text="Law 11 ..."
    )
    assert "Law 11" in out
    assert calls["n"] == 2  # retried once


def test_explain_offside_falls_back_when_always_empty(monkeypatch) -> None:
    monkeypatch.setattr(granite_mod._watsonx, "generate", lambda *a, **k: "")
    out = GraniteClient().explain_offside(
        margin_meters=5.45, is_offside=True, law_text="Law 11 ..."
    )
    assert out.strip() != ""
    assert "Law 11" in out  # deterministic fallback cites the Law
    assert "5.45" in out  # and states the margin
