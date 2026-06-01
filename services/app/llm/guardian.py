"""Granite Guardian output-safety check with a Bring Your Own Criteria (BYOC) rule.

Two layers: (1) a deterministic, test-backed guard that the explanation cites a Law
number (the no-invented-facts rule), and (2) Granite Guardian applying the custom
criterion via watsonx. An explanation is SAFE only if both agree.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

from app.llm import _watsonx

DEFAULT_GUARDIAN = "ibm/granite-guardian-3-8b"
_LAW_CITATION = re.compile(r"\blaw\s+\d{1,2}\b", re.IGNORECASE)

BYOC_CRITERION = (
    "The response must cite a specific Law of the Game by number and must not invent "
    "any rule that is not grounded in the provided Law text."
)


def cites_law_clause(text: str) -> bool:
    """Deterministic no-invented-facts guard: the explanation must cite a Law number."""
    return bool(_LAW_CITATION.search(text))


@dataclass
class GuardianVerdict:
    safe: bool
    cites_law: bool
    model_answer: str


class GuardianClient:
    def __init__(self, model_id: str | None = None) -> None:
        self.model_id = model_id or os.environ.get("GRANITE_GUARDIAN_MODEL_ID", DEFAULT_GUARDIAN)

    def check(self, explanation: str) -> GuardianVerdict:
        cites = cites_law_clause(explanation)
        prompt = (
            "You are a safety reviewer applying a custom criterion (Bring Your Own Criteria).\n"
            f"Criterion: {BYOC_CRITERION}\n\n"
            f"Response to review:\n{explanation}\n\n"
            "Does the response satisfy the criterion? Answer with one word: Yes or No."
        )
        try:
            answer = _watsonx.generate(self.model_id, prompt, max_new_tokens=3).strip().lower()
        except Exception:
            answer = "(error)"
        model_ok = answer.startswith("yes")
        return GuardianVerdict(safe=cites and model_ok, cites_law=cites, model_answer=answer)
