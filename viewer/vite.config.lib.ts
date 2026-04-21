import { resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import dts from 'vite-plugin-dts'

const __dirname = fileURLToPath(new URL('.', import.meta.url))

export default defineConfig({
  plugins: [
    react(),
    dts({
      include: ['src'],
      exclude: ['src/__tests__', 'src/main.tsx', 'src/sample-data.ts'],
      outDir: 'dist/lib',
      tsconfigPath: './tsconfig.lib.json',
    }),
  ],
  build: {
    lib: {
      entry: resolve(__dirname, 'src/index.ts'),
      formats: ['es'],
      fileName: 'index',
    },
    outDir: 'dist/lib',
    emptyOutDir: true,
    copyPublicDir: false,
    rollupOptions: {
      external: [
        'react',
        'react-dom',
        'react/jsx-runtime',
        '@xyflow/react',
        'zustand',
        'zustand/vanilla',
        'dagre',
        'elkjs',
        'lucide-react',
        'aws-react-icons',
      ],
      output: {
        banner: (chunk) => (chunk.isEntry ? `'use client'\n` : ''),
        assetFileNames: '[name][extname]',
      },
    },
  },
})
