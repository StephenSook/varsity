# Responsible AI

VARSITY serves blind and low-vision football fans. They cannot visually check the audio, so a
confidently-wrong explanation is the most harmful failure mode. We treat this as safety-critical
and engineer for it. Every claim below points at the file that backs it; nothing here is
aspirational.

## Scope, stated plainly

VARSITY **explains a received VAR/offside decision**. It never adjudicates, predicts, or
second-guesses the official. This is not a slogan: it is a coded, tested property
(`services/app/law11.py` defers to the official when its own derivation disagrees;
`services/app/verification.py` has a dispositive `no-re-adjudication` critic).

## Frameworks we align with

- **NIST AI Risk Management Framework** and the **Generative AI Profile** (NIST-AI-600-1, 2024) -
  Govern / Map / Measure / Manage. Our measures: the faithfulness chain below, the formal
  verification suite (`docs/VERIFICATION.md`), and the provenance manifest (`docs/SAFETY_CASE.md`).
- **OWASP Top 10 for LLM Applications 2025** - LLM01 prompt injection (the canned path takes only
  structured StatsBomb 360 facts, not free text; the live feed is the spotlighting surface, tracked
  in the build plan), LLM05 improper output handling (the screen reader consumes only verified
  prose), LLM06 excessive agency (the narrator has read-only tools; no mutation).
- **W3C WCAG 2.2 AA** - 4.1.3 Status Messages (the `aria-live` verdict region), 1.3.1 Info &
  Relationships, 2.2.2 Pause/Stop/Hide (the ticker has a pause control), 2.3.3 Animation from
  Interactions (`prefers-reduced-motion` gates every decorative animation).

## The faithfulness architecture (defense in depth)

Every spoken explanation passes a layered chain. The deterministic layers are the hard guarantee;
the model judge is defense-in-depth, never the sole gate.

| Layer | What it guarantees | Where |
|---|---|---|
| Deterministic floor | If Granite errs, a per-language template still quotes the retrieved Law. | `services/app/llm/granite.py` |
| Neuro-symbolic proof | An auditable Law-11 rule traversal; the explanation must agree with it. | `services/app/law11.py` |
| Multi-critic panel | cites-law + no-re-adjudication + substantive are **dispositive**; Granite Guardian groundedness + screen-reader-prose are **advisory** (reported, but a single probabilistic flake never flips the hard gate). | `services/app/verification.py` |
| Granite Guardian | IBM's groundedness judge (REVEAL #1 on the public leaderboard) as the advisory model critic. | `services/app/llm/guardian.py` |
| Calibrated uncertainty | The margin's confidence is spoken in a frozen, externally-calibrated IPCC likelihood lexicon, never the model's own hedging. | `services/app/uncertainty.py` |
| Provenance manifest | Every claim is linked to an IFAB clause + its evidence, with a SHA-256 over the chain. | `services/app/provenance.py` |
| Formal verification | Z3 proves three Law-11 safety properties; Hypothesis + metamorphic tests guard the geometry. | `services/verify/law11_smt.py` |

This mirrors the established faithfulness literature (decompose-then-verify: FActScore, Claimify,
MiniCheck; groundedness judging: Granite Guardian; calibrated verbalization: IPCC AR6, Sherman
Kent's *Words of Estimative Probability*, 1964). The components named in that literature that we
have NOT built (a runtime MiniCheck/AlignScore NLI gate, grammar-constrained decoding, an
injected-error gold-eval suite) are listed honestly under Known Limitations, because we run Granite
on the watsonx REST endpoint, which does not expose token-logit constraints, and a 770M NLI model
cannot load per request on the free deployment tier.

## Known limitations (read this first)

- **Faithfulness is not correctness.** This chain guarantees the narration is faithful to the proof
  and the retrieved Law. It does not guarantee the proof is true: VARSITY's correctness is bounded
  by the StatsBomb 360 / Sportmonks input data.
- **Granite Guardian is probabilistic.** It is the advisory layer for exactly this reason; the
  deterministic checks carry the hard guarantee. We do not treat any single model as an auditable
  boundary.
- **No runtime NLI gate or grammar-constrained decoding yet.** These are real next steps (see the
  build plan); they are not claimed as shipped.
- **Multilingual safety.** Granite Guardian is English-primary; non-English narration is generated
  natively but the groundedness judge is strongest in English.

## Reporting

Security or safety concerns: open an issue on the repository. We will respond.
