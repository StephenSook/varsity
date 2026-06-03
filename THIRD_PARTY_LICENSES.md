# Third-party licenses

VARSITY is licensed under Apache-2.0 (see `LICENSE`). It uses the third-party components below.
Licenses were verified against each component's published metadata (PyPI / npm registry / Hugging
Face model card / repository `LICENSE`) on 2026-06-03. Components without a standard SPDX identifier
are noted explicitly; nothing here is GPL.

## IBM AI models (Apache-2.0)

| Component | License | Role |
|---|---|---|
| IBM Granite 4.x (incl. Granite 4.0 Nano on-device) | Apache-2.0 | Explanation generation |
| IBM Granite Guardian 3.x | Apache-2.0 | Groundedness / safety check |
| IBM Granite embedding (multilingual) | Apache-2.0 | RAG embeddings |

## Backend (Python)

| Component | License | Notes |
|---|---|---|
| fastapi | MIT | API framework |
| uvicorn | BSD-3-Clause | ASGI server |
| pydantic | MIT | |
| sse-starlette | BSD-3-Clause | SSE streaming |
| httpx | BSD-3-Clause | HTTP client |
| python-dotenv | BSD-3-Clause | |
| mcp (MCP Python SDK) | MIT | MCP servers |
| a2a-sdk | Apache-2.0 | A2A narrator agent |
| faiss-cpu | MIT | Vector index |
| numpy | BSD-3-Clause | |
| opentelemetry-api / -sdk / -instrumentation-fastapi | Apache-2.0 | Tracing |
| IBM Docling | MIT | IFAB PDF parsing (build-time) |
| IBM Context Forge (mcp-contextforge-gateway) | Apache-2.0 | MCP gateway federation |
| statsbombpy | **No SPDX license: StatsBomb User Agreement (proprietary)** | StatsBomb data access; this is a data-use agreement, not a code license. Attribution to StatsBomb required (see `docs/LEGAL.md`). |
| mplsoccer | MIT | Pitch geometry (build-time) |

## Frontend (JS/TS)

| Component | License | Notes |
|---|---|---|
| react, react-dom | MIT | |
| three, @react-three/fiber | MIT | Decorative 3D (aria-hidden) |
| @huggingface/transformers (Transformers.js) | Apache-2.0 | On-device inference runtime |
| kokoro-js | Apache-2.0 | On-device TTS (sighted read-aloud) |
| @orama/orama | Apache-2.0 | On-device offline RAG |
| lenis | MIT | Smooth scroll |
| **gsap** | **Not SPDX: GSAP "Standard" no-charge license (Webflow)** | Free for commercial web use; a proprietary agreement, not open source. https://gsap.com/standard-license |

## Dev / CI only (not shipped in the product)

| Component | License | Notes |
|---|---|---|
| pytest | MIT | |
| hypothesis | **MPL-2.0** (weak, file-level copyleft) | Property-based tests; dev-only, does not affect the distributed app |
| z3-solver | MIT | Formal verification (CI) |
| typescript, @playwright/test | Apache-2.0 | |
| axe-core, @axe-core/playwright | **MPL-2.0** | Accessibility CI; dev-only |
| vite, vitest, tailwindcss, vite-plugin-pwa, @tailwindcss/vite | MIT | |

## Number-to-words

VARSITY's spoken-number verbalizer (`apps/web/src/speech.ts`) is implemented in-house. The
`num2words` PyPI library is **LGPL-2.1** (copyleft) and is deliberately not used; the npm `n2words`
library is MIT but was not needed for our small number range. This keeps the runtime dependency
tree free of copyleft.

## Data and rules

- **StatsBomb Open Data**: used under the StatsBomb Public Data User Agreement (non-commercial
  research/educational; attribution required). VARSITY consumes it and produces a new derivative
  (an explanation), and does not redistribute the raw event data.
- **IFAB Laws of the Game**: Copyright The IFAB; cited and paraphrased under fair-use principles
  for a non-commercial educational/accessibility purpose. See `docs/LEGAL.md`.
