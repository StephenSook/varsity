# Changelog

All notable changes to VARSITY are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project aims to follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- On-device offline mode now converts the offside margin with the international yard
  (0.9144), matching the online geometry, `sonify.ts`, and `geometry.py`. Airplane mode
  previously used a stale 0.875 factor and spoke a margin about 4 percent too small; the
  canned offline frame now speaks 5.69 m, the same value as the online path.

### Added
- An inline Gource build time-lapse in the README (an animated preview that links to the
  full render attached to the v1.0.0 release).
- An end-to-end contract test for the `/stream/live` route, and watsonx degrade-to-floor
  tests for the penalty and free-text-oracle paths.

### Changed
- The A2A narrator's canned-payload substitution and the unknown-decision-type fallback now
  log a warning, so neither is silent.

### Security
- Bumped `vitest` to v4, which clears a development-only advisory (the Vitest UI server,
  which this project never runs). The shipped bundle and the backend runtime tree have no
  known vulnerabilities, and no secret has ever been committed (verified with gitleaks over
  the full history).

## [1.0.0] - 2026-06-05

First public release: the deployed, CI-gated build entered for the IBM SkillsBuild AI
Builders Challenge (June 2026). Live at https://web-chi-wine-13.vercel.app (frontend) and
https://varsity-api.onrender.com (backend).

### Added
- **Grounded explanation pipeline.** A VAR review triggers real StatsBomb 360 offside
  geometry (margin computed, not hardcoded), exact IFAB Law retrieval (Docling to FAISS,
  Granite embeddings, Hit@5 = 1.00), an IBM Granite explanation, and a Granite Guardian
  groundedness check, delivered over SSE to a screen reader. It explains a received decision
  and never adjudicates.
- **Honest uncertainty.** A calibrated confidence band (ECE 0.34 percent against a 4.16
  percent overconfident control), an IPCC-style verbal scale, and a too-close call that
  withholds the number and defers to the official.
- **Audio-first accessibility.** Screen-reader-native `aria-live`, listener-centred HRTF
  spatial earcons, five-language narration (EN, ES, FR, PT, DE), WCAG 2.2 AA enforced in CI,
  and a full keyboard mode.
- **All-IBM stack.** Granite reasoning, Granite Guardian, Granite embeddings, Granite Vision,
  and Docling, federated through Context Forge with an A2A narrator, plus a fully on-device
  offline mode running Granite Nano in the browser.
- **Provable and resilient.** Every claim is a live button on the `/judges` page, the IFAB
  corpus is SHA-256-signed and fails closed, the free-text oracle survives a 13/13 red-team,
  and a watsonx outage degrades to a Law-citing floor instead of crashing.
- **A real live feed.** `GET /live/now` returns the matches in play right now via
  API-Football, honest about its state when no key is configured.
- A project knowledge map (a README Mermaid graph, a 199-concept auto-extracted graph, and a
  cinematic 3D architecture view) under `docs/knowledge-graph/`.

[Unreleased]: https://github.com/StephenSook/varsity/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/StephenSook/varsity/releases/tag/v1.0.0
