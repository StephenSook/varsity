# VARSITY Architecture

## Container view

```mermaid
graph TB
  subgraph Browser["Browser (fan device)"]
    UI["React + Vite front end"]
    ARIA["ARIA live region"]
    SR["User's own screen reader"]
    NANO["Granite Nano on-device<br/>(Transformers.js + WebGPU)<br/>+ Orama offline RAG"]
    UI --> ARIA --> SR
  end

  subgraph Render["Render (containers)"]
    API["FastAPI backend<br/>(SSE)"]
    CF["IBM Context Forge<br/>MCP gateway"]
    RAGS["IFAB-RAG MCP server<br/>(FAISS)"]
    GEO["Match-data / geometry<br/>MCP server"]
    A2A["A2A narrator agent"]
  end

  WX["IBM watsonx<br/>Granite + Granite Guardian"]
  SM["Sportmonks / API-Football<br/>(live VAR events)"]
  SB["StatsBomb 360<br/>(open data, build-time)"]

  UI -->|SSE| API
  API --> CF
  CF --> RAGS
  CF --> GEO
  CF --> A2A
  CF --> WX
  API -->|poll| SM
  GEO --> SB
  UI -. airplane mode .-> NANO
```

## VAR-event sequence

```mermaid
sequenceDiagram
  participant T as Trigger<br/>(Sportmonks / API-Football / canned)
  participant G as Geometry<br/>(StatsBomb 360)
  participant C as Context Forge
  participant R as IFAB-RAG<br/>(FAISS)
  participant L as Granite<br/>(watsonx / on-device)
  participant S as Granite Guardian<br/>(BYOC)
  participant A as ARIA live region

  T->>G: VAR / offside event + freeze-frame
  G->>G: compute offside margin (left-to-right normalized)
  G->>C: structured decision JSON
  C->>R: retrieve governing Law
  R-->>C: Law 11 clause
  C->>L: prompt(decision + Law)
  L-->>C: plain-language explanation + cited clause
  C->>S: safety check ("must cite a Law clause")
  S-->>C: SAFE + score
  C-->>A: SSE push
  A->>A: screen reader speaks (assertive), before broadcast catches up
```

## Notes

- The federation registers exactly four services behind the gateway: IFAB-RAG MCP, match-data/geometry MCP, the A2A narrator agent, and the Granite coordinator. The `/admin` observability trace shows one VAR event fanning out across all four.
- The canned StatsBomb 360 path is the deterministic floor for the demo; the live trigger is the flourish. A cached replay buffer keeps the live path off the critical path.
- Offline mode runs the explanation entirely in the browser (Granite Nano + Orama), so it works with the network cut.
