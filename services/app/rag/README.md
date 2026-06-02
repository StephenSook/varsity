# IFAB Laws RAG corpus

The retriever is grounded in the real IFAB Laws of the Game, ingested with Docling
and embedded with IBM Granite. The built index (`index/chunks.json` + `index/laws.faiss`)
is committed so the app, the container, and CI all ship the real corpus without
re-running the heavy ingest.

## Source

IFAB **Laws of the Game 2025/26 (single pages)**, theifab.com (230 pages). This is
the edition **in force for the June 2026 World Cup**: the 2026/27 edition only takes
effect 1 July 2026, after the tournament opens (11 June) and after the challenge
deadline, and its `...2026-27-single-pages` download is still a 404 as of 2026-06-02.
So 2025/26 is the correct, authoritative corpus.

## Fetching the PDF

`downloads.theifab.com` redirects plain non-interactive clients, but a request with
a normal browser `User-Agent` + `Referer` and redirect-follow gets the PDF:

```bash
curl -L -A "Mozilla/5.0 ... Chrome/124 Safari/537.36" -H "Referer: https://www.theifab.com/" \
  -o data/laws-of-the-game-2025-26-single-pages.pdf \
  "https://downloads.theifab.com/downloads/laws-of-the-game-2025-26-single-pages?l=en"
```

The PDF (`data/`) is gitignored; only the built index is committed.

## Ingest (build-time, runs once)

```bash
uv venv .venv-ingest && source .venv-ingest/bin/activate
uv pip install docling faiss-cpu numpy httpx python-dotenv
# Docling OOMs on Apple MPS for a 230-page PDF; convert on CPU first (cached sidecar):
python scripts/convert_ifab.py data/laws-of-the-game-2025-26-single-pages.pdf
# then chunk + Granite-embed + build the FAISS index (needs WATSONX_* in ../.env):
python -m app.rag.ingest data/laws-of-the-game-2025-26-single-pages.pdf
```

Pipeline:
1. **Docling** (IBM) converts the PDF to structured markdown.
2. It is split into **one chunk per Law** (tagged with the Law number and its
   canonical title), plus a dedicated **VAR protocol** chunk. The longest block per
   Law number is kept, which discards table-of-contents and cross-reference hits.
3. Each chunk is embedded with **IBM Granite** embeddings
   (`ibm/granite-embedding-278m-multilingual`, 768-dim) via watsonx. The title plus
   the Law's opening window is embedded (the model caps input at ~512 tokens); the
   full multi-page text stays in `chunks.json` for the Detail panel.
4. A **FAISS** `IndexFlatIP` over the L2-normalised vectors is persisted as
   `laws.faiss` alongside `chunks.json`.

## Retrieval (request time)

`app/rag/retriever.py` shares the Granite model id with the ingest, so the index and
the query live in the same vector space:

- **online** (watsonx creds present): embed the query with Granite, search the FAISS
  index (exact inner product = cosine).
- **offline / CI** (no network): **BM25** over the same corpus with an IDF-weighted
  title-match bonus, so a query naming a Law (`the penalty kick`) routes to that Law
  rather than to a body that merely repeats the words (Law 10's penalty shoot-out).

The IFAB-RAG MCP server (`app/mcp_servers/ifab_rag.py`) exposes this retriever as a
federated `retrieve_law` tool.
