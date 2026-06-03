"""IBM Granite reasoning client (watsonx ML REST, via the shared helper)."""

from __future__ import annotations

import os
from dataclasses import dataclass

from app.llm import _watsonx
from app.llm.guardian import cites_law_clause

DEFAULT_MODEL = "ibm/granite-4-h-small"


# Deterministic Law-11-grounded floors per language, used only when watsonx returns no
# usable text. The live Granite path produces the real in-language explanation; these
# keep the demo from ever showing nothing. Keyed by BCP-47-ish language prefixes.
_FALLBACKS: dict[str, tuple[str, str]] = {
    "en": (
        "When the ball was played, the most advanced attacker was {m:.2f} meters ahead of "
        "the second-to-last defender. That puts the player offside under Law 11.",
        "When the ball was played, the most advanced attacker was level with or behind the "
        "second-to-last defender by {m:.2f} meters. That keeps the player onside under Law 11.",
    ),
    "es": (
        "Según la Ley 11, el atacante más adelantado estaba por delante del penúltimo "
        "defensor por {m:.2f} metros cuando se jugó el balón, por lo que estaba "
        "correctamente en posición de fuera de juego.",
        "Según la Ley 11, el atacante más adelantado estaba a la altura o por detrás del "
        "penúltimo defensor por {m:.2f} metros, por lo que su posición era legal.",
    ),
    "fr": (
        "Selon la Loi 11, l'attaquant le plus avancé était devant l'avant-dernier "
        "défenseur de {m:.2f} mètres au moment où le ballon a été joué, il était donc "
        "correctement jugé hors-jeu.",
        "Selon la Loi 11, l'attaquant le plus avancé était au niveau ou derrière "
        "l'avant-dernier défenseur de {m:.2f} mètres, sa position était donc légale.",
    ),
    "pt": (
        "Segundo a Lei 11, o atacante mais avançado estava à frente do penúltimo "
        "defensor por {m:.2f} metros quando a bola foi jogada, por isso foi corretamente "
        "marcado impedimento.",
        "Segundo a Lei 11, o atacante mais avançado estava na linha ou atrás do penúltimo "
        "defensor por {m:.2f} metros, por isso a posição era legal.",
    ),
    "de": (
        "Nach Regel 11 war der vorderste Angreifer beim Abspiel {m:.2f} Meter vor dem "
        "vorletzten Verteidiger, daher wurde korrekt auf Abseits entschieden.",
        "Nach Regel 11 war der vorderste Angreifer auf gleicher Höhe mit oder hinter dem "
        "vorletzten Verteidiger ({m:.2f} Meter), daher war die Position regulär.",
    ),
}


def _lang_key(language: str) -> str:
    """Map a language name or code to a fallback key (English if unknown)."""
    low = language.lower()
    prefixes = {
        "en": ("en", "ingl"),
        "es": ("es", "span", "español", "espanol"),
        "fr": ("fr", "fren", "franç", "franc"),
        "pt": ("pt", "port"),
        "de": ("de", "germ", "deut"),
    }
    for key, starts in prefixes.items():
        if low.startswith(starts):
            return key
    return "en"


def _fallback_explanation(
    *, margin_meters: float, is_offside: bool, language: str = "English"
) -> str:
    """Deterministic Law-11-grounded floor when watsonx returns no usable text."""
    offside_tpl, onside_tpl = _FALLBACKS[_lang_key(language)]
    tpl = offside_tpl if is_offside else onside_tpl
    return tpl.format(m=abs(margin_meters))


# Deterministic floors for non-offside decisions (penalty, handball, ...). Each cites the
# Law number because the Guardian gate requires a Law citation. Used only when watsonx
# returns no usable text; the live path produces the real in-language explanation.
_DECISION_FALLBACKS: dict[str, str] = {
    "en": "Under Law {law}, the referee's decision was: {outcome}. The official applied that Law to the incident.",  # noqa: E501
    "es": "Según la Ley {law}, la decisión del árbitro fue: {outcome}. El colegiado aplicó esa Ley a la jugada.",  # noqa: E501
    "fr": "Selon la Loi {law}, la décision de l'arbitre était : {outcome}. L'arbitre a appliqué cette Loi à l'action.",  # noqa: E501
    "pt": "Segundo a Lei {law}, a decisão do árbitro foi: {outcome}. O árbitro aplicou essa Lei ao lance.",  # noqa: E501
    "de": "Nach Regel {law} lautete die Entscheidung des Schiedsrichters: {outcome}. Der Schiedsrichter wandte diese Regel an.",  # noqa: E501
}


def _fallback_decision(*, law: str, outcome: str, language: str = "English") -> str:
    return _DECISION_FALLBACKS[_lang_key(language)].format(law=law, outcome=outcome)


_ORACLE_PREFIX = {
    "en": "Under Law",
    "es": "Según la Ley",
    "fr": "Selon la Loi",
    "pt": "Segundo a Lei",
    "de": "Nach Regel",
}


def _first_sentence(law_text: str) -> str:
    """First real sentence of a Law (skipping the Docling markdown headers/comments)."""
    for line in law_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("<!--"):
            continue
        return line.split(". ")[0].strip().rstrip(".") + "."
    return law_text.strip()[:160]


def _fallback_answer(*, law: str, title: str, law_text: str, language: str = "English") -> str:
    """Grounded floor for the rule oracle: quote the retrieved Law, citing its number."""
    return f"{_ORACLE_PREFIX[_lang_key(language)]} {law} ({title}): {_first_sentence(law_text)}"


# Markers that mean the model echoed the prompt instructions instead of answering.
_LEAK_MARKERS = (
    "<explanation",
    "law text:",
    "decision data:",
    "do not invent",
    "cite the law number",
    "in 2 to 3 short sentences",
)


def _looks_like_prompt_leak(text: str) -> bool:
    low = text.lower()
    return any(marker in low for marker in _LEAK_MARKERS)


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
            f"warm language. Reply in {language}, in 2 to 3 short sentences. Lead with where "
            "the players were, then state the verdict, then cite the Law that justifies it "
            "(given-before-new order). Ground the explanation in the Law text below and cite "
            "the Law number. Do not invent any rule that is not in the Law text.\n\n"
            f"Law text:\n{law_text}\n\n"
            "Decision data: the most advanced attacker was "
            f"{abs(margin_meters):.2f} meters {relation} the second-to-last defender when "
            f"the ball was played. Verdict: {verdict}.\n\nExplanation:"
        )
        # watsonx greedy occasionally returns empty text, echoes the prompt scaffolding, or
        # (the fail-closed-to-floor case) produces a valid sentence that never cites the Law
        # number. Accept only a substantive, non-leaked, LAW-CITING reply; otherwise fall back
        # to the in-language deterministic floor, which always quotes the Law. This guarantees
        # every spoken explanation provably cites the Law (faithfulness by construction).
        for _ in range(3):
            text = self.generate(prompt, max_new_tokens=180, min_new_tokens=40).strip()
            if len(text) >= 20 and not _looks_like_prompt_leak(text) and cites_law_clause(text):
                return text
        return _fallback_explanation(
            margin_meters=margin_meters, is_offside=is_offside, language=language
        )

    def explain_decision(
        self,
        *,
        incident: str,
        outcome: str,
        law: str,
        law_text: str,
        language: str = "English",
    ) -> str:
        """Plain-language, Law-grounded explanation of a non-offside VAR decision (penalty,
        handball, ...) over the SAME retrieval + safety path as offside."""
        prompt = (
            "You are explaining a soccer VAR decision to a blind fan in plain, warm "
            f"language. Reply in {language}, in 2 to 3 short sentences. Lead with the "
            "incident, then state the decision, then cite the Law that justifies it "
            "(given-before-new order). Ground the explanation in the Law text below and cite "
            "the Law number. Do not invent any rule that is not in the Law text.\n\n"
            f"Law text:\n{law_text}\n\n"
            f"Incident: {incident} Verdict: {outcome}.\n\nExplanation:"
        )
        # Fail closed to the deterministic floor unless the reply is substantive, non-leaked,
        # and cites the Law number (every decision explanation must cite its Law).
        for _ in range(3):
            text = self.generate(prompt, max_new_tokens=180, min_new_tokens=40).strip()
            if len(text) >= 20 and not _looks_like_prompt_leak(text) and cites_law_clause(text):
                return text
        return _fallback_decision(law=law, outcome=outcome, language=language)

    def answer_question(
        self,
        *,
        question: str,
        law: str,
        title: str,
        law_text: str,
        language: str = "English",
    ) -> str:
        """Answer a free-text fan question grounded ONLY in the retrieved Law (the rule
        oracle). Off-topic questions are declined; the Guardian still checks groundedness."""
        prompt = (
            "You are a Laws-of-the-Game assistant for a blind soccer fan. Answer the "
            f"question in {language}, in 2 to 3 short sentences, grounded ONLY in the Law "
            "text below, and cite the Law number. If the question is not about the Laws of "
            "football, say you can only answer questions about the Laws of the Game. Do not "
            f"invent any rule not in the Law text.\n\nLaw text:\n{law_text}\n\n"
            f"Question: {question}\n\nAnswer:"
        )
        for _ in range(3):
            text = self.generate(prompt, max_new_tokens=180, min_new_tokens=40).strip()
            if len(text) >= 20 and not _looks_like_prompt_leak(text):
                return text
        return _fallback_answer(law=law, title=title, law_text=law_text, language=language)
