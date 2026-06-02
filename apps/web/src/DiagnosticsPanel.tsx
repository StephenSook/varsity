import { useEffect, useState } from 'react'

// On-device pre-flight diagnostics: turns the "it runs entirely on your device" claim
// into something a judge can read on camera. Reports the service worker, the WebGPU
// adapter, what is cached, persistent-storage grant, and the storage estimate. Semantic
// + screen-reader friendly (a real <dl>), and offered behind a toggle so it never
// clutters the core demo.

type Diag = {
  serviceWorker: string
  webgpu: string
  caches: string
  persisted: string
  storage: string
  network: string
}

const mb = (n?: number): string => (n ? `${(n / 1048576).toFixed(0)} MB` : '?')

async function collect(): Promise<Diag> {
  const nav = navigator as Navigator & {
    gpu?: { requestAdapter?: () => Promise<{ info?: { vendor?: string; architecture?: string } } | null> }
    storage?: { persisted?: () => Promise<boolean>; estimate?: () => Promise<StorageEstimate> }
  }

  const serviceWorker =
    'serviceWorker' in navigator && navigator.serviceWorker.controller
      ? 'active, controlling this page'
      : 'serviceWorker' in navigator
        ? 'registered'
        : 'unsupported'

  let webgpu = 'unavailable (deterministic fallback)'
  if (nav.gpu?.requestAdapter) {
    try {
      const a = await nav.gpu.requestAdapter()
      if (a) webgpu = `adapter ready ${a.info?.vendor ?? ''} ${a.info?.architecture ?? ''}`.trim()
    } catch {
      /* keep unavailable */
    }
  }

  let caches_ = 'none'
  if ('caches' in window) {
    const keys = await caches.keys()
    caches_ = keys.length ? keys.map((k) => k.replace(/-http.*$/, '')).join(', ') : 'none'
  }

  let persisted = 'unknown'
  if (nav.storage?.persisted) persisted = (await nav.storage.persisted()) ? 'granted' : 'not granted'

  let storage = 'unknown'
  if (nav.storage?.estimate) {
    const e = await nav.storage.estimate()
    storage = `${mb(e.usage)} used of ${mb(e.quota)} available`
  }

  return {
    serviceWorker,
    webgpu,
    caches: caches_,
    persisted,
    storage,
    network: navigator.onLine ? 'online' : 'offline',
  }
}

export function DiagnosticsPanel() {
  const [diag, setDiag] = useState<Diag | null>(null)
  const [busy, setBusy] = useState(false)
  const refresh = () => void collect().then(setDiag)
  useEffect(refresh, [])

  async function requestPersist() {
    const nav = navigator as Navigator & { storage?: { persist?: () => Promise<boolean> } }
    if (!nav.storage?.persist) return
    setBusy(true)
    await nav.storage.persist().catch(() => {})
    setBusy(false)
    refresh()
  }

  if (!diag) return null
  const rows: [string, string][] = [
    ['Service worker', diag.serviceWorker],
    ['WebGPU', diag.webgpu],
    ['Cached on device', diag.caches],
    ['Persistent storage', diag.persisted],
    ['Storage used', diag.storage],
    ['Network', diag.network],
  ]

  return (
    <section
      aria-label="On-device diagnostics"
      className="w-full max-w-md rounded-xl bg-slate-900/70 p-4 text-left ring-1 ring-slate-700/50"
    >
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-emerald-300">On-device diagnostics</h3>
        <button
          type="button"
          onClick={refresh}
          className="text-xs text-slate-400 underline-offset-2 hover:text-emerald-300 hover:underline"
        >
          Refresh
        </button>
      </div>
      <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
        {rows.map(([k, v]) => (
          <div key={k} className="contents">
            <dt className="text-slate-400">{k}</dt>
            <dd data-testid={`diag-${k.split(' ')[0].toLowerCase()}`} className="text-slate-200">
              {v}
            </dd>
          </div>
        ))}
      </dl>
      {diag.persisted !== 'granted' && (
        <button
          type="button"
          onClick={() => void requestPersist()}
          disabled={busy}
          className="mt-3 rounded-full border border-emerald-500/60 px-4 py-1.5 text-xs font-medium text-emerald-300 hover:bg-emerald-500/10 disabled:opacity-50"
        >
          {busy ? 'Requesting...' : 'Make on-device weights eviction-exempt'}
        </button>
      )}
    </section>
  )
}
