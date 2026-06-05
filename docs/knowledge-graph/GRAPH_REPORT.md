# Graph Report - docs  (2026-06-05)

## Corpus Check
- 30 files · ~121,559 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 199 nodes · 211 edges · 18 communities detected
- Extraction: 73% EXTRACTED · 25% INFERRED · 0% AMBIGUOUS · INFERRED: 52 edges (avg confidence: 0.8)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Explain-Not-Adjudicate & Attribution|Explain-Not-Adjudicate & Attribution]]
- [[_COMMUNITY_Confidence Calibration|Confidence Calibration]]
- [[_COMMUNITY_Offside Geometry Engine|Offside Geometry Engine]]
- [[_COMMUNITY_SSE Pipeline & Federation|SSE Pipeline & Federation]]
- [[_COMMUNITY_App & Deployment Topology|App & Deployment Topology]]
- [[_COMMUNITY_Accessibility (WCAG 2.2 AA)|Accessibility (WCAG 2.2 AA)]]
- [[_COMMUNITY_Multilingual Narration|Multilingual Narration]]
- [[_COMMUNITY_Law 11 Proof & Argumentation|Law 11 Proof & Argumentation]]
- [[_COMMUNITY_Spatial Audio & Earcons|Spatial Audio & Earcons]]
- [[_COMMUNITY_On-Device Voice & ASR|On-Device Voice & ASR]]
- [[_COMMUNITY_Brand Submission Banner|Brand: Submission Banner]]
- [[_COMMUNITY_Red-Team & Injection Defense|Red-Team & Injection Defense]]
- [[_COMMUNITY_Audio Perception (Sonification)|Audio Perception (Sonification)]]
- [[_COMMUNITY_Licensing & Deployment Risk|Licensing & Deployment Risk]]
- [[_COMMUNITY_Brand App Icon|Brand: App Icon]]
- [[_COMMUNITY_Privacy & Data Minimization|Privacy & Data Minimization]]
- [[_COMMUNITY_Safety Guardrails (HAP)|Safety Guardrails (HAP)]]
- [[_COMMUNITY_Corpus Attribution|Corpus Attribution]]

## God Nodes (most connected - your core abstractions)
1. `Four Federated Backends Fan-Out` - 7 edges
2. `Illustrative Offside Margin (x-distance, meters)` - 6 edges
3. `Descriptive Geometry (geometry_descriptors.py, pure Python)` - 6 edges
4. `Confidence Calibration Receipt (calibration.py)` - 6 edges
5. `On-device ASR default (Whisper-base, Transformers.js/WebGPU)` - 6 edges
6. `WCAG 2.2 AA Conformance Target` - 6 edges
7. `Assertive aria-live Verdict Region` - 6 edges
8. `VARSITY Submission Banner` - 5 edges
9. `GUM Uncertainty Budget (gum.py, JCGM 100:2008)` - 5 edges
10. `Bayesian Posterior P=Phi(m/sigma) + Credible Interval` - 5 edges

## Surprising Connections (you probably didn't know these)
- `Kokoro-82M on-device TTS (WebGPU)` --semantically_similar_to--> `On-device ASR default (Whisper-base, Transformers.js/WebGPU)`  [INFERRED] [semantically similar]
  docs/WEBGPU.md → docs/VOICE.md
- `ifab-rag MCP (retrieve_law, FAISS)` --semantically_similar_to--> `BM25 Offline Retrieval Floor`  [INFERRED] [semantically similar]
  docs/federation.md → docs/benchmarks/rag-eval.md
- `IBM Granite (granite-4-h-small reasoning)` --semantically_similar_to--> `Granite Coordinator (explain_offside)`  [INFERRED] [semantically similar]
  docs/IBM_STACK.md → docs/federation.md
- `SHA-256 Provenance Manifest` --semantically_similar_to--> `SHA-256 Corpus Signing`  [INFERRED] [semantically similar]
  docs/SAFETY_CASE.md → docs/SECURITY-HARDENING.md
- `Assertive aria-live Verdict Region` --semantically_similar_to--> `HTML lang Attribute (SC 3.1.1 / 3.1.2)`  [INFERRED] [semantically similar]
  docs/ACCESSIBILITY.md → docs/ACCESSIBILITY-SR-LANG.md

## Hyperedges (group relationships)
- **** — uncertainty_gum_budget, uncertainty_bayesian_posterior, calibration_receipt, sources_measured_ledger [INFERRED 0.85]
- **** — descriptors_orient2d_exact, descriptors_robust_alpha_shape, descriptors_h0_persistence_grouping, descriptors_convex_hull_free_space [EXTRACTED 1.00]
- **** — verification_z3_smt_properties, verification_hypothesis_property, verification_metamorphic_invariants, geometry_law11_reference_line [EXTRACTED 1.00]
- **On-device all-IBM/WebGPU offline stack** —  [INFERRED 0.85]
- **Confidence/margin made audible** —  [INFERRED 0.85]
- **Honesty/non-adjudication fencing across modalities** —  [INFERRED 0.75]
- **SSE Named-Event Pipeline Flow** —  [EXTRACTED 1.00]
- **Context Forge Four-Backend Fan-Out** —  [EXTRACTED 1.00]
- **IBM Granite/watsonx Model Stack** —  [EXTRACTED 1.00]
- **Explain-Not-Adjudicate Scope Lock** —  [INFERRED 0.90]
- **Deterministic Fail-Closed Defense-in-Depth** —  [INFERRED 0.85]
- **Blind-User-Cannot-Visually-Check Threat Rationale** —  [INFERRED 0.80]
- **Honesty-marked scope across docs (named gaps not claimed)** —  [INFERRED 0.85]
- **Deterministic floor guarantees output when AI/feed unavailable** —  [INFERRED 0.80]
- **Screen-reader-native spoken delivery is the primary product surface** —  [INFERRED 0.80]

## Communities

### Community 0 - "Explain-Not-Adjudicate & Attribution"
Cohesion: 0.11
Nodes (22): Explains, Not Adjudicates, Nominative Fair Use (Names/Marks), Non-Affiliation (FIFA/IFAB), Adjudication-Bait/Fabrication Held, Deterministic Law-Quoting Floor, Coded Explain-Not-Adjudicate Scope, Layered Faithfulness Chain, Granite Guardian Advisory Judge (+14 more)

### Community 1 - "Confidence Calibration"
Cohesion: 0.11
Nodes (21): Calibrated-by-Construction (Phi is exact Bayesian posterior), ECE 0.34% + Brier 0.060 (40k seeded draws), IPCC Verbal Hedge from Confidence, Overconfident Control (sigma halved, ECE 4.16%, ~12x worse), Confidence Calibration Receipt (calibration.py), SAOT/Dragon Precision Contrast (what VARSITY is NOT), HOMOGRAPHY_CORRELATION r=0.70 (Type-B, Szulc 2026), Honesty-Gate Exclusions (fabricated 91% figure, LocSim tolerance) (+13 more)

### Community 2 - "Offside Geometry Engine"
Cohesion: 0.12
Nodes (19): Convex Hull + free_space_behind_line_m2 (Voronoi-lite), Descriptive Geometry (geometry_descriptors.py, pure Python), Defensive Grouping (MST-gap, H0 persistence), Honest Exclusions (Voronoi/H1/tropical dropped on principle), orient2d_sign Exact Rational Predicate (Shewchuk-family), Line Thickness via 2D PCA (minor eigenvalue), block_concavity_ratio (data-adaptive alpha-shape, exact Delaunay), Defensive Line Tilt via Theil-Sen Estimator (+11 more)

### Community 3 - "SSE Pipeline & Federation"
Cohesion: 0.12
Nodes (18): Canned StatsBomb 360 Deterministic Floor, Geometry Stage (offside margin), SSE Named-Event Pipeline, StatsBomb 360 (build-time open data), A2A Narrator Agent (message/send), IBM Context Forge MCP Gateway, Four Federated Backends Fan-Out, Granite Coordinator (explain_offside) (+10 more)

### Community 4 - "App & Deployment Topology"
Cohesion: 0.12
Nodes (18): ARIA Live Region (assertive), FastAPI Backend (SSE), On-Device Offline Mode (Granite Nano + Orama), React + Vite Front End, IBM Cloud Code Engine (on-theme), Render Backend (render.yaml, /health), Vercel Front End (apps/web, VITE_BACKEND_URL), watsonx Secrets (API_KEY/PROJECT_ID, never committed) (+10 more)

### Community 5 - "Accessibility (WCAG 2.2 AA)"
Cohesion: 0.12
Nodes (17): Assertive aria-live Verdict Region, Dual-track Design (screen-reader layer parallel to visuals), Global focus-visible Ring + Focus Appearance, Forced-colors / Windows High Contrast Mode, Keyboard Map + Stage Scrubber, Skip Link + Focus Not Obscured, Target Size 24x24 (axe wcag22aa gate), AT Test Matrix (NVDA/VoiceOver/TalkBack) (+9 more)

### Community 6 - "Multilingual Narration"
Cohesion: 0.18
Nodes (13): Five-language Narration (EN/ES/FR/PT/DE), Glossary Prompt-injection into Granite, Deterministic In-language Floors, Per-language Number Verbalization (speech.ts), Terminology-Hit-Rate Eval (reference-free, /multilingual), TBX IFAB Termbase (termbase.py), Bundled-TTS Fallback (the only hard guarantee), AT Compatibility Matrix (lang on live updates) (+5 more)

### Community 7 - "Law 11 Proof & Argumentation"
Cohesion: 0.18
Nodes (11): ASPIC+ / Dung structured-argumentation mapping, Undermining/rebutting/undercutting attackers (A1-A4), law11.py proof tree (pure-Python forward-chaining), No runnable ASPIC+/Dung solver built (no extra power), Coded non-adjudication (defer-to-official strict premise), faithfulness_ok deterministic guard, Granite Vision 3.2 diagram captioning (build-time), Draft -> human-reviewed approved.json gate (+3 more)

### Community 8 - "Spatial Audio & Earcons"
Cohesion: 0.22
Nodes (9): Brewster earcon parameters (BREWSTER), ISO 226:2003 equal-loudness gain (iso226Gain), HRTF spatial scan (spatialScanPlan), Binary left/right pan claim (not navigation map), Front-hemisphere clamp (40.7% front-back confusion), Individualized HRTF declined (near-zero marginal benefit), ±50° max azimuth (Drullman & Bronkhorst 2000), Web Audio PannerNode HRTF (fixed, no SOFA) (+1 more)

### Community 9 - "On-Device Voice & ASR"
Cohesion: 0.28
Nodes (9): Granite Speech opt-in all-IBM ASR (experimental), On-device ASR default (Whisper-base, Transformers.js/WebGPU), On-device privacy posture (no upload/account/analytics), Web Speech API zero-download floor (may upload audio), Deterministic Law-grounded fallback + provenance, IBM Granite 4.0 Nano 350M (offline phrasing), Kokoro-82M on-device TTS (WebGPU), WebGPU not in Playwright CI (probe skips, not fakes) (+1 more)

### Community 10 - "Brand: Submission Banner"
Cohesion: 0.29
Nodes (8): Broadcast-Graphic Aesthetic, Deep Navy Night-Stadium Scene, Signal-Green Offside Line Sweep, Perspective Football Pitch, IBM Stack Chips (Granite, Guardian, Context Forge, World Cup 2026), VARSITY Submission Banner, Tagline: Hear the Why Behind Every VAR Call, VARSITY Serif Wordmark

### Community 11 - "Red-Team & Injection Defense"
Cohesion: 0.25
Nodes (8): Cyrillic Homoglyph Residual, Honesty-Gated Reporting, Leetspeak Breach + De-leet Fix, 8-Vector Live Probes, Multilingual Injection Miss + Fix, GET /red_team CI Regression, Prompt-Injection/Jailbreak Screen, Spotlighting (Delimited Data)

### Community 12 - "Audio Perception (Sonification)"
Cohesion: 0.33
Nodes (6): confidenceVoice (vibrato + inharmonicity timbre), Critical-band roughness/beating (Plomp & Levelt 1965), Plomp-Levelt margin chord (marginChord), sonify.ts perceptual layer (pure-math, unit-tested), Spatial chord verdict preamble, confidenceEarcon (loudness + broadband noise texture)

### Community 13 - "Licensing & Deployment Risk"
Cohesion: 0.33
Nodes (6): Apache-2.0, No Runtime Copyleft, Partnership-First Deployment, Risk Summary Matrix, localStorage Preferences, On-Device Offline Mode (WebGPU), Server-Side API Keys

### Community 14 - "Brand: App Icon"
Cohesion: 0.6
Nodes (5): VARSITY App Icon, Deep Navy Rounded-Square Tile, Glowing Signal-Green Offside Line, Glowing Blue Player/Ball Marker Dot, Signal-Green Brand Color

### Community 15 - "Privacy & Data Minimization"
Cohesion: 0.5
Nodes (4): DP/Federated Out of Scope, GDPR Article 9 Special-Category, No Analytics, Cookies, Telemetry, No PII / No Disability Status

### Community 16 - "Safety Guardrails (HAP)"
Cohesion: 0.67
Nodes (3): watsonx HAP Guardrail Tier, Deterministic HAP Screen, Oracle Fail-Closed Decline

### Community 17 - "Corpus Attribution"
Cohesion: 1.0
Nodes (2): IFAB Laws Fair-Use Corpus, StatsBomb Open Data Attribution

## Knowledge Gaps
- **76 isolated node(s):** `Signal-Green Brand Color`, `VARSITY Serif Wordmark`, `Tagline: Hear the Why Behind Every VAR Call`, `IBM Stack Chips (Granite, Guardian, Context Forge, World Cup 2026)`, `Level-Is-Onside Tolerance` (+71 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Corpus Attribution`** (2 nodes): `IFAB Laws Fair-Use Corpus`, `StatsBomb Open Data Attribution`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Illustrative Offside Margin (x-distance, meters)` connect `Offside Geometry Engine` to `Confidence Calibration`?**
  _High betweenness centrality (0.024) - this node is a cross-community bridge._
- **Why does `GUM Uncertainty Budget (gum.py, JCGM 100:2008)` connect `Confidence Calibration` to `Offside Geometry Engine`?**
  _High betweenness centrality (0.022) - this node is a cross-community bridge._
- **Why does `Span Tree (geometry/law/granite/guardian)` connect `SSE Pipeline & Federation` to `App & Deployment Topology`?**
  _High betweenness centrality (0.012) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `On-device ASR default (Whisper-base, Transformers.js/WebGPU)` (e.g. with `IBM Granite 4.0 Nano 350M (offline phrasing)` and `Kokoro-82M on-device TTS (WebGPU)`) actually correct?**
  _`On-device ASR default (Whisper-base, Transformers.js/WebGPU)` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Signal-Green Brand Color`, `VARSITY Serif Wordmark`, `Tagline: Hear the Why Behind Every VAR Call` to the rest of the system?**
  _76 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Explain-Not-Adjudicate & Attribution` be split into smaller, more focused modules?**
  _Cohesion score 0.11 - nodes in this community are weakly interconnected._
- **Should `Confidence Calibration` be split into smaller, more focused modules?**
  _Cohesion score 0.11 - nodes in this community are weakly interconnected._