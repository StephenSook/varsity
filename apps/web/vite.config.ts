import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        // Split the React runtime into its own long-lived chunk. App code changes far more
        // often than React/scheduler, so isolating them lets a returning visitor reuse the
        // cached vendor chunk across deploys. Everything else (incl. the lazy-loaded ONNX /
        // kokoro chunks behind dynamic import) keeps Rollup's default code-splitting.
        manualChunks(id) {
          if (/[\\/]node_modules[\\/](react|react-dom|scheduler)[\\/]/.test(id)) {
            return 'react-vendor'
          }
        },
      },
    },
  },
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.svg', 'apple-touch-icon.png'],
      manifest: {
        name: 'VARSITY',
        short_name: 'VARSITY',
        description: 'Hear the why behind every VAR call.',
        theme_color: '#0a0f1c',
        background_color: '#0a0f1c',
        display: 'standalone',
        icons: [
          { src: '/apple-touch-icon.png', sizes: '180x180', type: 'image/png' },
          { src: '/favicon.svg', sizes: 'any', type: 'image/svg+xml', purpose: 'any maskable' },
        ],
      },
      workbox: {
        // Precache the shell + the static IFAB index; the heavy chunks (kokoro 2.2MB,
        // the 21MB ONNX wasm) are cached at runtime instead, so the install stays lean.
        globPatterns: ['**/*.{js,css,html,svg,json,png,ico,webmanifest}'],
        globIgnores: ['**/kokoro-*.js'],
        maximumFileSizeToCacheInBytes: 2 * 1024 * 1024,
        runtimeCaching: [
          {
            // Same-origin heavy assets too big to precache (kokoro chunk, ONNX wasm).
            urlPattern: ({ url, sameOrigin }) =>
              sameOrigin && /\/assets\/.*\.(js|wasm)$/.test(url.pathname),
            handler: 'CacheFirst',
            options: {
              cacheName: 'varsity-heavy-assets',
              expiration: { maxEntries: 64 },
              cacheableResponse: { statuses: [0, 200] },
            },
          },
          {
            // Cross-origin Hugging Face model weights (Granite Nano + Kokoro ONNX shards).
            urlPattern: ({ url }) =>
              /(^|\.)huggingface\.co$|(^|\.)hf\.co$|cdn-lfs/.test(url.hostname),
            handler: 'CacheFirst',
            options: {
              cacheName: 'hf-model-weights',
              expiration: { maxEntries: 128 },
              cacheableResponse: { statuses: [0, 200] },
            },
          },
        ],
      },
    }),
  ],
})
