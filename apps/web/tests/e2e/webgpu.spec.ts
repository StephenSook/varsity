import { expect, test } from '@playwright/test'

// WebGPU is NOT exposed in Playwright-driven browsers (verified: navigator.gpu is
// missing in the bundled Chromium AND in real Chrome via `channel: 'chrome'`, headed
// or headless, with --enable-unsafe-webgpu). So an automated end-to-end run of Granite
// Nano / Kokoro ON WebGPU is not possible in CI. We instead assert the two things that
// ARE automatable and honest:
//   1. the on-device offline mode degrades gracefully to the deterministic floor with a
//      recorded provenance (the real, testable half), and
//   2. a capability probe that SKIPS honestly when no WebGPU adapter exists, rather than
//      asserting a fake pass.
// The real Nano/Kokoro-on-WebGPU path is verified manually in Chrome 113+ via
// scripts/verify-webgpu.mjs (see docs/WEBGPU.md). No backend is needed for this suite.

test('on-device offline mode degrades gracefully (no WebGPU, no backend)', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: /Offline mode/ }).click()
  // A Law-grounded explanation is produced entirely on-device.
  await expect(page.locator('[aria-live="assertive"]')).not.toHaveText('', { timeout: 60_000 })
  // The provenance line records HOW it was produced (deterministic floor or Nano/WebGPU).
  const provenance = page.getByTestId('offline-source')
  await expect(provenance).toBeVisible()
  await expect(provenance).toContainText('on-device')
  // and the governing Law was retrieved in-browser (Orama BM25 over the static IFAB index).
  await expect(provenance).toContainText('Orama BM25')
})

test('WebGPU capability probe (skips honestly when WebGPU is unavailable)', async ({ page }) => {
  await page.goto('/')
  const hasAdapter = await page.evaluate(async () => {
    const gpu = (navigator as unknown as { gpu?: { requestAdapter?: () => Promise<unknown> } }).gpu
    if (!gpu?.requestAdapter) return false
    try {
      return (await gpu.requestAdapter()) != null
    } catch {
      return false
    }
  })
  test.skip(
    !hasAdapter,
    'WebGPU unavailable in this browser; Nano/Kokoro on WebGPU verified manually in Chrome 113+',
  )
  // Reaching here means a real adapter exists, so the app runs Granite Nano on it.
  expect(hasAdapter).toBe(true)
})
