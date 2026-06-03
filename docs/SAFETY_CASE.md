# Safety case

A short assurance argument in the Goal Structuring Notation idiom (top claim, decomposed into
subclaims, each resting on evidence that runs in this repository). It is deliberately falsifiable:
every leaf points at code or a test you can execute.

## G0 - Top claim

> A blind fan can trust that every spoken VARSITY explanation is faithful to the received decision
> and to the IFAB Laws, signals its own uncertainty honestly, and never adjudicates.

This decomposes into four subclaims.

## G1 - The explanation is faithful to the Laws and the proof

**Strategy:** defense in depth. Deterministic checks are dispositive; the probabilistic model judge
is advisory.

- **E1.1** A neuro-symbolic Law-11 proof traverses the rule and the explanation must agree with it
  (`services/app/law11.py`, `services/app/verification.py` `no-re-adjudication` critic).
- **E1.2** A deterministic floor quotes the retrieved Law even if Granite errs
  (`services/app/llm/granite.py`).
- **E1.3** Granite Guardian groundedness runs as the advisory critic; a single false-positive does
  not flip the hard gate, but a real grounding failure stays visible
  (`services/app/llm/guardian.py`, `verification.py`).
- **E1.4** A provenance manifest links every claim to an IFAB clause + its evidence, sealed with a
  SHA-256 over the grounding chain (`services/app/provenance.py`).

## G2 - The rule engine is correct by Law 11

- **E2.1** Z3 proves three Law-11 safety properties (mutual-exclusivity, own-half safety, restart
  safety), each guarded against vacuous truth (`services/verify/law11_smt.py`).
- **E2.2** Hypothesis property-based + three metamorphic invariants (lateral mirror, x-translation
  preserves margin, permutation) guard the geometry (`services/tests/test_metamorphic.py`).
- **E2.3** The geometry enforces Law 11.1's halfway-line condition, provably consistent with the
  proof engine (`docs/VERIFICATION.md`).

## G3 - Uncertainty is signalled honestly, in audio a blind fan can use

- **E3.1** The offside margin's confidence is spoken in a frozen, externally-calibrated IPCC
  likelihood lexicon, inserted deterministically, never the model's own hedging
  (`services/app/uncertainty.py`). Rationale: Sherman Kent (1964) showed uncalibrated probability
  words span 30-75% across readers; a blind fan calibrates trust entirely on the words.
- **E3.2** The verdict earcon's roughness is coupled to the uncertainty band: a clear call is a
  pure triad, a very-tight call adds beating + a rough neighbour tone, so the listener *hears* the
  uncertainty a sighted fan would read off the margin (`apps/web/src/sonify.ts`).

## G4 - The system never adjudicates (the scope boundary)

- **E4.1** When the proof engine's own derivation disagrees with the official, it defers: the
  official has finer semi-automated tracking; the decision stands (`law11.py`).
- **E4.2** The `no-re-adjudication` critic is deterministic and dispositive; an explanation that
  contradicts the received decision fails the hard gate (`verification.py`, tested).
- **E4.3** The geometry, parallax, and uncertainty layers describe and explain; none recompute a
  verdict.

## Defeaters we acknowledge (honest gaps)

- Faithfulness is bounded by input-data correctness (StatsBomb 360 / Sportmonks), not guaranteed by
  this case.
- The advisory Guardian layer is probabilistic; the hard guarantee rests on the deterministic
  checks + the formal proofs.
- A runtime NLI faithfulness gate and an injected-error gold-eval suite are future work
  (`docs/RESPONSIBLE_AI.md`), not claimed here.
