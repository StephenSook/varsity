import { useEffect, useState } from 'react'

// A small online/offline indicator, announced politely on change. Makes the
// "airplane mode" reveal legible: the badge flips to Offline the moment the network
// is cut, while the on-device explanation keeps working from the cached model.
export function OnlineBadge() {
  const [online, setOnline] = useState(typeof navigator === 'undefined' ? true : navigator.onLine)
  useEffect(() => {
    const on = () => setOnline(true)
    const off = () => setOnline(false)
    window.addEventListener('online', on)
    window.addEventListener('offline', off)
    return () => {
      window.removeEventListener('online', on)
      window.removeEventListener('offline', off)
    }
  }, [])

  return (
    <div
      role="status"
      aria-live="polite"
      data-testid="online-badge"
      className="fixed right-3 top-3 z-50 flex items-center gap-2 rounded-full bg-slate-900/70 px-3 py-1 text-xs ring-1 ring-slate-700/60 backdrop-blur"
    >
      <span
        aria-hidden="true"
        className={`h-2 w-2 rounded-full ${online ? 'bg-emerald-400' : 'bg-amber-400'}`}
      />
      <span className="text-slate-200">{online ? 'Online' : 'Offline'}</span>
    </div>
  )
}
