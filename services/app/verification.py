"""Multi-critic verification of the explanation - a generator-and-critics faithfulness
panel (MADR / SAVER style), scoped strictly to VERIFICATION, never adjudication.

The generator is Granite. Each critic independently checks one faithfulness property. Critics
come in two kinds:

- **deterministic** (dispositive): cites-law, no-re-adjudication, substantive. These are
  faithfulness-by-construction checks - the explanation cites the governing Law clause the proof
  traversed, never contradicts the Law-11 proof, and is non-empty. The headline ``verified`` gate
  is these and only these: a stable, deterministic guarantee.
- **advisory** (defense-in-depth): the Granite Guardian model judgements (groundedness +
  screen-reader-prose). Guardian is a probabilistic judge (REVEAL #1, but ~82% balanced accuracy,
  not infallible), so it can false-positive on a genuinely-grounded explanation. We therefore
  REPORT its verdict (a real grounding failure stays visible) but do not let a single model flake
  flip the deterministic gate. This is the standard "deterministic hard gate + model judge as
  defense-in-depth, fail-closed only on the hard checks" composition.

The no-re-adjudication critic is a CODED SECURITY PROPERTY and stays deterministic/dispositive:
the explanation must agree with the Law-11 proof and must not re-adjudicate the RECEIVED decision.
"""

from __future__ import annotations

from dataclasses import dataclass

DETERMINISTIC = "deterministic"
ADVISORY = "advisory"


@dataclass(frozen=True)
class Critic:
    name: str
    passed: bool
    detail: str
    kind: str  # DETERMINISTIC (dispositive) | ADVISORY (model judge, defense-in-depth)


@dataclass(frozen=True)
class VerificationPanel:
    critics: list[Critic]
    verified: bool  # the HARD gate: every deterministic critic passes

    def of_kind(self, kind: str) -> list[Critic]:
        return [c for c in self.critics if c.kind == kind]


def verify(
    *,
    explanation: str,
    cites_law: bool,
    grounded: bool,
    screen_reader_ok: bool,
    proof_consistent: bool = True,
) -> VerificationPanel:
    """Run the critic panel. ``verified`` is the deterministic hard gate; the Guardian model
    critics are reported as advisory and never flip the hard gate on their own."""
    critics = [
        Critic("cites-law", bool(cites_law), "Cites a specific Law clause.", DETERMINISTIC),
        Critic(
            "no-re-adjudication",
            bool(proof_consistent),
            "Agrees with the rule proof; does not re-adjudicate the received decision.",
            DETERMINISTIC,
        ),
        Critic(
            "substantive",
            len(explanation.strip()) >= 20,
            "A substantive explanation, not empty or a leaked prompt.",
            DETERMINISTIC,
        ),
        Critic(
            "grounded",
            bool(grounded),
            "Grounded in the retrieved Law text (Granite Guardian, advisory).",
            ADVISORY,
        ),
        Critic(
            "screen-reader-safe",
            bool(screen_reader_ok),
            "Screen-reader-appropriate prose (Granite Guardian, advisory).",
            ADVISORY,
        ),
    ]
    verified = all(c.passed for c in critics if c.kind == DETERMINISTIC)
    return VerificationPanel(critics=critics, verified=verified)


def verification_stage(panel: VerificationPanel) -> dict:
    """The SSE 'verification' stage payload (a judge-facing critic panel)."""
    det = panel.of_kind(DETERMINISTIC)
    adv = panel.of_kind(ADVISORY)
    return {
        "stage": "verification",
        "verified": panel.verified,
        "passed": sum(1 for c in panel.critics if c.passed),
        "total": len(panel.critics),
        "hard_passed": sum(1 for c in det if c.passed),
        "hard_total": len(det),
        "advisory_passed": sum(1 for c in adv if c.passed),
        "advisory_total": len(adv),
        "critics": [
            {"name": c.name, "passed": c.passed, "detail": c.detail, "kind": c.kind}
            for c in panel.critics
        ],
    }
