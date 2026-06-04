"""Runtime loader for APPROVED diagram captions (the human-reviewed output of caption_diagrams.py).

If the approved file exists, the captions are available as clearly-tiered RAG chunks ("diagram
description", AI-generated at build time, human-reviewed). If it is absent, nothing is added, so
unverified captions never ship and the corpus is unchanged. The retriever appends these so a blind
fan asking about a Law also gets the described content of its figure. The captions live SEPARATELY
from the SHA-256-signed corpus (chunks.json), so the signature is never polluted by generated text.
"""

from __future__ import annotations

import json
from pathlib import Path

APPROVED = Path(__file__).parent / "index" / "diagram_captions.approved.json"


def approved_caption_chunks() -> list[dict]:
    """The approved, human-reviewed diagram-description chunks, or [] if none have been approved."""
    if not APPROVED.exists():
        return []
    try:
        data = json.loads(APPROVED.read_text())
    except (OSError, ValueError):
        return []
    from app.llm.vision import to_chunk

    out: list[dict] = []
    for c in data.get("captions", []):
        caption = str(c.get("caption", "")).strip()
        if caption:
            out.append(
                to_chunk(
                    figure_id=str(c.get("figure_id", "")),
                    law=str(c.get("law", "IFAB")),
                    caption=caption,
                )
            )
    return out
