"""Build-time ingestion of the IFAB Laws of the Game into a Law-tagged RAG index.

Pipeline: Docling (IBM) converts the official IFAB PDF into clean structured
markdown, the text is split into one chunk per Law (tagged by Law number and its
official title), each chunk is embedded with IBM Granite embeddings via watsonx,
and a FAISS index is persisted next to the chunk metadata. The retriever and the
IFAB-RAG MCP server query that index at request time.

This runs ONCE at build time, never on the hot path. It needs the build-time deps
(docling + faiss-cpu + numpy) plus watsonx creds for the Granite embeddings, so it
is intentionally NOT imported by the app or the tests.

Source corpus: IFAB Laws of the Game 2025/26 (single pages), theifab.com. The
2025/26 edition is the Laws in force for the June 2026 World Cup; the 2026/27
edition only takes effect 1 July 2026 (after the tournament opens and after the
challenge deadline), so 2025/26 is the correct, authoritative corpus.

The Granite embedding model MUST match the one the retriever uses to embed queries
at runtime, otherwise index and query live in different vector spaces and the
"semantic" retrieval silently returns nonsense.

Usage:
    # convert + chunk + embed + index in one go (re-uses a cached .md sidecar):
    python -m app.rag.ingest data/laws-of-the-game-2025-26-single-pages.pdf
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

INDEX_DIR = Path(__file__).resolve().parent / "index"
GRANITE_EMBED_MODEL = "ibm/granite-embedding-278m-multilingual"
EMBED_CHARS = 1500  # ~375 tokens, safely under the model's ~512-token input cap
EMBED_BATCH = 8

# The 17 Laws of the Game have fixed official titles. Tagging each chunk with the
# canonical title (rather than whatever the PDF heading happens to render as) keeps
# the corpus clean and the Detail panel's "full Law text" honest.
LAW_TITLES: dict[str, str] = {
    "1": "The Field of Play",
    "2": "The Ball",
    "3": "The Players",
    "4": "The Players' Equipment",
    "5": "The Referee",
    "6": "The Other Match Officials",
    "7": "The Duration of the Match",
    "8": "The Start and Restart of Play",
    "9": "The Ball In and Out of Play",
    "10": "Determining the Outcome of a Match",
    "11": "Offside",
    "12": "Fouls and Misconduct",
    "13": "Free Kicks",
    "14": "The Penalty Kick",
    "15": "The Throw-in",
    "16": "The Goal Kick",
    "17": "The Corner Kick",
    "VAR": "Video Assistant Referee (VAR) protocol",
}

# A line is a Law boundary when, stripped of markdown heading marks, it starts with
# "Law <n>" (optionally followed by the title). TOC lines match too, but they are
# discarded later by keeping only the longest block per Law.
LAW_BOUNDARY = re.compile(r"^#*\s*Law\s+(\d{1,2})\b", re.IGNORECASE)
# The VAR protocol follows Law 17 in the single-pages PDF. It is directly on-topic
# for VARSITY, so it is captured as its own chunk rather than bleeding into Law 17.
VAR_START = re.compile(r"^#*\s*Protocol principles", re.IGNORECASE)
# Everything from here on is back-matter (quality programme, summary of changes,
# glossary) and is dropped so it does not pollute the last captured section.
POST_LAWS = re.compile(
    r"^#*\s*(FIFA Quality Programme|Outline summary of Law changes|Glossary)", re.IGNORECASE
)


def pdf_to_markdown(pdf_path: Path) -> str:
    """Convert the IFAB PDF to structured markdown with Docling, caching the result.

    Docling on a 230-page PDF is slow, so the markdown is cached in a ``.md`` sidecar
    next to the PDF and re-used on subsequent runs (delete it to force a reconvert).
    """
    cache = pdf_path.with_suffix(".docling.md")
    if cache.exists():
        return cache.read_text()
    from docling.document_converter import DocumentConverter  # heavy, build-time only

    markdown = DocumentConverter().convert(str(pdf_path)).document.export_to_markdown()
    cache.write_text(markdown)
    return markdown


def chunk_by_law(markdown: str) -> list[dict[str, str]]:
    """One chunk per Law: split on Law headings, keep the longest block per Law number.

    A 230-page single-pages PDF mentions "Law N" in the table of contents, in
    cross-references, and at the real section start. Grouping every block under its
    Law number and keeping the longest one discards the short TOC/reference hits and
    keeps the substantive section text.
    """
    lines = markdown.splitlines()
    blocks: list[tuple[str, list[str]]] = []
    current_law = "0"
    buffer: list[str] = []

    def flush() -> None:
        blocks.append((current_law, buffer))

    for line in lines:
        stripped = line.strip()
        law_match = LAW_BOUNDARY.match(stripped)
        if POST_LAWS.match(stripped):
            flush()
            current_law = "0"  # drop back-matter
            buffer = [line]
        elif VAR_START.match(stripped):
            flush()
            current_law = "VAR"
            buffer = [line]
        elif law_match and 1 <= int(law_match.group(1)) <= 17:
            flush()
            current_law = law_match.group(1)
            buffer = [line]
        else:
            buffer.append(line)
    flush()

    longest: dict[str, str] = {}
    for law, buf in blocks:
        if law == "0":
            continue
        text = "\n".join(buf).strip()
        if len(text) > len(longest.get(law, "")):
            longest[law] = text

    def _order(law: str) -> tuple[int, int]:
        return (0, int(law)) if law.isdigit() else (1, 0)  # numeric Laws first, then VAR

    chunks: list[dict[str, str]] = []
    for law in sorted(longest, key=_order):
        chunks.append(
            {"law": law, "title": LAW_TITLES.get(law, f"Law {law}"), "text": longest[law]}
        )
    return chunks


def build_index(chunks: list[dict[str, str]], out_dir: Path) -> None:
    """Embed each chunk with Granite (watsonx) and persist a FAISS index + metadata."""
    import faiss  # build-time + runtime (faiss-cpu)
    import numpy as np

    from app.llm import _watsonx  # reuse the runtime watsonx REST helper

    # The Granite embedding model caps input at ~512 tokens, so embed the title plus
    # the Law's opening window (which defines it) rather than the full multi-page text.
    # The full text still lives in chunks.json for the Detail panel; only the vector
    # used for retrieval is built from the window.
    texts = [f"{c['title']}. {c['text'][:EMBED_CHARS]}" for c in chunks]
    vectors: list[list[float]] = []
    for i in range(0, len(texts), EMBED_BATCH):
        vectors.extend(_watsonx.embed(GRANITE_EMBED_MODEL, texts[i : i + EMBED_BATCH]))
    matrix = np.asarray(vectors, dtype="float32")
    faiss.normalize_L2(matrix)  # cosine via inner product

    index = faiss.IndexFlatIP(matrix.shape[1])
    index.add(matrix)

    out_dir.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(out_dir / "laws.faiss"))
    (out_dir / "chunks.json").write_text(json.dumps(chunks, ensure_ascii=False, indent=2))
    print(f"indexed {len(chunks)} chunks ({matrix.shape[1]}-dim Granite) -> {out_dir}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest the IFAB Laws into a FAISS index.")
    parser.add_argument("pdf", type=Path, help="path to the IFAB Laws PDF")
    parser.add_argument("--out", type=Path, default=INDEX_DIR)
    parser.add_argument(
        "--no-embed",
        action="store_true",
        help="convert + chunk only (write chunks.json), skip the Granite/FAISS step",
    )
    args = parser.parse_args()

    markdown = pdf_to_markdown(args.pdf)
    chunks = chunk_by_law(markdown)
    laws_found = [c["law"] for c in chunks]
    sizes = ", ".join(f"L{c['law']}:{len(c['text'])}" for c in chunks)
    print(f"chunks: {len(chunks)} | laws: {laws_found}\n  sizes -> {sizes}")

    if args.no_embed:
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "chunks.json").write_text(json.dumps(chunks, ensure_ascii=False, indent=2))
        print(f"wrote chunks.json ({len(chunks)} chunks), skipped embedding")
        return 0

    build_index(chunks, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
