import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const __dirname = dirname(fileURLToPath(import.meta.url))

// Vitest config for the dashboard package. Mirrors the viewer's setup
// (jsdom, globals, jest-dom matchers, ResizeObserver polyfill) so tests
// for both components and lib utilities can render React in jsdom.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      // @/* path alias must mirror dashboard/tsconfig.json
      '@': resolve(__dirname, '.'),
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./__tests__/setup.ts'],
    include: ['__tests__/**/*.test.{ts,tsx}'],
  },
})
