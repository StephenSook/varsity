# On-device WebGPU: Granite Nano + Kokoro

VARSITY's offline mode runs entirely in the browser with no network: **IBM Granite 4.0
Nano (350M)** phrases the explanation via Transformers.js, and **Kokoro-82M** can read it
aloud, both on **WebGPU** when the browser supports it.

## How it is wired

- `apps/web/src/offline.ts` creates the Granite Nano pipeline with `{ device: 'webgpu', dtype: 'q4' }`.
- `apps/web/src/tts.ts` creates Kokoro with `{ device: 'webgpu', dtype: 'fp32' }`.
- Transformers.js exposes **no** API that reports whether it actually used the GPU, so we
  verify the adapter ourselves: `webgpuReady()` confirms `navigator.gpu.requestAdapter()`
  returns a real adapter before starting a (large) model download, and the model call is
  wrapped in try/catch. If WebGPU or the adapter is missing, offline mode falls back to a
  deterministic, Law-grounded floor and records the provenance
  (`granite-nano-webgpu` vs `deterministic`).

## Verification status (honest)

| Claim | How it is verified |
|---|---|
| Offline mode degrades gracefully without WebGPU | **Automated** (`tests/e2e/webgpu.spec.ts`, runs in CI): offline mode produces an on-device explanation with a recorded provenance, no backend. |
| The WebGPU detection is adapter-aware | **Unit-level** (`webgpuReady()` checks `requestAdapter()`), plus the capability probe in the spec. |
| Granite Nano / Kokoro actually run **on WebGPU** | **Manual**, in Chrome/Edge 113+ (`scripts/verify-webgpu.mjs`). See below. |

### Why WebGPU is not in CI

WebGPU is **not exposed in Playwright-driven browsers** in our testing: `navigator.gpu`
is missing in Playwright's bundled Chromium *and* in real Chrome launched via
`channel: 'chrome'`, headed or headless, with `--enable-unsafe-webgpu`
`--enable-features=Vulkan,WebGPU`. So we do not claim an automated WebGPU run we cannot
observe. The capability probe in the spec **skips** (it does not fake-pass) when no adapter
is present, which is the case in CI.

## Manual verification (real WebGPU)

Run the app, then drive it with a real WebGPU browser:

```bash
cd apps/web
npm run build && npm run preview -- --port 4173 &
# HEADLESS=0 launches a visible Chromium with WebGPU (Metal on macOS):
HEADLESS=0 node scripts/verify-webgpu.mjs http://localhost:4173
```

It prints `WEBGPU_ADAPTER {...}` (the adapter, if any) and `OFFLINE_RESULT {...}` (whether
the app recorded `granite-nano-webgpu`). Or simply open `http://localhost:4173` in Chrome
113+, click **Offline mode**, and confirm the provenance line reads
"Explained on-device by Granite Nano (WebGPU), no network."
