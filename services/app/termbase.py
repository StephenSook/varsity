"""Multilingual IFAB Laws-of-the-Game termbase (TBX-style: one concept, one official term per
language).

The fan's explanation is delivered in their language with the OFFICIAL football terminology, not an
ad-hoc synonym. The termbase (a) injects a glossary into the Granite prompt - glossary
prompt-injection beats strict lexical decoding constraints for terminology (WMT 2025 terminology
shared task) and is feasible on the watsonx REST endpoint, which exposes no token-level constraints;
and (b) drives the deterministic, reference-free Terminology-Hit-Rate eval
(``services/verify/multilingual_eval.py``).

Terms verified against the official IFAB Law 11 pages (es/fr/de are IFAB-authoritative; it/nl/pt are
the national-FA official translations IFAB hosts). Note the corrections this verification caught:
the official Spanish word for a Law is "Regla" (not the colloquial "Ley"); IFAB uses "adversario /
Gegenspieler / adversaire" (opponent), not "defender"; Brazilian Portuguese uses "impedimento" +
"Regra 11" (we use the pt-BR variant for its wider reach; pt-PT is "fora de jogo" + "Lei 11"); and
"offside line" is not a formal IFAB term in any language, so it is deliberately not in the termbase.

Scope, stated honestly: VARSITY narrates in five languages (en/es/fr/pt/de) and carries the full
term set for them; it/nl carry the full reference set to show the path to IFAB's official
translations (30 languages). The Laws TEXT stays the English RAG corpus; a full native-language Law
corpus is the production path - here the TERMS are localised. In-concept: the explanation of a
received decision, in the fan's language; never adjudication.
"""

from __future__ import annotations

# concept -> { lang: official term }. en/es/fr/pt/de = the narration languages; it/nl are the
# reference reach toward IFAB's official translations.
TERMS: dict[str, dict[str, str]] = {
    "offside": {
        "en": "offside",
        "es": "fuera de juego",
        "fr": "hors-jeu",
        "pt": "impedimento",
        "de": "Abseits",
        "it": "fuorigioco",
        "nl": "buitenspel",
    },
    "offside position": {
        "en": "offside position",
        "es": "posición de fuera de juego",
        "fr": "position de hors-jeu",
        "pt": "posição de impedimento",
        "de": "Abseitsstellung",
        "it": "posizione di fuorigioco",
        "nl": "buitenspelpositie",
    },
    "second-to-last opponent": {
        "en": "second-to-last opponent",
        "es": "penúltimo adversario",
        "fr": "avant-dernier adversaire",
        "pt": "penúltimo adversário",
        "de": "vorletzter Gegenspieler",
        "it": "penultimo avversario",
        "nl": "voorlaatste tegenstander",
    },
    "interfering with play": {
        "en": "interfering with play",
        "es": "interferir en el juego",
        "fr": "intervenir dans le jeu",
        "pt": "interferir no jogo",
        "de": "ins Spiel eingreifen",
        "it": "intervenire nel gioco",
        "nl": "ingrijpen in het spel",
    },
    "gaining an advantage": {
        "en": "gaining an advantage",
        "es": "sacar ventaja",
        "fr": "tirer un avantage",
        "pt": "tirar vantagem",
        "de": "sich einen Vorteil verschaffen",
        "it": "trarre vantaggio",
        "nl": "voordeel behalen",
    },
    "Law": {
        "en": "Law",
        "es": "Regla",
        "fr": "Loi",
        "pt": "Regra",
        "de": "Regel",
        "it": "Regola",
        "nl": "Regel",
    },
}

# The languages VARSITY narrates in (full glossary + eval).
NARRATION_LANGS: tuple[str, ...] = ("en", "es", "fr", "pt", "de")

_PREFIXES: dict[str, tuple[str, ...]] = {
    "en": ("en", "ingl"),
    "es": ("es", "span", "español", "espanol"),
    "fr": ("fr", "fren", "franç", "franc"),
    "pt": ("pt", "port"),
    "de": ("de", "germ", "deut"),
    "it": ("it", "ital"),
    "nl": ("nl", "dutch", "neder"),
}


def lang_key(language: str) -> str:
    """Map a language name or code to a termbase key (English if unknown)."""
    low = language.lower()
    for key, starts in _PREFIXES.items():
        if low.startswith(starts):
            return key
    return "en"


def term(concept: str, language: str) -> str | None:
    return TERMS.get(concept, {}).get(lang_key(language))


def offside_term(language: str) -> str:
    return TERMS["offside"].get(lang_key(language), "offside")


def language_count() -> int:
    """How many languages carry the term set (the reach toward IFAB's official translations)."""
    return len(TERMS["offside"])


# Concepts injected into the Granite prompt as a glossary (the load-bearing offside vocabulary).
_GLOSSARY_CONCEPTS = ("offside", "second-to-last opponent")
# Concepts the Terminology-Hit-Rate checks verbatim (present exactly in our narration + floors):
# the official offside term and the localised word for "Law".
_HIT_CONCEPTS = ("offside", "Law")


def glossary_for(language: str) -> list[tuple[str, str]]:
    """(English concept, official localised term) pairs to nudge a non-English narration; [] for
    English (no glossary needed)."""
    key = lang_key(language)
    if key == "en":
        return []
    out: list[tuple[str, str]] = []
    for concept in _GLOSSARY_CONCEPTS:
        localized = TERMS[concept].get(key)
        if localized:
            out.append((concept, localized))
    return out


def glossary_line(language: str) -> str:
    """A concise glossary line the Granite prompt can use to keep the official terminology."""
    pairs = glossary_for(language)
    if not pairs:
        return ""
    body = "; ".join(f"{en} = {loc}" for en, loc in pairs)
    return f"Use the official Laws-of-the-Game terms ({body}). "


def term_hit_rate(text: str, language: str) -> float:
    """Reference-free Terminology-Hit-Rate: the fraction of the language's core terms (the offside
    term and the localised word for Law) that appear in the text. The report's killer metric
    ('97% of French outputs contain hors-jeu'), computable with no reference translation."""
    key = lang_key(language)
    checks = [TERMS[c].get(key) for c in _HIT_CONCEPTS]
    checks = [c for c in checks if c]
    if not checks:
        return 1.0
    low = text.lower()
    hits = sum(1 for t in checks if t.lower() in low)
    return round(hits / len(checks), 3)
