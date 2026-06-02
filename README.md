<p align="center">
  <img src="docs/brand/banner.png" alt="VARSITY. Hear the why behind every VAR call. A real-time, screen-reader-native, IFAB-grounded AI explainer of VAR and offside decisions, built on IBM Granite, Granite Guardian, and Context Forge for the World Cup 2026 challenge." width="100%" />
</p>

# VARSITY

**Verifiable, Accessible, Rule-grounded Soccer Transparency Interpreter for You.**

VARSITY is a real-time, screen-reader-native, IFAB-grounded AI explainer of VAR and offside decisions, built as a fan product. When a Video Assistant Referee review happens, VARSITY retrieves the governing Law of the Game, computes the offside geometry, generates a plain-language explanation of why the decision was made, and speaks it through the fan's own screen reader, in their language, before the broadcast picture catches up.

Built for the IBM SkillsBuild AI Builders Challenge (June 2026, Soccer / AI / World Cup).

## The problem

A blind football fan is often the last person in the room to understand a VAR call. Audio description is improving and major tournaments increasingly offer it, but even great commentary rarely explains the rule-grounded reason behind a contested VAR or offside decision as it happens. The decision data exists (the applied Law, the offside geometry, the structured outcome) yet it lives only in visual pipelines: stadium screens, broadcast overlays, and officials-only tools. No deployed product turns that into rule-grounded natural language delivered through a blind fan's own accessibility channel in real time. VARSITY adds that layer. It complements audio description and commentary, it does not replace them.

## What makes it different

The first system that is **all four at once**: real-time, screen-reader-native, IFAB-Laws-grounded, and fan-facing, with offside coverage. Prior art (X-VARS, CVPR 2024; SoccerRef-Agents, 2026) is offline, referee-facing, and foul-only. VARSITY is what those would look like if they shipped to the fan who needs it.

## Capability honesty

Every capability is labeled by how it is wired, and each is verifiable in this repository. We do not claim a roadmap item as if it were built.

- **Wired-live**: runs in this repo and has been exercised end to end (tests and/or a live run this session).
- **Integration**: real, built, demo-scoped, but not on the hot path of the core demo.
- **Roadmap**: designed and specified, not yet built. Listed so the scope is honest.

| Capability | Tier | Where / how to verify |
|---|---|---|
| Offside-margin geometry from StatsBomb 360 freeze-frames | Wired-live | `services/app/geometry.py` + `services/tests/test_geometry.py` (real 2022 World Cup frame, 5.45 m) |
| IFAB-Laws RAG: Docling to FAISS, IBM Granite embeddings online + BM25 offline | Wired-live | `services/app/rag/` over the real **IFAB Laws of the Game 2025/26** (18 Docling-ingested chunks incl. the VAR protocol); evaluated in `docs/benchmarks/rag-eval.md` |
| RAG retrieval evaluation (Hit-Rate@k + MRR over a golden IFAB set) | Wired-live | `services/evals/` + `docs/benchmarks/rag-eval.md`; CI-gated (Hit@5 = 1.00, every offside query routes to Law 11) |
| IBM Granite reasoning via watsonx (rule-grounded explanation citing the Law) | Wired-live | `services/app/llm/granite.py` (5 languages, prompt-leak guard); live run this session |
| Granite Guardian groundedness + Law-citation safety | Wired-live | `services/app/llm/guardian.py` + tests |
| OpenTelemetry per-request span tree (geometry to law to granite to guardian) | Wired-live | `services/app/observability.py`, `services/app/pipeline.py`; spans printed per `GET /stream` request |
| Context Forge MCP gateway + A2A narrator round-trip | Wired-live | `services/app/mcp_servers/`, `app/a2a_agent/` (real `message/send` round-trip in `client.py` + test), `app/federation.py`, `docs/federation.md` |
| Live-trigger resilience + "VAR is reviewing" announcement | Wired-live | `services/app/triggers/`, `GET /stream/live` emits the transitional review event; front-end Live / Replay toggle |
| SSE pipeline to a screen-reader `aria-live` region | Wired-live | `services/app/main.py`, `apps/web/src/Demo.tsx` (pre-registered region, verbosity-gated, re-announce-safe) |
| 5-language narration (EN / ES / FR / PT / DE) | Wired-live | `apps/web/src/Demo.tsx`; the same call re-narrated, the `lang` attribute flips the spoken voice |
| Spatial audio: listener-centred HRTF + animated offside crossing + semantic verdict earcon | Wired-live | `apps/web/src/sonify.ts`; the attacker tone moves past the centred offside line, then a major (onside) / minor+tritone (offside) earcon |
| SVG offside-line visualization synced to the computed margin | Wired-live | `apps/web/src/OffsidePitch.tsx` (margin on screen equals the geometry value) |
| Broadcast-delay ticker (Phenix-cited offset, live-measured delta) | Wired-live | `apps/web/src/BroadcastTicker.tsx`; lead = the OTA broadcast offset minus VARSITY's measured latency |
| Keyboard power-mode + stage scrubber + verbosity modes | Wired-live | `apps/web/src/Demo.tsx`, `StageScrubber.tsx`, `KeyboardHelp.tsx`; every action by one keypress, any step re-narrated |
| Shareable on-device audio clip | Wired-live | `apps/web/src/share.ts`, `tts.ts`; Kokoro WAV via the Web Share API with download / clipboard fallback |
| On-device offline mode (Transformers.js + WebGPU, Granite 4.0 Nano) | Wired-live | `apps/web/src/offline.ts`; a Law-grounded explanation fully in-browser, no backend (verified 0 backend calls), deterministic floor when WebGPU is absent |
| Read-aloud for the sighted track (Web Speech floor + Kokoro-82M on-device) | Wired-live | `apps/web/src/tts.ts`; the accessibility path stays the user's own screen reader |
| 3D / GSAP cinematic hero | Wired-live | `apps/web/src/Hero3D.tsx` (React Three Fiber pitch, lazy-loaded, `aria-hidden`, motion-gated) + a GSAP intro |

## Architecture

One VAR offside event flows from a trigger, through the geometry and rule-grounding
backends coordinated by the IBM Context Forge MCP gateway, into a Granite explanation
that Granite Guardian gates, and out over SSE to the screen reader. See
[docs/federation.md](docs/federation.md) for the four-backend federation and the
VAR-event sequence diagram.

```mermaid
flowchart LR
    subgraph Trigger
      SM["Sportmonks<br/>Goal Under Review"] --> RES{resilient<br/>resolver}
      AF["API-Football<br/>final outcomes"] --> RES
      RB["cached replay<br/>buffer (floor)"] --> RES
      SB["StatsBomb 360<br/>canned frame"] --> RES
    end

    RES --> GEO["match-geometry MCP<br/>offside margin (m)"]

    subgraph Gateway["IBM Context Forge MCP gateway"]
      GEO --> COORD["Granite coordinator"]
      RAG["ifab-rag MCP<br/>Law 11 retrieval"] --> COORD
      A2A["A2A narrator agent"] --> COORD
    end

    COORD --> GRAN["IBM Granite (watsonx)<br/>rule-grounded explanation"]
    GRAN --> GUARD["Granite Guardian<br/>groundedness + Law cite"]
    GUARD --> SSE["FastAPI SSE<br/>/stream"]
    SSE --> LIVE["aria-live region"]
    LIVE --> SR(["Blind fan's<br/>own screen reader"])

    SSE -. decorative, aria-hidden .-> VIZ["SVG offside-line viz<br/>+ spatial-audio cue"]

    OFF["On-device offline mode<br/>Granite Nano · WebGPU"] -. no network .-> LIVE
```

The canned StatsBomb path is the deterministic floor; the live trigger is a resilient flourish that falls back to a cached replay buffer. The screen-reader layer is always parallel to (and independent of) the decorative visual and audio layers.

See [docs/IBM_STACK.md](docs/IBM_STACK.md) for every IBM component mapped to its file path and how to verify it is running, and [docs/ACCESSIBILITY.md](docs/ACCESSIBILITY.md) for the WCAG conformance target, the `aria-live` design decision, and the screen-reader test matrix.

## Evaluation

The IFAB retrieval is measured, not asserted. A golden set of 20 VAR/offside questions mapped to the governing Law is run against the real retriever, scored directly (no inflated harness). Full report: [docs/benchmarks/rag-eval.md](docs/benchmarks/rag-eval.md).

| Path | Hit@1 | Hit@3 | Hit@5 | MRR |
|---|---|---|---|---|
| BM25 (offline / CI, deterministic) | 0.90 | 1.00 | 1.00 | 0.942 |
| Granite embeddings + FAISS (online) | 0.95 | 0.95 | 1.00 | 0.963 |

Every offside question routes to **Law 11 at rank 1**, and the two offline near-misses (goal-line to goal-kick, referee to VAR) recover by rank 2-3. CI fails if Hit@5 drops below 1.0.

## Tech

Only what is built and running is listed here. Roadmap technologies are in the table above.

- **Front end:** React 19, Vite 6, TypeScript, Tailwind CSS v4, a multi-section cinematic site (React Three Fiber + GSAP hero, Lenis smooth scroll, scroll-reveals, liquid-glass), an SVG offside-line visualization, a listener-centred Web Audio HRTF spatial-audio engine with a semantic verdict earcon, a broadcast-delay ticker, keyboard power-mode + a stage scrubber + verbosity modes, a shareable on-device audio clip, an on-device offline mode (Transformers.js + WebGPU, Granite 4.0 Nano), a sighted-track read-aloud (Web Speech API + Kokoro-82M), 5-language narration (EN/ES/FR/PT/DE), ARIA live regions.
- **Backend:** FastAPI + SSE, IBM Context Forge (MCP gateway), IBM Granite + Granite Guardian via watsonx (raw ML REST), Docling to FAISS IFAB-Laws RAG, OpenTelemetry tracing, the official `mcp` and `a2a-sdk` SDKs (IFAB-RAG and geometry MCP servers, an A2A narrator agent with a real `message/send` round-trip), Sportmonks / API-Football triggers with a cached replay buffer, pure-Python offside geometry over StatsBomb 360 data.
- **Accessibility:** WCAG 2.2 AA, a pre-registered ARIA live region (`assertive` for the explicitly-requested verdict) with a re-announce-safe fix and verbosity control, screen-reader-native delivery, a `lang` attribute that switches the spoken voice, full keyboard support, decorative motion gated behind `prefers-reduced-motion`, axe-core + Playwright accessibility CI.

## Accessibility validation

We are validating VARSITY with blind and low-vision football fans and audio-description users. A first-hand reply from a blind supporter on an audio-description community list confirmed the core need: current match commentary often leaves them unsure what is happening on the pitch, and clear information on the rules during a contested moment would be genuinely helpful. That is exactly the gap VARSITY targets, alongside (not instead of) the audio description and commentary fans already rely on. Outreach records and any personal details are kept private and are not in this repository.

## Develop

```bash
# front end
cd apps/web && npm install && npm run dev
# backend
cd services && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && uvicorn main:app --reload
```

CI runs lint, typecheck, tests, and build on every push and pull request.

## License

Apache-2.0. See [LICENSE](LICENSE).
