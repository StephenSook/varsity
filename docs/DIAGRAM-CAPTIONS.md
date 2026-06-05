# Diagram captioning: making the IFAB figures accessible (Granite Vision)

The IFAB Laws of the Game PDF carries **diagrams** that prose cannot replace: the offside-position
figure in Law 11, the referee-signal graphics in Laws 5 and 6. Plain Docling ingestion drops them,
leaving `<!-- image -->` holes in the corpus, so a blind fan gets the Law text but never the figure's
content. This pipeline captions those figures with **IBM Granite Vision 3.2** (`ibm/granite-vision-3-2-2b`,
a vision-language model built for document and diagram understanding, on watsonx.ai) into accessible
alt-text, at build time.

## How it stays honest (a vision caption is model-generated)

A generated caption could be wrong, which on a rule corpus would be fabrication. It is fenced three ways:

1. **Grounded.** `services/app/llm/vision.py:caption_prompt` passes the figure's own page text and instructs the
   model to describe only what the figure literally shows, adding no rule or verdict the text omits.
2. **Guarded.** `faithfulness_ok` is a deterministic gate: it rejects a caption that asserts a verdict or
   opinion, or that shares no real vocabulary with the Law text (a sign of drift or hallucination).
   `caption_image` returns an empty string on failure, so an unfaithful caption never leaves the pipeline.
3. **Gated.** `services/scripts/caption_diagrams.py` writes a **draft** (`diagram_captions.draft.json`)
   that a human reviews and promotes to `diagram_captions.approved.json`. The runtime loader
   (`services/app/rag/diagram_captions.py`) reads only the approved file, and the captions are tiered
   **"diagram description (AI-generated, build-time, human-reviewed)"**, never official IFAB text. They
   live separately from the SHA-256-signed corpus, so the signature is never polluted by generated text.

## What is built vs what is gated

- **Built and tested now:** the watsonx image-chat envelope (`vision_messages`, the verified
  `/ml/v1/text/chat` shape), the faithfulness guard, the chunk tiering, the gated extractor
  (`caption_diagrams.py`, the IFAB PDFs are committed under `services/data/`), the runtime loader, and
  the `GET /diagram_captions` endpoint. Pure-function tests in `services/tests/test_vision.py`.
- **Human-review gate (named, not held back):** running the pipeline to populate the **approved**
  corpus needs PyMuPDF + live watsonx credentials and a human to confirm each caption faithfully
  describes its figure (to guarantee no fabrication). Until then `GET /diagram_captions` returns an
  empty set, so the demo is unaffected and nothing unverified ships.

The model id is configurable (`GRANITE_VISION_MODEL_ID`); confirm it against the watsonx catalogue for
the target instance (the default may need pinning, e.g. to `granite-vision-4.1-4b`).

## In concept

This deepens the screen-reader-native, IFAB-grounded thesis: a blind fan asking about offside can get
the described content of the offside diagram, not just the prose. It describes a received rule's figure;
it never adjudicates or predicts.
