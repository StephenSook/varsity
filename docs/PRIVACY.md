# Privacy

VARSITY's privacy posture is mostly *what it does not build*. An accessibility tool handles a
vulnerable user group, so the safest design collects nothing it does not strictly need.

## What we do NOT collect

1. **We never ask whether you are blind, low-vision, or have any disability.** Disability status is
   special-category data under GDPR Article 9; the safest treatment is to never collect, derive, or
   store it. Your screen reader's presence is a fact known only to your own device.
2. **No third-party analytics.** No Google Analytics, no Mixpanel, no Sentry, no PostHog, no Segment.
   (Verifiable: there is no analytics SDK in `apps/web/`.)
3. **No cookies.** (Verifiable: there is no `document.cookie` use in the codebase.)
4. **No advertising, no fingerprinting, no telemetry of screen-reader use or navigation.**

## What stays on your device

- **Your preferences** (language, sound on/off, verbosity) live in `localStorage` and are never
  transmitted.
- **Offline mode** runs IBM Granite Nano entirely in your browser via WebGPU
  (`apps/web/src/offline.ts`). When you use it, your interaction is processed locally and the
  explanation never leaves the device.

## What leaves your browser, and only this

- To the VARSITY backend: the public match/scenario you selected (or your free-text Laws question)
  and your language preference. These are not personal data.
- To Hugging Face, once: the on-device Granite Nano model file is downloaded the first time you
  enable offline mode, then cached locally. This is a model download, not a data upload.

## Operational secrets (not user data)

The Sportmonks / watsonx / API-Football keys live only in server environment variables and are never
sent to the browser; the frontend talks to our backend, which injects them server-side. They are
rotated and never committed (`.env` is gitignored; `.env.example` ships placeholders).

## What we deliberately did not add

Differential privacy and federated learning are **out of scope**: VARSITY has no user-data training
pipeline, so there is nothing for them to protect. Adding them would be theatre, not privacy.
