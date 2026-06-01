"""Build-time ingestion of the IFAB Laws of the Game into a Law-tagged RAG index.

Pipeline: Docling converts the official IFAB PDF into clean structured text, the
text is split into chunks tagged by Law number, each chunk is embedded, and a
FAISS index is persisted for the IFAB-RAG MCP server to query at request time.

This runs ONCE at build time, never on the hot path. It needs the build-time deps
(requirements-data.txt) plus docling, sentence-transformers, and faiss-cpu, so it
is intentionally NOT imported by the app or the tests and not installed in CI.

Source corpus: IFAB Laws of the Game 2026/27 (single pages), published on
theifab.com/documents. The direct download on downloads.theifab.com is gated
behind a browser session, so fetch the PDF via the documents-page download button
(or a Playwright session) and pass its local path here.

Usage:
    python -m app.rag.ingest path/to/ifab_laws_2026_27.pdf --out app/rag/index
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

LAW_HEADING = re.compile(r"\bLaw\s+(\d{1,2})\b", re.IGNORECASE)


def pdf_to_markdown(pdf_path: Path) -> str:
    """Convert the IFAB PDF to structured markdown with Docling (IBM)."""
    from docling.document_converter import DocumentConverter  # heavy, build-time only

    result = DocumentConverter().convert(str(pdf_path))
    return result.document.export_to_markdown()


def chunk_by_law(markdown: str) -> list[dict[str, str]]:
    """Split the Laws text into chunks tagged with the Law number they belong to."""
    lines = markdown.splitlines()
    chunks: list[dict[str, str]] = []
    current_law = "0"
    buffer: list[str] = []

    def flush() -> None:
        text = "\n".join(buffer).strip()
        if text:
            chunks.append({"law": current_law, "text": text})

    for line in lines:
        match = LAW_HEADING.search(line)
        if match and line.strip().lower().startswith("law"):
            flush()
            buffer = [line]
            current_law = match.group(1)
        else:
            buffer.append(line)
    flush()
    return chunks


def build_index(chunks: list[dict[str, str]], out_dir: Path) -> None:
    """Embed each chunk and persist a FAISS index plus the chunk metadata."""
    import faiss  # build-time only
    from sentence_transformers import SentenceTransformer  # build-time only

    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    embeddings = model.encode(
        [c["text"] for c in chunks], normalize_embeddings=True, convert_to_numpy=True
    )
    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)

    out_dir.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(out_dir / "laws.faiss"))
    (out_dir / "chunks.json").write_text(json.dumps(chunks, indent=2))
    print(f"indexed {len(chunks)} chunks -> {out_dir}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest the IFAB Laws into a FAISS index.")
    parser.add_argument("pdf", type=Path, help="path to the IFAB Laws PDF")
    parser.add_argument("--out", type=Path, default=Path("app/rag/index"))
    args = parser.parse_args()

    markdown = pdf_to_markdown(args.pdf)
    chunks = chunk_by_law(markdown)
    laws_found = sorted({c["law"] for c in chunks}, key=int)
    print(f"chunks: {len(chunks)} | laws: {laws_found}")
    build_index(chunks, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
