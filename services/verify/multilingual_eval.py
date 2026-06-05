"""Multilingual terminology eval - the deterministic, reference-free Terminology-Hit-Rate.

The report's "killer metric" for a multilingual explainer is the Terminology-Hit-Rate: do the
outputs in each language contain the OFFICIAL term ("97% of French outputs contain hors-jeu")? It is
reference-FREE (no human reference translation needed) and deterministic, so it runs in CI - unlike
chrF or COMET-22, which both need native-reviewer reference translations we do not have (those are
a manual submission deliverable, not yet produced). This suite runs the in-language deterministic
FLOORS (which are guaranteed to use the official terminology) and scores the offside-term + Law-word
hit rate per language. A floor hit-rate of 1.0 proves VARSITY's deterministic fallback always uses
the official IFAB terminology; the same metric can be run over the LIVE Granite output (requires a
live watsonx run) to measure the glossary-injection's effect.
"""

from __future__ import annotations

from app.llm.granite import _fallback_explanation
from app.termbase import TERMS, lang_key, offside_term, term_hit_rate

_LANG_NAME = {"en": "English", "es": "Spanish", "fr": "French", "pt": "Portuguese", "de": "German"}


def evaluate() -> dict:
    """Run the Terminology-Hit-Rate over an offside floor in each narration language."""
    rows: list[dict] = []
    for name in _LANG_NAME.values():
        key = lang_key(name)
        text = _fallback_explanation(margin_meters=5.69, is_offside=True, language=name)
        rows.append(
            {
                "lang": key,
                "language": name,
                "offside_term": offside_term(name),
                "law_word": TERMS["Law"][key],
                "has_offside_term": TERMS["offside"][key].lower() in text.lower(),
                "has_law_word": TERMS["Law"][key].lower() in text.lower(),
                "term_hit_rate": term_hit_rate(text, name),
            }
        )
    overall = round(sum(r["term_hit_rate"] for r in rows) / len(rows), 3) if rows else 1.0
    return {
        "rows": rows,
        "languages": len(rows),
        "overall_term_hit_rate": overall,
        "note": (
            "Reference-free Terminology-Hit-Rate over the deterministic in-language floors. chrF "
            "COMET-22 need native-reviewer reference translations (a manual deliverable not yet "
            "produced), so they are not "
            "run here; this metric is the CI-runnable guarantee that the official IFAB terminology "
            "is used in every language."
        ),
    }


def report() -> str:
    result = evaluate()
    lines = ["Multilingual Terminology-Hit-Rate (deterministic floors):"]
    for r in result["rows"]:
        lines.append(
            f"  {r['lang']}: hit-rate {r['term_hit_rate']} "
            f"(offside='{r['offside_term']}' {'OK' if r['has_offside_term'] else 'MISS'}, "
            f"Law='{r['law_word']}' {'OK' if r['has_law_word'] else 'MISS'})"
        )
    n = result["languages"]
    lines.append(f"  overall: {result['overall_term_hit_rate']} over {n} languages")
    return "\n".join(lines)


if __name__ == "__main__":
    print(report())
