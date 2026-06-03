"""Rule-only VAR decisions (no geometry): the SAME RAG + Granite + Guardian path that
explains offside also explains a penalty (Law 14) and a handball (Law 12), so VARSITY is
a general rule-grounded VAR explainer, not an offside-only tool.

These are ILLUSTRATIVE incidents, clearly tiered as such: the Law retrieval, the Granite
explanation and the Guardian groundedness check are all REAL (real corpus, real model),
but the incident itself is a representative description, not a specific match's positional
data (unlike the real StatsBomb offside frames in scenarios.py). The verdict earcon /
margin / SVG do not apply; only the rule-grounded explanation does.
"""

from __future__ import annotations

DECISIONS: dict[str, dict] = {
    "penalty": {
        "decision_type": "penalty",
        "label": "Penalty",
        "law_query": (
            "penalty kick awarded for an offence punishable by a direct free kick "
            "committed by a defender inside their own penalty area, Law 14"
        ),
        "incident": (
            "An attacker running toward goal is tripped by a defender inside the penalty "
            "area before getting a shot away."
        ),
        "outcome": "Penalty kick awarded",
    },
    "handball": {
        "decision_type": "handball",
        "label": "Handball",
        "law_query": (
            "deliberate handball handling the ball offence, the ball touches a player's "
            "hand or arm making the body unnaturally bigger, Law 12"
        ),
        "incident": (
            "A defender blocks a goal-bound shot with an arm held away from the body, "
            "making their body unnaturally bigger."
        ),
        "outcome": "Handball, penalty kick awarded",
    },
}
DEFAULT_DECISION = "penalty"


def decision_names() -> list[str]:
    return list(DECISIONS)


def _resolve(name: str) -> str:
    return name if name in DECISIONS else DEFAULT_DECISION


def get_decision(name: str) -> dict:
    return DECISIONS[_resolve(name)]


def trigger_meta(name: str) -> dict:
    d = get_decision(name)
    return {
        "source": "Illustrative VAR incident",
        "decision_type": d["decision_type"],
        "label": d["label"],
        "tier": "illustrative",
        "outcome": d["outcome"],
    }


def decisions_index() -> list[dict]:
    return [
        {
            "decision_type": d["decision_type"],
            "label": d["label"],
            "outcome": d["outcome"],
            "tier": "illustrative",
        }
        for d in DECISIONS.values()
    ]
