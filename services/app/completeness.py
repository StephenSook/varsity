"""Deterministic argumentative-completeness scorer (a lite Walton critical-questions checker).

Faithfulness asks "does the narration say nothing FALSE?" (the verification critics); completeness
asks the complementary question "does the narration say ENOUGH - does it disclose what a blind fan,
who cannot see the line, needs in order to calibrate trust?". Each check is DISCLOSURE-shaped
("does the narration STATE X") and never JUDGMENT-shaped ("was X correct"): this is explanation,
not adjudication - the scope fence from Walton, Reed & Macagno (Argumentation Schemes, Cambridge
University Press, 2008) and the CQ-checker report.

For an offside explanation it scores whether the narration discloses, weighted by what matters most
to a blind fan:
- the verdict (Expert-Opinion "Opinion" critical question),
- the margin to the line (Sign "correlation strength / margin" CQ - the highest weight, since a fan
  cannot see how close it was),
- the governing Law (Established-Rule CQ),
- the offside line / second-to-last defender (Position-to-Know CQ),
- and, for a knife-edge call, that the call is tight (Sign "margin of error" CQ).

It is deterministic (regex over the narration), so it adds no model calls.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_MARGIN = re.compile(r"\d+(?:\.\d+)?\s*(?:m\b|metre|meter|cm|centimet|centímet)", re.IGNORECASE)
_VERDICT = re.compile(
    r"\boffside\b|\bonside\b|fuera de juego|hors-?jeu|impedimento|abseits", re.IGNORECASE
)
_LAW = re.compile(r"\b(?:law|ley|loi|lei|gesetz|regel|regra)\b.{0,12}?\d", re.IGNORECASE)
_REFERENCE = re.compile(
    r"second-?to-?last|second-?last|2nd-?last|penúltim|avant-dernier|vorletzt|"
    r"offside line|defender|last opponent|opponent",
    re.IGNORECASE,
)
_TIGHT = re.compile(
    r"tight|marginal|knife-edge|within (?:the )?(?:measurement )?noise|measurement noise|"
    r"borderline|very close|by (?:a )?few centimet|fine margin|umpire'?s call|too close|\blevel\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Disclosure:
    name: str
    disclosed: bool
    weight: float
    detail: str


@dataclass(frozen=True)
class CompletenessReport:
    disclosures: list[Disclosure]
    score: float  # weighted fraction disclosed, in [0, 1]
    complete: bool  # score >= threshold
    dangling: list[str]  # names of the disclosures the narration is missing


def score_offside(
    explanation: str, *, within_noise: bool = False, threshold: float = 0.8
) -> CompletenessReport:
    """Score how completely an offside narration discloses what a blind fan needs."""
    checks = [
        Disclosure("verdict", bool(_VERDICT.search(explanation)), 1.0, "states the verdict"),
        Disclosure("law", bool(_LAW.search(explanation)), 0.9, "cites the governing Law"),
        Disclosure(
            "reference",
            bool(_REFERENCE.search(explanation)),
            0.7,
            "references the offside line or the second-to-last defender",
        ),
    ]
    if within_noise:
        # Too close to call: a precise margin would be false precision, so disclosing the
        # TIGHTNESS (not a number) is what calibrates a blind fan's trust.
        checks.append(
            Disclosure(
                "tightness",
                bool(_TIGHT.search(explanation)),
                1.0,
                "acknowledges the call is tight (within measurement noise)",
            )
        )
    else:
        checks.append(
            Disclosure(
                "margin", bool(_MARGIN.search(explanation)), 1.0, "states the margin to the line"
            )
        )
    total = sum(c.weight for c in checks)
    earned = sum(c.weight for c in checks if c.disclosed)
    score = round(earned / total, 3) if total else 1.0
    return CompletenessReport(
        disclosures=checks,
        score=score,
        complete=score >= threshold,
        dangling=[c.name for c in checks if not c.disclosed],
    )


def completeness_stage(report: CompletenessReport) -> dict:
    """The SSE 'completeness' stage payload (a judge-facing disclosure panel)."""
    return {
        "stage": "completeness",
        "score": report.score,
        "complete": report.complete,
        "disclosed": sum(1 for d in report.disclosures if d.disclosed),
        "total": len(report.disclosures),
        "disclosures": [
            {"name": d.name, "disclosed": d.disclosed, "detail": d.detail}
            for d in report.disclosures
        ],
        "dangling": report.dangling,
    }
