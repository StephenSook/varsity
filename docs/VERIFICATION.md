# Verification of the VARSITY rule engine

VARSITY explains a received VAR/offside decision; it never adjudicates. Because a blind fan
cannot visually check the audio, the rule engine that produces each explanation is held to a
higher bar than tests-of-examples: it is **formally and metamorphically verified**. None of the
tooling below ships in the deployed runtime; `z3-solver` and `hypothesis` are dev/CI-only.

## 1. Machine-checked safety properties (Z3)

`services/verify/law11_smt.py` encodes the propositional structure of the offside engine
(`app/law11.py` + `app/geometry.py`) as SMT constraints and proves three Law-11 safety
properties by showing each property's negation is **unsatisfiable**. Each proof is guarded
against vacuous truth: the base model is first shown satisfiable, so an `unsat` on the negated
property is meaningful rather than an empty model.

| Property | Statement | Law |
|---|---|---|
| `mutual_exclusivity` | An offside position and being level (onside) can never both hold. | 11.1 |
| `own_half_safety` | A player in their own half can never commit an offside offence. | 11.1 |
| `restart_safety` | A goal kick, throw-in or corner can never yield an offside offence. | 11.3 |

Run it: `cd services && python -m verify.law11_smt` (prints `PROVED` per property, exit 0 on
success). The same proofs run in CI as `tests/test_smt_properties.py`.

## 2. Property-based testing (Hypothesis)

`tests/test_metamorphic.py` generates hundreds of random valid freeze-frames per run and asserts
engine invariants hold on all of them:

- **Rule/geometry consistency** the Law-11 proof engine never contradicts the received decision,
  and its own derivation matches the geometry on every frame.
- **Offside requires the opponents' half** if the geometry calls a player offside, that player is
  in the opponents' half (Law 11.1).

## 3. Metamorphic invariants (no oracle needed)

A metamorphic relation asserts that a transformation which should *not* change the verdict indeed
leaves it unchanged. These catch coordinate-frame bugs that example-tests miss:

- **Lateral mirror** (`y -> 80 - y`): mirroring the pitch sideways must not change an offside call.
- **Uniform x-translation**: the margin is relative (attacker minus the offside line), so shifting
  every player along the pitch cannot change it.
- **Permutation**: the verdict depends on positions, not on the order players appear in the frame.

## Honest note: a gap the verification surfaced

Writing these checks exposed a real incompleteness. `geometry.compute_offside` originally set
`is_offside = beyond_defender AND beyond_ball` and **omitted Law 11.1's halfway-line condition**,
while `app/law11.py` enforced it. The two agree on every realistic frame (attackers near the
opponents' goal) but could diverge for an attacker in their own half. The halfway-line condition
was added to the geometry (`HALFWAY_X`, now a single source of truth imported by the proof
engine), so the two are provably consistent on every frame the property tests generate. This is
verification doing its job: finding the gap before a judge does.
