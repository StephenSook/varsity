"""Multi-critic verification of the explanation - a generator-and-critics faithfulness
panel (MADR / SAVER style), scoped strictly to VERIFICATION, never adjudication.

The generator is Granite. The critics each independently check one faithfulness property
and vote; the explanation is "verified" only if every critic passes. Two critics are the
Granite Guardian model judgements (groundedness + screen-reader-prose); the others are
deterministic. The non-adjudication critic is a CODED SECURITY PROPERTY: the explanation
must agree with the Law-11 proof and must not re-adjudicate or contradict the RECEIVED
decision. Most critics are deterministic, so the panel adds no extra model latency beyond
the single Guardian call the pipeline already makes.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Critic:
    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class VerificationPanel:
    critics: list[Critic]
    verified: bool


def verify(
    *,
    explanation: str,
    cites_law: bool,
    grounded: bool,
    screen_reader_ok: bool,
    proof_consistent: bool = True,
) -> VerificationPanel:
    """Run the critic panel over a generated explanation. Verified iff all critics pass."""
    critics = [
        Critic("cites-law", bool(cites_law), "Cites a specific Law clause."),
        Critic(
            "grounded", bool(grounded), "Grounded in the retrieved Law text (Granite Guardian)."
        ),
        Critic(
            "screen-reader-safe",
            bool(screen_reader_ok),
            "Screen-reader-appropriate prose (Granite Guardian).",
        ),
        Critic(
            "no-re-adjudication",
            bool(proof_consistent),
            "Agrees with the rule proof; does not re-adjudicate the received decision.",
        ),
        Critic(
            "substantive",
            len(explanation.strip()) >= 20,
            "A substantive explanation, not empty or a leaked prompt.",
        ),
    ]
    return VerificationPanel(critics=critics, verified=all(c.passed for c in critics))


def verification_stage(panel: VerificationPanel) -> dict:
    """The SSE 'verification' stage payload (a judge-facing critic panel)."""
    return {
        "stage": "verification",
        "verified": panel.verified,
        "passed": sum(1 for c in panel.critics if c.passed),
        "total": len(panel.critics),
        "critics": [
            {"name": c.name, "passed": c.passed, "detail": c.detail} for c in panel.critics
        ],
    }
