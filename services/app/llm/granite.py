"""IBM Granite reasoning client (watsonx ML REST, via the shared helper)."""

from __future__ import annotations

import os
from dataclasses import dataclass

from app.llm import _watsonx

DEFAULT_MODEL = "ibm/granite-4-h-small"


@dataclass
class GraniteConfig:
    model_id: str

    @classmethod
    def from_env(cls) -> GraniteConfig:
        return cls(model_id=os.environ.get("GRANITE_MODEL_ID", DEFAULT_MODEL))


class GraniteClient:
    """Granite text-generation client. Auth + transport live in app.llm._watsonx."""

    def __init__(self, config: GraniteConfig | None = None) -> None:
        self.config = config or GraniteConfig.from_env()

    def generate(self, prompt: str, *, max_new_tokens: int = 200, decoding: str = "greedy") -> str:
        return _watsonx.generate(
            self.config.model_id, prompt, max_new_tokens=max_new_tokens, decoding=decoding
        )

    def explain_offside(
        self,
        *,
        margin_meters: float,
        is_offside: bool,
        law_text: str,
        language: str = "English",
    ) -> str:
        """Generate a plain-language, Law-grounded explanation of an offside decision."""
        verdict = "offside" if is_offside else "onside"
        relation = "ahead of" if is_offside else "behind"
        prompt = (
            "You are explaining a soccer VAR offside decision to a blind fan in plain, "
            f"warm language. Reply in {language}, in 2 to 3 short sentences. Ground the "
            "explanation in the Law text below and cite the Law number. Do not invent any "
            "rule that is not in the Law text.\n\n"
            f"Law text:\n{law_text}\n\n"
            "Decision data: the most advanced attacker was "
            f"{abs(margin_meters):.2f} meters {relation} the second-to-last defender when "
            f"the ball was played. Verdict: {verdict}.\n\nExplanation:"
        )
        return self.generate(prompt, max_new_tokens=180)
