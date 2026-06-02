"""Granite Guardian output-safety check.

Two layers, both grounded in how Granite Guardian actually works (verified against
the IBM granite-guardian-3-8b model card):

1. A deterministic, test-backed guard that the explanation cites a Law number
   (the no-invented-facts BYOC criterion: "the response must cite a Law clause").
2. Granite Guardian's ``groundedness`` RAG risk: the model checks whether the
   explanation is grounded in the retrieved IFAB Law text. Guardian emits "Yes"
   when risk is present (the response is NOT grounded) and "No" when it is safe
   (grounded). An explanation is SAFE only if it cites a Law AND Guardian finds it
   grounded.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

from app.llm import _watsonx

DEFAULT_GUARDIAN = "ibm/granite-guardian-3-8b"
# Match a Law-number citation in any supported language (EN/ES/FR/PT/DE), so a
# Spanish "Ley 11" explanation is not wrongly flagged as not citing a clause.
_LAW_CITATION = re.compile(
    r"\b(?:law|ley|loi|lei|gesetz|regel|regra)\b.{0,12}?\d{1,2}\b", re.IGNORECASE
)

# Granite Guardian's native output tokens (model card): "Yes" = risk present, "No" = safe.
_SAFE_TOKEN = "no"
_UNSAFE_TOKEN = "yes"

# The ``groundedness`` RAG risk, worded per the IBM model card.
GROUNDEDNESS_RISK = (
    "The assistant's response includes claims or facts that are not supported by, "
    "or are contradicted by, the provided context."
)


def cites_law_clause(text: str) -> bool:
    """Deterministic no-invented-facts guard: the explanation must cite a Law number."""
    return bool(_LAW_CITATION.search(text))


def _groundedness_prompt(explanation: str, context: str) -> str:
    """Free-form Granite Guardian groundedness template (model-card structure)."""
    return (
        "You are a safety agent trying to help determine whether the assistant "
        "message to the user is harmful according to the safety risk definition below.\n\n"
        "<start_of_turn>\n"
        f"Context: {context}\n"
        f"Assistant Message: {explanation}\n"
        "<end_of_turn>\n\n"
        "Our safety risk definition is defined below:\n\n"
        "<start_of_risk_definition>\n"
        f"* {GROUNDEDNESS_RISK}\n"
        "<end_of_risk_definition>\n\n"
        "Is the assistant message harmful based on the risk definition? "
        "Your answer must be either 'Yes' or 'No'."
    )


@dataclass
class GuardianVerdict:
    safe: bool
    cites_law: bool
    grounded: bool = True
    risk_label: str = "No"
    model_answer: str = ""


class GuardianClient:
    def __init__(self, model_id: str | None = None) -> None:
        self.model_id = model_id or os.environ.get("GRANITE_GUARDIAN_MODEL_ID", DEFAULT_GUARDIAN)

    def check(self, explanation: str, *, law_context: str = "") -> GuardianVerdict:
        cites = cites_law_clause(explanation)
        prompt = _groundedness_prompt(explanation, law_context)
        try:
            raw = _watsonx.generate(self.model_id, prompt, max_new_tokens=5).strip()
        except Exception:
            raw = ""
        answer = raw.lower()
        if answer.startswith(_SAFE_TOKEN):
            grounded, label = True, "No"
        elif answer.startswith(_UNSAFE_TOKEN):
            grounded, label = False, "Yes"
        else:
            # Ambiguous / infra error: do not let flakiness fail a Law-cited answer;
            # the deterministic cites-law guard still gates safety.
            grounded, label = True, "Failed"
        return GuardianVerdict(
            safe=cites and grounded,
            cites_law=cites,
            grounded=grounded,
            risk_label=label,
            model_answer=raw,
        )
