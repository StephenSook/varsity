import pytest

import app.llm.granite as granite_mod
from app.llm.granite import GraniteClient, _fallback_explanation, _looks_like_prompt_leak


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


def test_explain_offside_spanish_fallback(monkeypatch) -> None:
    monkeypatch.setattr(granite_mod._watsonx, "generate", lambda *a, **k: "")
    out = GraniteClient().explain_offside(
        margin_meters=5.45, is_offside=True, law_text="Law 11", language="Spanish"
    )
    assert "Ley 11" in out  # Spanish fallback cites the Law (Ley)
    assert "5.45" in out


@pytest.mark.parametrize(
    ("language", "needle"),
    [("French", "Loi 11"), ("Portuguese", "Lei 11"), ("German", "Regel 11"), ("English", "Law 11")],
)
def test_multilingual_fallbacks_cite_the_law(language, needle) -> None:
    out = _fallback_explanation(margin_meters=5.45, is_offside=True, language=language)
    assert needle in out
    assert "5.45" in out


def test_prompt_leak_is_rejected_then_falls_back(monkeypatch) -> None:
    # The model echoing the prompt scaffolding must not reach the user.
    monkeypatch.setattr(
        granite_mod._watsonx,
        "generate",
        lambda *a, **k: "<explanation> based on the Law. Do not invent any rule that is not...",
    )
    out = GraniteClient().explain_offside(
        margin_meters=5.45, is_offside=True, law_text="Law 11", language="Portuguese"
    )
    assert not _looks_like_prompt_leak(out)
    assert "Lei 11" in out  # fell back to the clean Portuguese floor


def test_leak_detector_passes_clean_text() -> None:
    assert not _looks_like_prompt_leak("Selon la Loi 11, l'attaquant était hors-jeu.")
    assert _looks_like_prompt_leak("Law text: ... Decision data: ...")
