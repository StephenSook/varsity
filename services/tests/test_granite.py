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
    assert "Regla 11" in out  # Spanish fallback cites the Law (official IFAB Spanish: Regla)
    assert "5.45" in out


@pytest.mark.parametrize(
    ("language", "needle"),
    [
        ("French", "Loi 11"),
        ("Portuguese", "Regra 11"),
        ("German", "Regel 11"),
        ("English", "Law 11"),
    ],
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
    assert "Regra 11" in out  # fell back to the clean Portuguese floor (pt-BR: Regra)


def test_leak_detector_passes_clean_text() -> None:
    assert not _looks_like_prompt_leak("Selon la Loi 11, l'attaquant était hors-jeu.")
    assert _looks_like_prompt_leak("Law text: ... Decision data: ...")


def test_watsonx_outage_degrades_to_floor_without_crashing_or_retrying(monkeypatch) -> None:
    # A hard watsonx failure (expired key, 401/403/429/5xx, network timeout) must NOT escape and
    # kill the SSE stream; it degrades to the deterministic Law-citing floor, and does NOT retry
    # (a hard outage will not recover, unlike a transient empty completion).
    calls = {"n": 0}

    def boom(*a, **k):
        calls["n"] += 1
        raise RuntimeError("watsonx 429")

    monkeypatch.setattr(granite_mod._watsonx, "generate", boom)
    out = GraniteClient().explain_offside(
        margin_meters=5.45, is_offside=True, law_text="Law 11 ..."
    )
    assert out.strip() != "" and "Law 11" in out and "5.45" in out  # the floor explanation
    assert calls["n"] == 1  # one attempt, then straight to the floor (no 3x retry on a hard outage)


def test_explain_decision_outage_degrades_to_floor_without_retrying(monkeypatch) -> None:
    # The SAME hard-outage contract on the penalty/handball path (pipeline.py -> /stream/decision):
    # a watsonx failure degrades to the deterministic Law-citing floor, with no 3x retry.
    calls = {"n": 0}

    def boom(*a, **k):
        calls["n"] += 1
        raise RuntimeError("watsonx 503")

    monkeypatch.setattr(granite_mod._watsonx, "generate", boom)
    out = GraniteClient().explain_decision(
        incident="An attacker is tripped inside the penalty area.",
        outcome="Penalty awarded",
        law="14",
        law_text="Law 14 ...",
    )
    assert out.strip() != "" and "14" in out  # the deterministic, Law-citing floor
    assert calls["n"] == 1  # one attempt, no retry on a hard outage


def test_answer_question_outage_degrades_to_floor_without_retrying(monkeypatch) -> None:
    # The SAME hard-outage contract on the free-text oracle path (pipeline.py -> /stream/ask).
    calls = {"n": 0}

    def boom(*a, **k):
        calls["n"] += 1
        raise RuntimeError("watsonx timeout")

    monkeypatch.setattr(granite_mod._watsonx, "generate", boom)
    out = GraniteClient().answer_question(
        question="Why was that offside?",
        law="11",
        title="Offside",
        law_text="Law 11 ...",
    )
    assert out.strip() != "" and "11" in out  # the deterministic, Law-grounded floor
    assert calls["n"] == 1  # one attempt, no retry on a hard outage
