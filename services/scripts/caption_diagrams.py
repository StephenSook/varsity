"""Build-time: extract the figures from the IFAB Laws PDF and caption them with Granite Vision.

Gated: runs only when the PDF and the watsonx credentials are present; otherwise it is a no-op (no
draft written), so it never affects CI or the deterministic demo. It writes a DRAFT captions file
that a human reviews and promotes to ``diagram_captions.approved.json`` (the runtime's source). Each
figure is grounded by its own page text, and every caption passes the deterministic faithfulness
guard in ``app.llm.vision`` before it is kept.

Run:  python -m services.scripts.caption_diagrams   (from the services/ dir, with WATSONX_* set)
"""

from __future__ import annotations

import base64
import json
import os
import sys
from pathlib import Path

PDF = Path("data/laws-of-the-game-2025-26-single-pages.pdf")
DRAFT = Path("app/rag/index/diagram_captions.draft.json")


def _has_creds() -> bool:
    return all(os.environ.get(k) for k in ("WATSONX_API_KEY", "WATSONX_PROJECT_ID"))


def extract_figures(pdf_path: Path) -> list[tuple[str, int, bytes, str]]:
    """Return (figure_id, page_no, png_bytes, page_text) for each embedded figure. Needs PyMuPDF."""
    import fitz  # PyMuPDF (build-time dependency only)

    doc = fitz.open(pdf_path)
    out: list[tuple[str, int, bytes, str]] = []
    for page_no in range(len(doc)):
        page = doc[page_no]
        page_text = page.get_text()
        for i, img in enumerate(page.get_images(full=True)):
            xref = img[0]
            pix = fitz.Pixmap(doc, xref)
            if pix.n - pix.alpha >= 4:  # CMYK or similar -> RGB
                pix = fitz.Pixmap(fitz.csRGB, pix)
            out.append((f"p{page_no + 1}_i{i}", page_no + 1, pix.tobytes("png"), page_text))
    return out


def run() -> int:
    if not PDF.exists() or not _has_creds():
        print("caption_diagrams: PDF or WATSONX creds missing; skipping (no draft written).")
        return 0
    from app.llm import vision

    captions = []
    for figure_id, page, png, page_text in extract_figures(PDF):
        caption = vision.caption_image(
            base64.b64encode(png).decode(),
            law_title=f"page {page}",
            law_context=page_text,
        )
        if caption:
            captions.append({"figure_id": figure_id, "page": page, "caption": caption})
    DRAFT.parent.mkdir(parents=True, exist_ok=True)
    DRAFT.write_text(
        json.dumps({"captions": captions, "status": "draft-review-required"}, indent=2)
    )
    print(f"caption_diagrams: wrote {len(captions)} faithful draft captions to {DRAFT}")
    return 0


if __name__ == "__main__":
    sys.exit(run())
