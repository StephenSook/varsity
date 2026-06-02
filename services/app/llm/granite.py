"""IBM Granite reasoning client (watsonx ML REST, via the shared helper)."""

from __future__ import annotations

import os
from dataclasses import dataclass

from app.llm import _watsonx

DEFAULT_MODEL = "ibm/granite-4-h-small"


def _fallback_explanation(
    *, margin_meters: float, is_offside: bool, language: str = "English"
) -> str:
    """Deterministic Law-11-grounded floor when watsonx returns no usable text."""
    meters = abs(margin_meters)
    if language.lower().startswith(("span", "español")):
        if is_offside:
            return (
                f"Según la Ley 11, el atacante más adelantado estaba por delante del "
                f"penúltimo defensor por {meters:.2f} metros cuando se jugó el balón, "
                "por lo que estaba correctamente en posición de fuera de juego."
            )
        return (
            f"Según la Ley 11, el atacante más adelantado estaba a la altura o por "
            f"detrás del penúltimo defensor por {meters:.2f} metros, por lo que su "
            "posición era legal."
        )
    verdict = "offside" if is_offside else "onside"
    relation = "ahead of" if is_offside else "level with or behind"
    return (
        f"Under Law 11, the most advanced attacker was {relation} the second-to-last "
        f"defender by {meters:.2f} meters when the ball was played, so the player was "
        f"correctly judged {verdict}."
    )


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

    def generate(
        self,
        prompt: str,
        *,
        max_new_tokens: int = 200,
        min_new_tokens: int | None = None,
        decoding: str = "greedy",
    ) -> str:
        return _watsonx.generate(
            self.config.model_id,
            prompt,
            max_new_tokens=max_new_tokens,
            min_new_tokens=min_new_tokens,
            decoding=decoding,
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
        # watsonx greedy occasionally returns empty text; retry, then fall back to a
        # deterministic Law-grounded floor so the demo never produces no explanation.
        for _ in range(3):
            text = self.generate(prompt, max_new_tokens=180, min_new_tokens=40).strip()
            if len(text) >= 20:
                return text
        return _fallback_explanation(
            margin_meters=margin_meters, is_offside=is_offside, language=language
        )
