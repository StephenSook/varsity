import type { CapacitorConfig } from '@capacitor/cli'

// VARSITY ships as a web-first installable PWA; this Capacitor config wraps the exact same built
// web app (`dist`) into a native Android shell so it can also be sideloaded as a real .apk. The
// shell adds no new capability over the PWA (WebGPU, service worker, and aria-live all come from
// the system WebView); it is purely a native distribution of the identical frozen front end.
const config: CapacitorConfig = {
  appId: 'dev.stephensook.varsity',
  appName: 'VARSITY',
  webDir: 'dist',
}

export default config
