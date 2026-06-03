"""Tests for the multilingual IFAB termbase."""

from __future__ import annotations

from app.termbase import (
    NARRATION_LANGS,
    TERMS,
    glossary_line,
    language_count,
    offside_term,
    term_hit_rate,
)


def test_every_narration_language_has_the_core_terms():
    for key in NARRATION_LANGS:
        assert key in TERMS["offside"]
        assert key in TERMS["Law"]
        assert key in TERMS["second-to-last opponent"]


def test_official_terms_were_corrected_by_verification():
    # the verification caught these: ES Law is "Regla" (not "Ley"), IFAB uses "adversario"/
    # "Gegenspieler" (not "defender"), pt-BR is "impedimento" + "Regra".
    assert offside_term("Spanish") == "fuera de juego"
    assert TERMS["Law"]["es"] == "Regla"
    assert TERMS["Law"]["pt"] == "Regra"
    assert TERMS["offside"]["pt"] == "impedimento"
    assert TERMS["second-to-last opponent"]["de"] == "vorletzter Gegenspieler"
    assert offside_term("French") == "hors-jeu"


def test_offside_line_is_not_in_the_termbase():
    # the verification flagged "offside line" is not a formal IFAB term in any language
    assert "offside line" not in TERMS


def test_glossary_line_is_empty_for_english_and_localized_otherwise():
    assert glossary_line("English") == ""
    es = glossary_line("Spanish")
    assert "fuera de juego" in es and "penúltimo adversario" in es


def test_term_hit_rate_is_reference_free():
    hit = "Según la Regla 11, el atacante estaba en fuera de juego."
    miss = "The attacker was ahead of the line."
    assert term_hit_rate(hit, "Spanish") == 1.0
    assert term_hit_rate(miss, "Spanish") == 0.0


def test_language_count_shows_the_reach():
    assert language_count() >= 7  # en/es/fr/pt/de + it/nl reach toward IFAB's translations
