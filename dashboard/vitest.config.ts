import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const __dirname = dirname(fileURLToPath(import.meta.url))

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': resolve(__dirname, '.'),
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./__tests__/setup.ts'],
    include: [
      '__tests__/**/*.test.{ts,tsx}',
      'lib/**/*.test.{ts,tsx}',
      'app/**/*.test.{ts,tsx}',
      'components/**/*.test.{ts,tsx}',
    ],
  },
})
