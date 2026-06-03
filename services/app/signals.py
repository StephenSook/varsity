"""Referee-signal descriptions: the standardized on-pitch gesture for a decision, so a
blind fan knows what the stadium just reacted to.

A sighted fan reads the referee's or assistant referee's signal instantly; a blind fan
never receives that visual cue. These descriptions name the standardized signal defined in
Law 5 (The Referee) and Law 6 (The Other Match Officials); the VAR review signal is in the
VAR protocol. This EXPLAINS the received decision's communication; it never adjudicates.
"""

from __future__ import annotations

SIGNALS: dict[str, dict[str, str]] = {
    "offside": {
        "text": (
            "The assistant referee raises the flag straight up, then points across the "
            "field to show where the offside happened."
        ),
        "law": "6",
    },
    "onside": {
        "text": "The assistant referee keeps the flag down, and play continues.",
        "law": "6",
    },
    "penalty": {
        "text": "The referee blows the whistle and points firmly to the penalty spot.",
        "law": "5",
    },
    "handball": {
        "text": (
            "The referee signals handball with a raised arm, then points to the penalty spot."
        ),
        "law": "5",
    },
    "review": {
        "text": (
            "The referee draws a TV-screen rectangle in the air to show a VAR review is underway."
        ),
        "law": "VAR",
    },
}


def referee_signal(
    *, is_offside: bool | None = None, decision_type: str | None = None
) -> dict[str, str]:
    """The standardized referee/AR signal for this decision (Law 5/6 / VAR protocol)."""
    if decision_type is not None:
        return SIGNALS.get(decision_type, SIGNALS["penalty"])
    if is_offside is True:
        return SIGNALS["offside"]
    if is_offside is False:
        return SIGNALS["onside"]
    return SIGNALS["review"]
