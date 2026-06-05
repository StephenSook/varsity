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

| File | What it is | How to view |
|---|---|---|
| `graph.svg` | Static force-directed map of all 199 concepts, coloured by community | Renders inline on GitHub; open the file |
| `graph.html` | Interactive force-directed graph (drag, zoom, hover, search) | Download and open in any browser, no server needed |
| `GRAPH_REPORT.md` | Plain-language audit: god nodes, surprising connections, suggested questions, per-community cohesion | Renders on GitHub |
| `graph.json` | Raw graph (nodes + edges + communities) for GraphRAG / Neo4j / Gephi | Machine-readable |

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
