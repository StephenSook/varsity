import { defineConfig } from 'vitest/config'

// A standalone vitest config (not the Vite app config) so the unit tests run in a plain Node
// environment without loading the PWA / React / Tailwind plugins. The sonification parameter
// functions are pure, so no DOM or Web Audio is needed.
export default defineConfig({
  test: {
    environment: 'node',
    include: ['src/**/*.test.ts'],
  },
})
