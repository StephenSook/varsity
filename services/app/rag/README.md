# IFAB Laws RAG corpus

## Source

IFAB **Laws of the Game 2026/27 (single pages)**, published on
[theifab.com/documents](https://www.theifab.com/documents/?documentType=laws-of-the-game&language=en&years=all).
Confirmed published as of 2026-06-01 (both 2025/26 and 2026/27 editions are
available). The 2026/27 Laws take effect 1 July 2026; the World Cup may implement
the approved changes early.

## Fetching the PDF

The direct download on `downloads.theifab.com` redirects non-interactive clients
to the homepage (anti-bot), so the PDF cannot be fetched with a plain `curl`.
Fetch it once via the documents-page Download button in a browser, or with a
Playwright session, and save it locally (gitignored), then run the ingest.

## Ingest (build-time, runs once)

```bash
# install build-time deps + docling
pip install -r ../../requirements-data.txt docling sentence-transformers
python -m app.rag.ingest path/to/ifab_laws_2026_27.pdf --out app/rag/index
```

This uses **Docling** (IBM) to convert the PDF to structured text, splits it into
chunks tagged by Law number, embeds each chunk with `all-MiniLM-L6-v2`, and writes
a FAISS index (`laws.faiss`) plus `chunks.json`. The IFAB-RAG MCP server queries
that index at request time to ground each explanation in a real Law clause.

## Must-have corpus contents (per the build plan)

- Law 11 full text plus the four back-pocket distinctions (position vs offence,
  opponents' half, second-last opponent vs defender, hands/arms excluded).
- The 2026/27 VAR changes (second-yellow review, optional corner-kick review,
  mistaken-identity wording, in-stadium PA announcements).
