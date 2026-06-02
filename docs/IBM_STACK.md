# IBM stack in VARSITY

VARSITY runs on the IBM Granite + watsonx + open-source-AI stack end to end. Every
component below is wired and exercised in this repository, not aspirational. Each row
maps the component to its code and to a concrete way to verify it is really running.

| IBM component | What it does in VARSITY | Code | How to verify it is running |
|---|---|---|---|
| **IBM Granite** (`ibm/granite-4-h-small`, via watsonx ML REST) | Generates the plain-language, Law-grounded explanation of the VAR/offside decision, in the fan's language | `services/app/llm/granite.py`, `services/app/llm/_watsonx.py` | Run `GET /stream/canned`; the `granite` SSE stage reports the model id, the `verdict` carries the generated text. The OpenTelemetry span `granite` records `varsity.model`. |
| **Granite Guardian** (`ibm/granite-guardian-3-8b`) | Groundedness + Law-citation safety check on the explanation before it reaches the fan | `services/app/llm/guardian.py` | The `guardian` SSE stage returns `safe` / `grounded` / `cites_law`; `services/tests/test_guardian.py` covers it. |
| **Granite embeddings** (`ibm/granite-embedding-278m-multilingual`) | Embeds the IFAB Law corpus and the query for online semantic retrieval | `services/app/rag/ingest.py`, `services/app/rag/retriever.py` | `python -m evals.run_eval --embeddings` reports the Granite+FAISS retrieval scores; the FAISS index is built with the same model id. |
| **Granite 4.0 Nano** (`onnx-community/granite-4.0-350m-ONNX-web`, Transformers.js + WebGPU) | On-device offline explanation, fully in-browser with no network | `apps/web/src/offline.ts` | Click **Offline mode**; with WebGPU the provenance reads "Granite Nano (WebGPU), no network", with 0 backend requests in the Network tab. See `docs/WEBGPU.md`. |
| **Docling** | Converts the official IFAB Laws of the Game 2025/26 PDF into structured, Law-tagged chunks at build time | `services/app/rag/ingest.py`, `services/scripts/convert_ifab.py` | `services/app/rag/index/chunks.json` is the Docling output (18 chunks incl. the VAR protocol); `services/app/rag/README.md` documents the run. |
| **Context Forge** (MCP gateway) | Federates the IFAB-RAG and geometry MCP servers + the A2A narrator behind one gateway, with an admin/observability trace | `services/app/mcp_servers/`, `services/app/federation.py`, `docs/federation.md` | The MCP servers expose `retrieve_law` / `compute_offside_margin` as gateway tools; `docs/federation.md` shows the four-backend fan-out. |
| **A2A** (`a2a-sdk` 1.1.0) | A narrator agent serving an Agent Card and handling `message/send`, callable as a real A2A agent | `services/app/a2a_agent/narrator.py`, `services/app/a2a_agent/client.py` | `services/tests/test_narrator.py::test_a2a_message_send_round_trip` resolves the Agent Card and round-trips a real `message/send` to get the narration. |
| **watsonx** (foundation-model serving) | Hosts Granite + Granite Guardian + Granite embeddings; the single auth + transport surface | `services/app/llm/_watsonx.py` (IAM token caching, generation, embeddings) | Reads `WATSONX_API_KEY` / `WATSONX_PROJECT_ID`; the live pipeline smoke prints a real Granite explanation citing Law 11. |

## Quick proof

```bash
cd services && source .venv/bin/activate
# one VAR event end to end through Granite + Guardian + the real RAG, with OTel spans:
python -m uvicorn app.main:app --port 8000 &
curl -N "http://localhost:8000/stream/canned?language=English"
# real retrieval scores over the Docling-ingested IFAB corpus:
python -m evals.run_eval
# a real A2A message/send round-trip to the narrator agent:
python -m pytest tests/test_narrator.py -q
```
