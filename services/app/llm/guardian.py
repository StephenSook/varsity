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
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from app.llm import _watsonx

DEFAULT_GUARDIAN = "ibm/granite-guardian-3-8b"
# Match a Law-number citation in any supported language (EN/ES/FR/PT/DE), so a
# Spanish "Regla 11" explanation is not wrongly flagged as not citing a clause. The official
# IFAB Spanish word is "Regla" (not "Ley"); Brazilian Portuguese uses "Regra".
_LAW_CITATION = re.compile(
    r"\b(?:law|ley|loi|lei|gesetz|regel|regla|regra)\b.{0,12}?\d{1,2}\b", re.IGNORECASE
)

# Granite Guardian's native output tokens: "Yes" = risk present, "No" = safe.
_UNSAFE_TOKEN = "yes"

# Bring-Your-Own-Criteria definitions, evaluated by Granite Guardian via the chat
# endpoint (the raw text/generation endpoint does not trigger the model's
# risk-classification head; chat applies the Guardian template, verified live).
GROUNDEDNESS_RISK = (
    "The response includes claims or facts that are not supported by, or are "
    "contradicted by, the provided context."
)
# A custom, accessibility-specific criterion: the explanation is delivered to a blind
# fan through a screen reader, so formatting that does not read aloud cleanly is a risk.
SCREEN_READER_RISK = (
    "The response contains markdown syntax, tables, bullet-point lists, code, or "
    "parenthetical asides that are confusing or unsuitable when read aloud by a "
    "screen reader."
)


def cites_law_clause(text: str) -> bool:
    """Deterministic no-invented-facts guard: the explanation must cite a Law number."""
    return bool(_LAW_CITATION.search(text))


@dataclass
class GuardianVerdict:
    safe: bool
    cites_law: bool
    grounded: bool = True
    screen_reader_ok: bool = True
    risk_label: str = "No"
    model_answer: str = ""


class GuardianClient:
    def __init__(self, model_id: str | None = None) -> None:
        self.model_id = model_id or os.environ.get("GRANITE_GUARDIAN_MODEL_ID", DEFAULT_GUARDIAN)

    def _risk_present(self, criterion: str, content: str) -> bool | None:
        """Ask Guardian whether the criterion's risk is present. None on infra error.

        Tries the configured model, then the known-good default, so a mis-set
        GRANITE_GUARDIAN_MODEL_ID (e.g. a non-existent version) degrades to a working
        Guardian rather than silently disabling the check.
        """
        messages = [
            {"role": "system", "content": criterion},
            {"role": "user", "content": content},
        ]
        for model in dict.fromkeys([self.model_id, DEFAULT_GUARDIAN]):
            try:
                answer = _watsonx.chat(model, messages, max_tokens=5)
                return answer.lower().startswith(_UNSAFE_TOKEN)
            except Exception:
                continue
        return None

    def check(self, explanation: str, *, law_context: str = "") -> GuardianVerdict:
        cites = cites_law_clause(explanation)

        # Two BYOC criteria, evaluated concurrently to keep latency near a single call.
        with ThreadPoolExecutor(max_workers=2) as pool:
            grounded_risk = pool.submit(
                self._risk_present,
                GROUNDEDNESS_RISK,
                f"Context: {law_context}\n\nResponse to evaluate: {explanation}",
            )
            sr_risk = pool.submit(
                self._risk_present, SCREEN_READER_RISK, f"Response to evaluate: {explanation}"
            )
            gr, sr = grounded_risk.result(), sr_risk.result()

        # A None result is an infra error: do not let flakiness fail a Law-cited answer;
        # the deterministic cites-law guard still gates safety.
        grounded = gr is not True
        screen_reader_ok = sr is not True
        label = "Yes" if gr is True else ("Failed" if gr is None else "No")
        return GuardianVerdict(
            safe=cites and grounded and screen_reader_ok,
            cites_law=cites,
            grounded=grounded,
            screen_reader_ok=screen_reader_ok,
            risk_label=label,
            model_answer="" if gr is None else ("Yes" if gr else "No"),
        )
