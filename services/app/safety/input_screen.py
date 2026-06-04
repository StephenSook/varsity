"""Input screening for the free-text rule oracle (the LLM01 attack surface).

The oracle takes a fan's free-text question and feeds it to Granite. That is the one place
untrusted text reaches the model, so it gets defense-in-depth:

- a deterministic HAP (hate / abuse / profanity) screen - the always-on floor; abusive
  input is declined before any model call. The IBM watsonx HAP moderation
  (``granite-guardian-hap-38m`` family) is the heavier model tier, see ``safety/hap.py``;
- a deterministic prompt-injection / jailbreak screen (LLM01): "ignore previous
  instructions", system-prompt probes, role-override, delimiter breakouts;
- spotlighting (delimiting): even a clean question is wrapped as quoted DATA in the
  prompt, so any instruction embedded in it is treated as text, not as a command.

On a HAP or injection hit we FAIL CLOSED: the oracle declines (it already declines
off-topic questions), the question is withheld from the model, and no model call is made.
Deterministic, offline, sub-millisecond. This screens the INPUT; the existing Guardian
groundedness gate + the verification panel screen the OUTPUT.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Unambiguous profanity / abuse stems (word-boundary). Football vocabulary (offside, foul,
# card, tackle, dive, header) does not overlap these, so false positives are unlikely; the
# comprehensive tier is the IBM watsonx HAP guardrail (safety/hap.py).
_HAP = re.compile(
    r"\b(?:f+u+c+k+|sh[i1!]+t+|b[i1!]tch|bastard|assh[o0]le|c+u+n+t+|dickhead|"
    r"motherf\w*|wanker|tw[a4]t|n[i1]gg\w*|f[a4]gg?\w*|retard\w*)",
    re.IGNORECASE,
)

# Prompt-injection / jailbreak markers (LLM01). Conservative: targets the canonical
# override phrasings rather than guessing intent from ordinary questions.
_INJECTION = re.compile(
    # "ignore everything / ignore all ..." (objects that never appear in a real rules
    # question) OR "ignore [the/your/previous/...] <instruction|prompt|...>".
    r"ignore\s+(?:everything|all\b)"
    r"|ignore\s+(?:all\s+|the\s+|your\s+)?(?:previous|above|prior|earlier)\s+"
    r"(?:instruction|prompt|message|rule)"
    r"|disregard\s+(?:all|the|your|previous|any)"
    r"|forget\s+(?:everything|all|your|the\s+above|previous)"
    r"|(?:reveal|show|print|repeat|output)\s+(?:your\s+|the\s+)?(?:system\s+)?(?:prompt|instructions)"
    r"|system\s+prompt|your\s+(?:system\s+)?(?:prompt|instructions)"
    r"|you\s+are\s+now|act\s+as\s+(?:a|an|if|though)|pretend\s+(?:you|to\s+be|that)"
    r"|role-?play\s+as|developer\s+mode|jailbreak|\bDAN\b|do\s+anything\s+now"
    r"|new\s+instructions?\s*:|override\s+(?:the|your|all|any)"
    r"|<\|[^|]*\|>|```\s*system|\[/?INST\]|<<SYS>>",
    re.IGNORECASE | re.DOTALL,
)

# Multilingual injection markers (the oracle answers in 5 languages, so the floor screens
# them too). Found by red-teaming the live oracle: an English-only screen missed a Spanish
# injection (the downstream Law-grounding held, but the floor should catch it). High-signal
# override verbs in es/fr/pt/de; tuned to avoid the legit "ignorar la senal" form.
_INJECTION_INTL = re.compile(
    r"ignor[ae]\s+(?:todas?|las|toutes?|les)\b"  # es "ignora todas/las", fr "ignore les/toutes"
    r"|olvida\s+(?:todo|las|tus|las\s+instruc)"  # es "olvida todo/las instrucciones"
    r"|revela\s+(?:tu|el|su)\s+(?:prompt|instruc)"  # es "revela tu prompt"
    r"|oublie[z]?\s+(?:tout|les|toutes)"  # fr "oublie tout"
    r"|r[ée]v[èe]le\s+(?:ton|le|tes)\s+(?:prompt|instruction)"  # fr "revele ton prompt"
    r"|esque[cç]a\s+(?:tudo|as|todas)"  # pt "esqueca tudo"
    r"|revele\s+(?:o|seu|teu)\s+(?:prompt|instru)"  # pt "revele o prompt"
    r"|ignoriere\s+(?:alle|alles|die)"  # de "ignoriere alle"
    r"|vergiss\s+(?:alle|alles|die)"  # de "vergiss alle"
    r"|zeige\s+(?:mir\s+)?(?:dein|den)\s+(?:prompt|anweisung)",  # de "zeige deinen prompt"
    re.IGNORECASE,
)

# Leetspeak normalization: red-teaming found "1gnore prev1ous 1nstruct1ons" slipped the
# floor. We screen a de-leeted shadow copy too (the original text is unchanged), so common
# digit/symbol substitutions cannot dodge the patterns.
_LEET = str.maketrans(
    {"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s"}
)


def _deleet(text: str) -> str:
    return text.translate(_LEET)

# Spotlighting delimiters: the prompt instructs the model to treat everything between them
# strictly as the fan's question (data), never as instructions to follow.
SPOTLIGHT_OPEN = "<<<FAN_QUESTION>>>"
SPOTLIGHT_CLOSE = "<<<END_FAN_QUESTION>>>"

# Per-language polite decline (matches the 5 narration languages). The oracle already
# declines off-topic questions; an unsafe question is declined the same neutral way.
_DECLINE: dict[str, str] = {
    "english": "I can only help with respectful questions about the Laws of the Game. "
    "Please rephrase your question.",
    "spanish": "Solo puedo ayudar con preguntas respetuosas sobre las Reglas de Juego. "
    "Por favor, reformula tu pregunta.",
    "french": "Je ne peux repondre qu'aux questions respectueuses sur les Lois du Jeu. "
    "Merci de reformuler votre question.",
    "portuguese": "So posso ajudar com perguntas respeitosas sobre as Regras do Jogo. "
    "Por favor, reformule a sua pergunta.",
    "german": "Ich kann nur respektvolle Fragen zu den Spielregeln beantworten. "
    "Bitte formuliere deine Frage neu.",
}


# Accept both full narration names ("Spanish") and BCP-47 codes ("es", "es-ES").
_LANG_BY_PREFIX = {
    "en": "english",
    "es": "spanish",
    "fr": "french",
    "pt": "portuguese",
    "de": "german",
}


@dataclass(frozen=True)
class ScreenResult:
    ok: bool
    category: str | None  # None | "hap" | "injection"
    reason: str


def screen(text: str) -> ScreenResult:
    """Deterministic HAP + prompt-injection screen. Returns ok=False to FAIL CLOSED.

    Screens the raw text AND a de-leeted shadow copy (so "1gnore" is caught), against the
    English and multilingual injection patterns. No regex floor is complete - a homoglyph or
    a novel paraphrase can still slip; those are defended downstream by spotlighting +
    Law-grounding (see docs/RED-TEAM.md), not hidden.
    """
    t = text or ""
    variants = (t, _deleet(t))
    if any(_HAP.search(v) for v in variants):
        return ScreenResult(False, "hap", "abusive language")
    if any(_INJECTION.search(v) or _INJECTION_INTL.search(v) for v in variants):
        return ScreenResult(False, "injection", "prompt-injection pattern")
    return ScreenResult(True, None, "clean")


def spotlight(text: str) -> str:
    """Wrap untrusted user text as clearly-delimited DATA (spotlighting / datamarking).

    Strips the delimiters in a LOOP, not a single pass: a single replace is defeated by
    nesting (``<<<END_FAN_<<<END_FAN_QUESTION>>>QUESTION>>>`` collapses into a real close
    delimiter), so a crafted question could otherwise break out of the data block.
    """
    safe = text or ""
    while SPOTLIGHT_OPEN in safe or SPOTLIGHT_CLOSE in safe:
        safe = safe.replace(SPOTLIGHT_OPEN, "").replace(SPOTLIGHT_CLOSE, "")
    return f"{SPOTLIGHT_OPEN}\n{safe}\n{SPOTLIGHT_CLOSE}"


def decline_message(language: str = "English") -> str:
    key = (language or "english").strip().lower()
    if key in _DECLINE:  # a full narration name ("spanish")
        return _DECLINE[key]
    return _DECLINE.get(_LANG_BY_PREFIX.get(key[:2], "english"), _DECLINE["english"])
