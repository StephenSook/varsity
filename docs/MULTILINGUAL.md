# Multilingual: official IFAB terminology per language

VARSITY narrates VAR/offside decisions in five languages (English, Spanish, French, Portuguese,
German). A blind fan should hear the explanation in their language with the **official football
terminology**, not an ad-hoc synonym. This note documents how that is done, and is honest about
what is shipped versus what is the production path.

## The termbase

`services/app/termbase.py` is a TBX-style termbase: one concept, one official term per language
(offside, offside position, the second-to-last opponent, interfering with play, gaining an
advantage, and the word for "Law"). The terms were **verified** against the official IFAB Law 11
pages (Spanish, French, German are IFAB-authoritative; Italian, Dutch, and Portuguese are the
national-FA official translations IFAB hosts). The verification caught real corrections that a
guess would have missed:

- The official Spanish word for a Law is **"Regla"** (→ "Regla 11"), not the colloquial "Ley".
- IFAB uses **"adversario / Gegenspieler / adversaire"** (opponent), not "defender".
- Brazilian Portuguese uses **"impedimento" + "Regra 11"**; European Portuguese is "fora de jogo" +
  "Lei 11". VARSITY uses the pt-BR variant for its wider reach.
- **"Offside line"** is not a formal IFAB term in any language, so it is deliberately not in the
  termbase (it is a derived, descriptive label only).

## Glossary prompt-injection

The termbase injects a concise glossary into the IBM Granite prompt ("Use the official terms:
offside = hors-jeu; second-to-last opponent = avant-dernier adversaire"). Glossary prompt-injection
beats strict lexical decoding constraints for terminology (WMT 2025 terminology shared task) and is
the only feasible approach on the watsonx REST endpoint, which exposes no token-level grammar
constraints. The deterministic in-language **floors** already use the official terms, so even when
Granite is unavailable the narration is guaranteed to be officially-termed.

## The Terminology-Hit-Rate eval

`services/verify/multilingual_eval.py` computes the **Terminology-Hit-Rate**: do the outputs in each
language contain the official term ("97% of French outputs contain hors-jeu")? It is **reference-free**
(no human reference translation needed) and deterministic, so it runs in CI and serves live at
`GET /multilingual`. Over the in-language floors it scores **1.0** in all five languages (every floor
uses the official offside term and the official word for "Law").

chrF and COMET-22 are the gold-standard reference-based metrics, but both need native-reviewer
**reference translations**, which we do not have. Producing them (a 100-sentence offside test set
per language, native-reviewer-validated and credited) is a planned submission deliverable (a manual,
native-reviewer task), not a CI build. The Terminology-Hit-Rate is the part that is honestly
shippable today.

## Honest scope

- VARSITY narrates in five languages and carries the full term set for them; Italian and Dutch are
  in the termbase as the reach toward IFAB's official translations (30 languages).
- The Laws **text** remains the English RAG corpus; the **terms** are localised. A full
  native-language Law corpus over IFAB's official translations is the production path.
- Even with correct markup, screen readers do not reliably switch voice on a language change; that
  separate accessibility reality and VARSITY's dual-path fix are in
  `docs/ACCESSIBILITY-SR-LANG.md`. Spoken numbers are verbalised per language in `apps/web/src/speech.ts`.
- In-concept: the explanation of a received decision, in the fan's language; never adjudication.
