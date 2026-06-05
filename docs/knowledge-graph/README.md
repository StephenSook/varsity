# VARSITY knowledge map

A navigable knowledge graph of the VARSITY design corpus: every concept in the 30
documents under `docs/`, the relationships between them, and the clusters those
relationships form. It is a second, concept-level view of the project that sits
alongside the data-flow diagram in the main [README](../../README.md#architecture).

## How it was built

Generated from the documentation with the `graphify` pipeline (semantic extraction +
Louvain community detection). The input was the 30 files in `docs/` (27 markdown design
docs, the RAG-eval benchmark, and the two brand images), about 122k words. Every edge is
tagged by how it was found: `EXTRACTED` (stated in the source), `INFERRED` (a reasonable
cross-document link), or `AMBIGUOUS` (flagged, not hidden). The same honesty discipline
the product applies to its own claims applies to this graph.

Result: **199 concepts, 211 relationships, 18 communities.**

## Files

The first four files are the auto-extracted concept map (199 nodes from the docs). The 3D
file is a hand-curated architecture view (26 nodes, the data-flow spine), and the Gource
time-lapse is the animated repo-history companion.

| File | What it is | How to view |
|---|---|---|
| `graph.svg` | Static force-directed map of all 199 concepts, coloured by community | Renders inline on GitHub; open the file |
| `graph.html` | Interactive force-directed graph of all 199 concepts (drag, zoom, hover, search) | Download and open in any browser, no server needed |
| `graph-3d.html` | Cinematic 3D architecture graph: 26 curated nodes in 7 brand-coloured layers, glowing orbs, bloom, animated data-flow particles, auto-orbit | Open via a render proxy (see below) or download and serve locally |
| `GRAPH_REPORT.md` | Plain-language audit: god nodes, surprising connections, suggested questions, per-community cohesion | Renders on GitHub |
| `graph.json` | Raw graph (nodes + edges + communities) for GraphRAG / Neo4j / Gephi | Machine-readable |

## Moving and cinematic views

- **3D architecture graph** (`graph-3d.html`): a curated WebGL view of the pipeline, the
  trigger to geometry to RAG to Granite to Guardian to screen-reader flow, in the brand
  navy and signal-green, with bloom and auto-orbit. It loads three.js from a CDN, so view
  it through a render proxy (`https://raw.githack.com/StephenSook/varsity/main/docs/knowledge-graph/graph-3d.html`)
  or download it and run `python3 -m http.server` locally. GitHub will not execute a
  committed `.html` inline.
- **Gource time-lapse**: an animated video of the whole repository history (197 commits
  over 4.7 days) as a growing tree of files, in the brand palette with milestone captions.
  It is rendered to a 1080p60 MP4 and kept as a demo asset outside the repo (a ~37 MB
  binary does not belong in git history). Regenerate it any time with `gource` piped to
  `ffmpeg`; the exact command is recorded in the session notes.

## What the graph surfaces

The most-connected concepts ("god nodes") are exactly the load-bearing abstractions you
would hope to see: the four-backend Context Forge fan-out, the offside margin, descriptive
geometry, the confidence-calibration receipt, the on-device ASR default, the WCAG 2.2 AA
target, and the assertive `aria-live` verdict region.

The interesting structure is the cross-community bridges, the nodes with the highest
betweenness:

- The **offside margin** and the **GUM uncertainty budget** bridge the geometry cluster
  and the calibration cluster. The honest reading: the number the geometry computes and
  the confidence the fan hears are one coupled story, not two features.
- The **OpenTelemetry span tree** bridges the pipeline cluster and the deployment cluster.
- The proof tree connects to the explain-not-adjudicate cluster, and RAG connects to the
  safety-guardrail cluster, which is the grounding-to-safety spine.

The 18 communities map cleanly onto the project's five pillars (grounding, uncertainty,
accessibility, all-IBM stack, provability), which is the structure the
[main README](../../README.md#knowledge-map) renders as a Mermaid map.
