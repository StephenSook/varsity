# CLAUDE.md: VARSITY build guide

Neutral build guide for anyone (human or AI assistant) working in this repository. Stack, commands, conventions, and the accuracy guardrails.

## What this is

VARSITY: a real-time, screen-reader-native, IFAB-Laws-grounded AI explainer of VAR and offside decisions. See `README.md` for the product and `docs/architecture.md` for the design.

## Layout

- `apps/web`: React + Vite + TypeScript front end.
- `services`: FastAPI backend + the MCP servers (IFAB-RAG, match-data/geometry) + the A2A narrator agent. The offside-margin geometry lives in `services/app/geometry.py` (StatsBomb 360 freeze-frames); the RAG (Docling ingestion + FAISS index over the IFAB Laws) lives in `services/app/rag/`.
- `infra`: docker-compose, Context Forge config, `VERSIONS.lock`.
- `docs`: architecture diagrams and ADRs.

## Commands

- Front end: `cd apps/web && npm install && npm run dev | build | test`.
- Backend: `cd services && uvicorn main:app --reload`; tests `pytest`.
- Lint/format: `ruff` (Python), `eslint` + `prettier` (TS).

## Conventions

- Conventional Commits, subject <= 100 chars. Atomic commits, branch-first, PR + rebase-merge.
- Typecheck + lint + tests must pass before commit. CI runs them on every push/PR.
- Never commit secrets. Use `.env.example` as the template; real values go in `.env` (gitignored).

## Accessibility (non-negotiable)

- The spoken explanation is delivered through a pre-registered `aria-live` region the user's own screen reader speaks. Do not ship a custom TTS on the accessibility path.
- Mutate the live region's `textContent` in place; never destroy and recreate the node.
- `aria-live="assertive"` for the decision moment, `polite` for routine state.
- All decorative motion and 3D is `aria-hidden` and gated behind `prefers-reduced-motion`. Every action is keyboard-reachable. Target WCAG 2.2 AA.

## Accuracy guardrails (use correct facts only)

- Cite Granite tool-calling as "4th on BFCL, top open-license at release" (EMNLP 2024). Do not cite a "54.8 on BFCLv3" figure.
- Context Forge plugin hooks are `tool_pre_invoke` / `tool_post_invoke` / `prompt_pre_fetch` / `prompt_post_fetch`. There is no "CPEX".
- The transitional "review in progress" event comes from Sportmonks (`Goal Under Review`); API-Football emits final outcomes only.
- StatsBomb attack direction is always left-to-right; normalize before computing offside margins.
- Every generated explanation must cite a real Law id retrieved from the corpus. Granite Guardian enforces this (Bring Your Own Criteria: "response must cite a Law clause"). A unit test asserts it.
