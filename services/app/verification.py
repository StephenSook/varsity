"""Multi-critic verification of the explanation - a generator-and-critics faithfulness
panel (MADR / SAVER style), scoped strictly to VERIFICATION, never adjudication.

The generator is Granite. Each critic independently checks one faithfulness property. Critics
come in two kinds:

- **deterministic** (dispositive): cites-law, no-re-adjudication, substantive, neutral, and (on
  the offside path) verdict-consistent. These are faithfulness-by-construction checks - the
  explanation cites the governing Law, never contradicts the Law-11 proof, is non-empty, does not
  editorialize about the official, and (a lite round-trip re-parse) restates the same verdict the
  decision carried. The headline ``verified`` gate is these and only these: a stable, deterministic
  guarantee.
- **advisory** (defense-in-depth): the Granite Guardian model judgements (groundedness +
  screen-reader-prose). Guardian is a probabilistic judge (REVEAL #1, but not infallible), so it can
  false-positive on a genuinely-grounded explanation. We REPORT its verdict but never let a single
  model flake flip the deterministic gate.

The no-re-adjudication and neutral critics are CODED SECURITY PROPERTIES: the explanation must
agree with the Law-11 proof and must never re-adjudicate, second-guess, or editorialize about the
official.
"""

from __future__ import annotations

from dataclasses import dataclass

DETERMINISTIC = "deterministic"
ADVISORY = "advisory"

# Phrases that editorialize about the official or the call (never about the rule itself).
_EDITORIAL = (
    "poor call",
    "bad call",
    "wrong call",
    "should have",
    "got it wrong",
    "mistake by",
    "blunder",
    "howler",
    "robbed",
    "cheated",
    "disgrace",
    "biased",
    "incompetent",
    "terrible decision",
    "harsh decision",
    "unfair decision",
    "controversial",
    "the referee was wrong",
    "the official was wrong",
)

# Offside is verbalized in five languages; a verdict re-parse must recognize each.
_OFFSIDE_TERMS = ("offside", "fuera de juego", "hors-jeu", "hors jeu", "impedimento", "abseits")


def _is_neutral(explanation: str) -> bool:
    low = explanation.lower()
    return not any(phrase in low for phrase in _EDITORIAL)


def _asserts_offside(explanation: str) -> bool:
    """Lite round-trip re-parse: does the narration assert OFFSIDE (vs onside/legal)?"""
    low = explanation.lower()
    onside = (
        ("onside" in low and "not onside" not in low)
        or "not offside" in low
        or "no offence" in low
        or "no offense" in low
    )
    if onside:
        return False
    return any(term in low for term in _OFFSIDE_TERMS)


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
    is_offside: bool | None = None,
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
            "neutral",
            _is_neutral(explanation),
            "Explains the Law without editorializing about the official or the call.",
            DETERMINISTIC,
        ),
        Critic(
            "substantive",
            len(explanation.strip()) >= 20,
            "A substantive explanation, not empty or a leaked prompt.",
            DETERMINISTIC,
        ),
    ]
    if is_offside is not None:
        critics.append(
            Critic(
                "verdict-consistent",
                _asserts_offside(explanation) == bool(is_offside),
                "Restates the same verdict the decision carried (round-trip re-parse).",
                DETERMINISTIC,
            )
        )
    critics += [
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
