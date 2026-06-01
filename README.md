# VARSITY

**Verifiable, Accessible, Rule-grounded Soccer Transparency Interpreter for You.**

VARSITY is a real-time, screen-reader-native, IFAB-grounded AI explainer of VAR and offside decisions, built as a fan product. When a Video Assistant Referee review happens, VARSITY retrieves the governing Law of the Game, computes the offside geometry, generates a plain-language explanation of why the decision was made, and speaks it through the fan's own screen reader, in their language, before the broadcast picture catches up.

Built for the IBM SkillsBuild AI Builders Challenge (June 2026, Soccer / AI / World Cup).

## The problem

A blind football fan is often the last person in the room to understand a VAR call. The decision data exists (the applied Law, the offside geometry, the structured outcome) but it lives only in visual pipelines: stadium screens, broadcast overlays, and officials-only tools. No deployed product translates that into rule-grounded natural language delivered through a blind fan's accessibility channel in real time. VARSITY closes that last-mile gap.

## What makes it different

The first system that is **all four at once**: real-time, screen-reader-native, IFAB-Laws-grounded, and fan-facing, with offside coverage. Prior art (X-VARS, CVPR 2024; SoccerRef-Agents, 2026) is offline, referee-facing, and foul-only. VARSITY is what those would look like if they shipped to the fan who needs it.

## Architecture

See [docs/architecture.md](docs/architecture.md) for the container diagram and the VAR-event sequence diagram.

Pipeline: trigger (live event feed or a deterministic StatsBomb 360 freeze-frame) -> offside-margin geometry -> IFAB-Laws RAG -> IBM Granite reasoning via the IBM Context Forge MCP gateway -> Granite Guardian safety -> Server-Sent Events -> an `aria-live` region the screen reader speaks.

## Tech

- **Front end:** React, Vite, TypeScript, Tailwind CSS v4, GSAP, three.js / React Three Fiber, Web Audio API, Transformers.js (on-device Granite Nano for offline mode).
- **Backend:** FastAPI, IBM Context Forge (MCP gateway), IBM Granite + Granite Guardian via watsonx, Docling (IFAB Laws ingestion), FAISS, statsbombpy + mplsoccer (geometry), A2A narrator agent.
- **Accessibility:** WCAG 2.2 AA, ARIA live regions, screen-reader-native delivery, full keyboard support, `prefers-reduced-motion` respected.

## Capability honesty

Every capability is labeled by how it is wired (live / integration / accelerator) and is verifiable in this repository. See the judges section once published.

## Develop

```bash
# front end
cd apps/web && npm install && npm run dev
# backend
cd services && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && uvicorn main:app --reload
```

## License

Apache-2.0. See [LICENSE](LICENSE).
