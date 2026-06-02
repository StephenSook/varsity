// Honest WebGPU verification: launch Chromium with WebGPU enabled and report what
// is ACTUALLY available, then (if an adapter exists) drive the app's on-device offline
// mode and confirm whether Granite Nano genuinely ran on WebGPU. Prints a verdict; it
// never claims success it did not observe.
//
// Usage: node scripts/verify-webgpu.mjs [previewUrl]
import { chromium } from '@playwright/test'

const URL = process.argv[2] || 'http://localhost:4173'

const HEADLESS = process.env.HEADLESS !== '0'
const browser = await chromium.launch({
  headless: HEADLESS,
  args: [
    '--enable-unsafe-webgpu',
    '--enable-features=Vulkan',
    HEADLESS ? '--use-angle=swiftshader' : '--use-angle=metal',
    '--ignore-gpu-blocklist',
  ],
})
const page = await browser.newPage()

// 1) Does this browser expose a real WebGPU adapter?
await page.goto('about:blank')
const adapter = await page.evaluate(async () => {
  if (typeof navigator === 'undefined' || !('gpu' in navigator)) return { ok: false, why: 'navigator.gpu missing' }
  try {
    const a = await navigator.gpu.requestAdapter()
    if (!a) return { ok: false, why: 'requestAdapter() returned null' }
    const info = a.info || (a.requestAdapterInfo ? await a.requestAdapterInfo() : {})
    return { ok: true, vendor: info.vendor ?? '?', architecture: info.architecture ?? '?' }
  } catch (e) {
    return { ok: false, why: String(e) }
  }
})
console.log('WEBGPU_ADAPTER', JSON.stringify(adapter))

let offline = { reached: false }
if (adapter.ok) {
  // 2) Drive the real app: offline mode runs Granite Nano on WebGPU. Report the source
  //    the app itself recorded (granite-nano-webgpu vs deterministic fallback).
  try {
    await page.goto(URL, { waitUntil: 'load', timeout: 30_000 })
    await page.getByRole('button', { name: /Offline mode/ }).click()
    const handle = await page.waitForFunction(
      () => {
        const live = document.querySelector('[aria-live="assertive"]')?.textContent?.trim() || ''
        const src = document.querySelector('[data-testid="offline-source"]')?.textContent?.trim() || ''
        return live.length > 20 ? { live, src } : null
      },
      { timeout: 180_000 },
    )
    const res = await handle.jsonValue()
    // Read the recorded provenance flag the app sets on window for verification.
    const source = await page.evaluate(() => document.querySelector('[data-testid="offline-source"]')?.textContent || '')
    offline = { reached: true, source, sample: res.live.slice(0, 80) }
  } catch (e) {
    offline = { reached: true, error: String(e).slice(0, 160) }
  }
}
console.log('OFFLINE_RESULT', JSON.stringify(offline))

await browser.close()
