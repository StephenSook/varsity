"""Granite Vision build-time diagram captioning.

The IFAB Laws PDF contains DIAGRAMS (the offside-position figure in Law 11, the referee-signal
graphics in Laws 5/6). Plain Docling drops them, leaving ``<!-- image -->`` holes, so a blind fan
never gets the diagram's content. This module captions those figures with IBM Granite Vision 3.2 (a
vision-language model built for document and diagram understanding, on watsonx.ai) at BUILD
TIME, into accessible alt-text for the RAG corpus.

Honesty (a vision caption is model-generated, so it is fenced three ways):
1. GROUNDED: the surrounding Law text is passed with a faithfulness-bounded prompt.
2. GUARDED: a deterministic ``faithfulness_ok`` rejects a caption that asserts a verdict/opinion or
   shares no vocabulary with the Law text (a sign of drift or hallucination).
3. GATED: captions are a DRAFT requiring human review before they enter the live corpus, and the
   runtime loader reads only an APPROVED file. They are tiered "diagram description (AI-generated,
   build-time)", never presented as official IFAB text. This is an accessibility aid, not a rule.

The watsonx chat-with-image API (``/ml/v1/text/chat``, an ``image_url`` content part with a
base64 ``data:`` URL) is reused via ``_watsonx.chat``; the model id is configurable (verify it
against the watsonx catalogue, the default may need to be pinned per instance).
"""

from __future__ import annotations

import os

DEFAULT_VISION_MODEL = "ibm/granite-vision-3-2-2b"
# Phrases that betray a verdict/opinion rather than a literal description of the figure.
_FORBIDDEN = (
    "should have",
    "was wrong",
    "is wrong",
    "incorrect",
    "var got",
    "overturn",
    "i think",
    "probably",
    "in my opinion",
    "correct call",
)


def vision_model_id() -> str:
    return os.environ.get("GRANITE_VISION_MODEL_ID", DEFAULT_VISION_MODEL)


def caption_prompt(law_title: str, law_context: str) -> str:
    return (
        "You are writing alt-text for a blind fan. Describe ONLY what this diagram from the "
        f"IFAB Laws of the Game ({law_title}) literally shows: the positions and labels in the "
        "figure. Ground your description in the Law text and do NOT add any rule, verdict, or "
        "judgement the text does not state. Be concise: one or two sentences.\n\nLaw text:\n"
        + law_context
    )


def vision_messages(image_b64: str, prompt: str, *, mime: str = "image/png") -> list[dict]:
    """The watsonx chat messages for one image plus a grounding prompt (verified API shape:
    an ``image_url`` content part with a base64 ``data:`` URL, then the text instruction)."""
    return [
        {
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{image_b64}"}},
                {"type": "text", "text": prompt},
            ],
        }
    ]


def _tokens(text: str) -> list[str]:
    return "".join(ch.lower() if ch.isalnum() else " " for ch in text).split()


def faithfulness_ok(caption: str, law_context: str) -> bool:
    """Deterministic guard: reject a caption that is empty, asserts a verdict/opinion, or shares no
    real vocabulary with the Law text (so a hallucinated caption never enters the corpus)."""
    c = caption.lower().strip()
    if not c:
        return False
    if any(f in c for f in _FORBIDDEN):
        return False
    law_words = {w for w in _tokens(law_context) if len(w) > 4}
    cap_words = {w for w in _tokens(c) if len(w) > 4}
    return len(law_words & cap_words) >= 2


def caption_image(
    image_b64: str, *, law_title: str, law_context: str, mime: str = "image/png"
) -> str:
    """Live (build-time): caption one diagram image with Granite Vision. Returns '' if the caption
    fails the faithfulness guard, so an unfaithful caption never reaches the corpus."""
    from app.llm import _watsonx

    prompt = caption_prompt(law_title, law_context)
    text = _watsonx.chat(
        vision_model_id(), vision_messages(image_b64, prompt, mime=mime), max_tokens=160
    ).strip()
    return text if faithfulness_ok(text, law_context) else ""


def to_chunk(*, figure_id: str, law: str, caption: str) -> dict:
    """Build a clearly-tiered RAG chunk for an approved diagram caption."""
    return {
        "id": f"diagram:{figure_id}",
        "law": law,
        "title": f"{law} diagram (described)",
        "text": caption,
        "source": "granite-vision (AI-generated diagram description, build-time, human-reviewed)",
        "tier": "diagram-description",
    }
