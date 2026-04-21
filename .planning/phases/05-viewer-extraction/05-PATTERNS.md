# Phase 5: Viewer Extraction - Pattern Map

**Mapped:** 2026-04-21
**Files analyzed:** 14 (7 new, 7 modified)
**Analogs found:** 13 / 14 (1 partially novel — root `package.json` has no peer)

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `viewer/vite.config.app.ts` | config | transform | `viewer/vite.config.ts` (lines 1–18) | exact — direct split |
| `viewer/vite.config.lib.ts` | config | transform | `viewer/vite.config.ts` (lines 1–18) | role-match — same plugin composition pattern, different build target |
| `viewer/tsconfig.lib.json` | config | transform | `viewer/tsconfig.json` (lines 1–23) | exact — extends base, overrides 3 keys |
| `viewer/src/index.ts` | utility | request-response | `viewer/src/components/DiagramCanvas.tsx` line 27 (named export pattern) | role-match — barrel aggregates named exports |
| `viewer/src/lib-styles.css` | config | transform | `viewer/src/index.css` (lines 1–18) | role-match — same Tailwind v4 entry format, different scope |
| `package.json` (root) | config | — | none in repo | no analog — first JS root in repo |
| `viewer/package.json` | config | — | itself (lines 1–41) | exact — modify in place |
| `viewer/src/main.tsx` | utility | request-response | itself (lines 1–17) | exact — wrap existing render call |
| `viewer/src/App.tsx` | component | event-driven | itself (lines 1–142) | exact — `useStore` call sites unchanged |
| `viewer/src/store.ts` | store | event-driven | itself (lines 1–172) | exact — extend with factory + Context alongside singleton |
| `viewer/src/components/*.tsx` (8 files) | component | event-driven | themselves | exact — no source changes required |
| `viewer/src/components/flowmap/*.tsx` (4 files) | component | event-driven | themselves | exact — no source changes required |
| `.github/workflows/viewer-peer-compat.yml` | CI | batch | `.github/workflows/ci.yml` (lines 1–65) | role-match — same GHA job structure, adds matrix |

---

## Pattern Assignments

### CLUSTER A: Build Configuration Files

---

#### `viewer/vite.config.app.ts` (config, transform)

**Analog:** `viewer/vite.config.ts`

**Role:** App (single-file HTML) build config — splits off from the existing file. This IS the existing file with minor additions (`outDir` explicit, test block preserved).

**Full analog** (`viewer/vite.config.ts`, lines 1–18):
```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { viteSingleFile } from 'vite-plugin-singlefile'

export default defineConfig({
  plugins: [react(), tailwindcss(), viteSingleFile()],
  build: {
    target: 'esnext',
    assetsInlineLimit: 100000000,
    cssCodeSplit: false,
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/__tests__/setup.ts'],
  },
})
```

**Key differences for `vite.config.app.ts`:**
- Add explicit `build.outDir: 'dist'` (already the default, but clarifies intent).
- The `test` block stays here (Vitest reads the config pointed to by `--config`; tests use `vite.config.app.ts`).
- The three plugins (`react()`, `tailwindcss()`, `viteSingleFile()`) are preserved exactly — do NOT remove `tailwindcss()` from the app config.

**Key constraint:** `vite-plugin-singlefile` MUST NOT appear in `vite.config.lib.ts`. These configs exist as two separate files precisely because `vite-plugin-singlefile` sets `assetsInlineLimit` globally and breaks library output.

---

#### `viewer/vite.config.lib.ts` (config, transform)

**Analog:** `viewer/vite.config.ts` — same plugin composition skeleton, new `build.lib` section.

**Plugin composition pattern** (from `viewer/vite.config.ts` lines 1–4):
```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
// NOTE: @tailwindcss/vite is intentionally OMITTED here
// CSS for the library is built by @tailwindcss/cli as a separate step
```

**Core lib build pattern** (new — no direct analog in repo; derived from RESEARCH.md Pattern 1):
```typescript
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
        banner: (chunk) => {
          if (chunk.isEntry) return `'use client'\n`
          return ''
        },
        assetFileNames: '[name][extname]',
      },
    },
  },
})
```

**Key differences from the app config:**
- `viteSingleFile()` and `tailwindcss()` are absent.
- `build.lib` section is added — no analog in the codebase today.
- `rollupOptions.external` externalizes React and all peer deps from `viewer/package.json` `dependencies`.
- `output.banner` emits `'use client'` on entry chunk only (bypasses Rollup optimizer stripping).
- No `test` block — tests run via `vite.config.app.ts`.

---

#### `viewer/tsconfig.lib.json` (config, transform)

**Analog:** `viewer/tsconfig.json` (lines 1–23) — extends the base, overrides three keys.

**Full analog** (`viewer/tsconfig.json`, lines 1–23):
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2021", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedSideEffectImports": true
  },
  "include": ["src"],
  "exclude": ["src/__tests__"]
}
```

**Key differences for `tsconfig.lib.json`:**
- `extends: "./tsconfig.json"` (inherit all base options).
- Override `allowImportingTsExtensions: false` — required so `tsc` can emit `.d.ts` files.
- Override `noEmit: false` — required to allow declaration output (the base sets `noEmit: true` because `allowImportingTsExtensions: true` otherwise requires it).
- Add `declaration: true`, `declarationDir: "dist/lib"`, `emitDeclarationOnly: true`.
- Tighten `include` to `["src"]` and `exclude` to `["src/__tests__", "src/main.tsx", "src/sample-data.ts"]`.

**Critical constraint:** The base `tsconfig.json` sets `"allowImportingTsExtensions": true` AND `"noEmit": true`. These two options are coupled — TypeScript enforces that `allowImportingTsExtensions` is only valid when not emitting. The lib tsconfig MUST flip both simultaneously.

---

### CLUSTER B: New Source Files

---

#### `viewer/src/index.ts` (utility/barrel, request-response)

**Analog:** Named export pattern from `viewer/src/components/DiagramCanvas.tsx` line 27:
```typescript
export function DiagramCanvas() {
```
...and `viewer/src/components/FilterPanel.tsx` line 9:
```typescript
export function FilterPanel() {
```

All 13 exported components use the `export function ComponentName()` pattern — not default exports. The barrel `index.ts` re-exports these named exports.

**Full list of component exports to confirm** (verify each file exists at these paths before coding):
- `viewer/src/components/DiagramCanvas.tsx` — exports `DiagramCanvas`
- `viewer/src/components/FilterPanel.tsx` — exports `FilterPanel`
- `viewer/src/components/DetailPanel.tsx` — exports `DetailPanel`
- `viewer/src/components/SummaryBar.tsx` — exports `SummaryBar`
- `viewer/src/components/TabBar.tsx` — exports `TabBar`
- `viewer/src/components/SearchBar.tsx` — exports `SearchBar`
- `viewer/src/components/FindingCard.tsx` — exports `FindingCard`
- `viewer/src/components/GroupNode.tsx` — exports `GroupNode`
- `viewer/src/components/ResourceNode.tsx` — exports `ResourceNode` (component) AND the file is the clash point with the `ResourceNode` type in `types.ts`
- `viewer/src/components/flowmap/FlowMapCanvas.tsx` — exports `FlowMapCanvas`
- `viewer/src/components/flowmap/FlowMapFilterPanel.tsx` — exports `FlowMapFilterPanel`
- `viewer/src/components/flowmap/PathDetailPanel.tsx` — exports `PathDetailPanel`
- `viewer/src/components/flowmap/FlowMapEmptyState.tsx` — exports `FlowMapEmptyState`

**Import pattern** (from `viewer/src/App.tsx`, lines 3–8):
```typescript
import { useStore } from './store';
import { SummaryBar } from './components/SummaryBar';
import { TabBar } from './components/TabBar';
import { FilterPanel } from './components/FilterPanel';
import { DiagramCanvas } from './components/DiagramCanvas';
import { DetailPanel } from './components/DetailPanel';
```

**Barrel re-export pattern to copy:**
```typescript
// named component re-export (mirrors App.tsx import style)
export { DiagramCanvas } from './components/DiagramCanvas'
export { FilterPanel } from './components/FilterPanel'
// ... all 13 components

// type re-export (D-05 — all types from types.ts)
export type { ResourceGraph, Finding, ... } from './types'

// ResourceNode naming collision resolution:
// The component is exported aliased; the type keeps the original name.
export { ResourceNode as ResourceNodeComponent } from './components/ResourceNode'
export type { ResourceNode } from './types'

// Store factory (for dashboard mounting — D-11)
export { createViewerStore, ViewerProvider, useViewerStore } from './store'
```

**Note on `FlowMapEmptyState`:** Only 4 flowmap component files exist in the glob results (`FlowMapEmptyState`, `FlowMapFilterPanel`, `PathDetailPanel`, `FlowMapCanvas`). CONTEXT.md lists 5 flowmap files. Verify the 5th (possibly a nodes subdirectory component) before finalizing index.ts.

---

#### `viewer/src/lib-styles.css` (config, transform)

**Analog:** `viewer/src/index.css` (lines 1–18) — same Tailwind v4 entry format.

**Full analog** (`viewer/src/index.css`, lines 1–18):
```css
@import "tailwindcss";

@theme {
  --color-canvas-bg: #FAFBFC;
  --color-card-bg: #FFFFFF;
  --color-card-border: #E2E8F0;
  --color-card-hover: #F1F5F9;
  --color-sev-critical: #ef4444;
  --color-sev-high: #f97316;
  --color-sev-medium: #eab308;
  --color-sev-info: #3b82f6;
  --color-sev-clean: #22c55e;
  --color-flow-forward: #3B82F6;
  --color-flow-return:  #F97316;
  --color-flow-divergence: #EF4444;
  --font-mono: 'JetBrains Mono', ui-monospace, monospace;
  --font-sans: 'Inter', ui-sans-serif, system-ui, sans-serif;
}
```

**Key differences for `lib-styles.css`:**
- Replace `@import "tailwindcss"` with `@import "tailwindcss" source(none)` — this disables automatic project-wide scanning.
- Add explicit `@source` directives pointing only to component directories (not `main.tsx`, `sample-data.ts`, or `__tests__`).
- Keep the full `@theme` block from `index.css` — the color tokens are the same fixed palette (D-09 — no theming changes in Phase 5).
- Do NOT include font-face rules or `html, body, #root` resets — those are CLI-HTML-only concerns (consumers use their own base styles).

**`@source` directives pattern** (derived from RESEARCH.md Pattern 5):
```css
@import "tailwindcss" source(none);

@theme {
  /* copy entire @theme block from viewer/src/index.css lines 3-18 */
}

@source "./components";
@source "./components/flowmap";
@source "./App.tsx";
```

---

### CLUSTER C: Modified Source Files

---

#### `viewer/package.json` (config, modified in place)

**Analog:** itself — lines 1–41.

**Current state** (lines 1–41 — full file, read above):
- `name: "infracanvas-viewer"`, `private: true`, `type: "module"`
- `scripts`: `dev`, `build`, `postbuild`, `preview`, `test`, `test:watch`
- `dependencies`: react 18, react-dom 18, @xyflow/react, aws-react-icons, dagre, elkjs, lucide-react, zustand
- `devDependencies`: @tailwindcss/vite, @testing-library/*, @types/*, @vitejs/plugin-react, jsdom, tailwindcss, typescript, vite, vite-plugin-singlefile, vitest

**Changes required:**

`name` field:
```json
"name": "@infracanvas/viewer"
```

`scripts` section — replace `build` and `dev`/`preview`, preserve `postbuild`, `test`, `test:watch`:
```json
"scripts": {
  "build": "tsc -b && npm run build:app && npm run build:lib && npm run build:css",
  "build:app": "vite build --config vite.config.app.ts",
  "build:lib": "vite build --config vite.config.lib.ts",
  "build:css": "npx @tailwindcss/cli -m -i src/lib-styles.css -o dist/lib/styles.css",
  "postbuild": "cp dist/index.html ../cli/infracanvas/export/viewer_template.html",
  "dev": "vite --config vite.config.app.ts",
  "preview": "vite preview --config vite.config.app.ts",
  "test": "vitest run",
  "test:watch": "vitest"
}
```

Add `peerDependencies` (new key, does not exist today):
```json
"peerDependencies": {
  "react": "^18.0.0 || ^19.0.0",
  "react-dom": "^18.0.0 || ^19.0.0"
}
```

Add `exports` map (new key):
```json
"exports": {
  ".": {
    "types": "./dist/lib/index.d.ts",
    "import": "./dist/lib/index.js"
  },
  "./styles.css": "./dist/lib/styles.css"
},
"main": "./dist/lib/index.js",
"module": "./dist/lib/index.js",
"types": "./dist/lib/index.d.ts",
"files": ["dist/lib"],
"sideEffects": ["**/*.css"]
```

Add new `devDependencies` (two packages not currently installed):
```json
"vite-plugin-dts": "^4.5.4",
"@tailwindcss/cli": "^4.1.4"
```

**Preservation rule:** `react` and `react-dom` stay in `dependencies` (needed by CLI HTML build which runs in the same package). They are ALSO listed in `peerDependencies` — both coexist. `aws-react-icons`, `dagre`, `elkjs`, `lucide-react` stay in `dependencies` (bundled in CLI HTML; externalized in lib build via rollupOptions.external).

---

#### `viewer/src/main.tsx` (utility, request-response, modified)

**Analog:** itself (lines 1–17 — full file, read above).

**Current state** (full file):
```typescript
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import '@fontsource/inter/400.css';
// ... 5 more font imports
import App from './App';
import './index.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
```

**Change:** Add `ViewerProvider` import and wrap `<App/>`:
```typescript
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '@fontsource/inter/400.css'
import '@fontsource/inter/500.css'
import '@fontsource/inter/600.css'
import '@fontsource/inter/700.css'
import '@fontsource/jetbrains-mono/400.css'
import '@fontsource/jetbrains-mono/500.css'
import '@fontsource/jetbrains-mono/600.css'
import { ViewerProvider } from './store'   // NEW
import App from './App'
import './index.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ViewerProvider>            {/* NEW — creates default store instance */}
      <App />
    </ViewerProvider>
  </StrictMode>,
)
```

**Note:** Semicolons are used in the current file (`import ... ;`). The project CLAUDE.md convention states "no semicolons" but the existing file uses them. Follow the existing file's style exactly.

---

#### `viewer/src/store.ts` (store, event-driven, modified)

**Analog:** itself (lines 1–172 — full file, read above).

**Current singleton pattern** (lines 1 and 75):
```typescript
import { create } from 'zustand';
// ...
export const useStore = create<StoreState>((set) => ({
  // full state creator — 97 lines
}));
```

**Change:** Coexistence approach — keep singleton, add factory + Context alongside.

**Additions to make after the existing `useStore` export (after line 172):**

```typescript
// === NEW: factory + Context for dashboard consumption (D-11) ===
import { createStore } from 'zustand/vanilla'
import { useStore as useZustandStore } from 'zustand'
import { createContext, useContext, useState, type ReactNode } from 'react'

// Factory: each call produces an independent store instance
export function createViewerStore() {
  return createStore<StoreState>((set) => ({
    // identical state creator as the existing useStore above
    // copy the exact (set) => ({ ... }) body from lines 76-172
  }))
}

export type ViewerStoreApi = ReturnType<typeof createViewerStore>

export const ViewerStoreContext = createContext<ViewerStoreApi | undefined>(undefined)

export function ViewerProvider({
  store,
  children,
}: {
  store?: ViewerStoreApi
  children: ReactNode
}) {
  const [defaultStore] = useState(() => createViewerStore())
  return (
    <ViewerStoreContext.Provider value={store ?? defaultStore}>
      {children}
    </ViewerStoreContext.Provider>
  )
}

// Drop-in for components that migrate to Context-based store access
export function useViewerStore<T>(selector: (state: StoreState) => T): T {
  const store = useContext(ViewerStoreContext)
  if (!store) throw new Error('useViewerStore must be used within ViewerProvider')
  return useZustandStore(store, selector)
}
```

**Constraint:** The existing `export const useStore = create<StoreState>(...)` on line 75 MUST remain. Tests and all existing component call sites (`useStore(s => s.foo)` in `App.tsx`, `DiagramCanvas.tsx`, `FilterPanel.tsx`, etc.) continue using it. Zero test changes required.

**Import additions at top of file:**
```typescript
import { createStore } from 'zustand/vanilla'
import { useStore as useZustandStore } from 'zustand'
import { createContext, useContext, useState, type ReactNode } from 'react'
```

**State creator extraction:** To avoid duplicating 97 lines of state in the factory, extract the state creator to a named const before the `useStore` line:
```typescript
// Extract state creator so both singleton and factory use the same function
const stateCreator = (set: Parameters<typeof create<StoreState>>[0]) => ({
  // ... move lines 76-172 body here
})

export const useStore = create<StoreState>(stateCreator)

export function createViewerStore() {
  return createStore<StoreState>(stateCreator)
}
```

---

#### `viewer/src/App.tsx` (component, event-driven, unchanged)

**Analog:** itself (lines 1–142).

**Current `useStore` call pattern** (lines 25–30):
```typescript
const setGraph = useStore((s) => s.setGraph);
const setGateMode = useStore((s) => s.setGateMode);
const setHasFlowMap = useStore((s) => s.setHasFlowMap);
const activeTab = useStore((s) => s.activeTab);
const setActiveTab = useStore((s) => s.setActiveTab);
const hasFlowMap = useStore((s) => s.hasFlowMap);
```

**No changes required.** The module-level `useStore` singleton continues to work identically. Phase 4 tab wiring logic (hash sync lines 44–65, keyboard shortcuts lines 68–106) is preserved byte-for-byte.

---

#### `viewer/src/components/*.tsx` and `viewer/src/components/flowmap/*.tsx` (components, event-driven, unchanged)

**Analog pattern** — `DiagramCanvas.tsx` line 19:
```typescript
import { useStore } from '../store';
```

`FilterPanel.tsx` line 2:
```typescript
import { useStore } from '../store';
```

`FlowMapCanvas.tsx` (first 20 lines show same `@xyflow/react` + `useStore` import pattern as `DiagramCanvas.tsx`).

**No changes required to any component file.** All components import `useStore` from `'../store'` (or `'../../store'` for flowmap components). The singleton `useStore` remains exported and call sites resolve identically.

---

### CLUSTER D: CI Workflow File

---

#### `.github/workflows/viewer-peer-compat.yml` (CI, batch)

**Analog:** `.github/workflows/ci.yml` (lines 1–65) — same GHA structure.

**Reusable structural pattern** (from `ci.yml` lines 30–49, the `test-viewer` job):
```yaml
test-viewer:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4

    - uses: actions/setup-node@v4
      with:
        node-version: '20'

    - name: Install dependencies
      run: cd viewer && npm ci

    - name: Type check
      run: cd viewer && npx tsc --noEmit

    - name: Run tests
      run: cd viewer && npm test -- --run

    - name: Build
      run: cd viewer && npm run build
```

**Key differences for `viewer-peer-compat.yml`:**
- Add `on.push.paths: ['viewer/**']` trigger (only runs when viewer changes — not on CLI or CLI-binary changes).
- Add `strategy.matrix: { react-version: ['18', '19'] }` — two parallel jobs.
- Job name: `peer-compat` (not `test-viewer`).
- Node version: `'22'` (LTS as of 2026-04-21; `ci.yml` uses `'20'`).
- Add `Override React version` step after build:
  ```yaml
  - name: Override React version
    working-directory: viewer
    run: |
      npm install \
        react@${{ matrix.react-version }} \
        react-dom@${{ matrix.react-version }} \
        @types/react@${{ matrix.react-version }} \
        @types/react-dom@${{ matrix.react-version }} \
        --legacy-peer-deps
  ```
- Test step runs `npm test` (not `npm test -- --run` as in ci.yml); Vitest run mode is already set in the `test` script.

**Full workflow structure** (derived from ci.yml + RESEARCH.md):
```yaml
name: Viewer Peer Compatibility
on:
  push:
    paths: ['viewer/**']
  pull_request:
    paths: ['viewer/**']

jobs:
  peer-compat:
    strategy:
      matrix:
        react-version: ['18', '19']
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '22'
      - name: Install dependencies
        working-directory: viewer
        run: npm ci
      - name: Build package
        working-directory: viewer
        run: npm run build
      - name: Override React version
        working-directory: viewer
        run: |
          npm install \
            react@${{ matrix.react-version }} \
            react-dom@${{ matrix.react-version }} \
            @types/react@${{ matrix.react-version }} \
            @types/react-dom@${{ matrix.react-version }} \
            --legacy-peer-deps
      - name: Run test suite
        working-directory: viewer
        run: npm test
```

---

### CLUSTER E: Root `package.json` (new)

#### `package.json` (root) (config, no analog)

**No existing analog in the repo.** The repo currently has no root `package.json` (confirmed by filesystem check — the file does not exist).

**Pattern source:** npm workspaces documentation + RESEARCH.md Pattern 6.

**Target file:**
```json
{
  "name": "infracanvas-monorepo",
  "private": true,
  "workspaces": ["viewer"]
}
```

**Key constraints:**
- `"private": true` — prevents accidental publish of the monorepo root.
- `"workspaces": ["viewer"]` — only the `viewer/` JS package is a workspace member. `cli/` (Python) is NOT added.
- Phase 7 extends this to `["viewer", "dashboard"]` when the Next.js dashboard is created.

---

## Shared Patterns

### Named Export Convention
**Source:** `viewer/src/components/DiagramCanvas.tsx` line 27, `FilterPanel.tsx` line 9
**Apply to:** `viewer/src/index.ts` re-exports, any new utility file
```typescript
export function ComponentName() { ... }
// re-exported as:
export { ComponentName } from './components/ComponentName'
```
All components use named exports (not default). Default export exists only in `App.tsx` (imported by `main.tsx` directly, not by the library entry).

### Zustand Selector Pattern
**Source:** `viewer/src/App.tsx` lines 25–30, `viewer/src/components/FilterPanel.tsx` lines 10–18
**Apply to:** All components that must switch to `useViewerStore` for dashboard isolation
```typescript
const graph = useStore(s => s.graph)
const filters = useStore(s => s.filters)
```
Selectors are arrow functions inline with the hook call — no `createSelector` abstraction. This pattern continues unchanged for Phase 5.

### Vite `defineConfig` Plugin Composition
**Source:** `viewer/vite.config.ts` lines 1–12
**Apply to:** Both `vite.config.app.ts` and `vite.config.lib.ts`
```typescript
import { defineConfig } from 'vite'
// plugins listed in order: [framework, styling, output-mode]
export default defineConfig({
  plugins: [react(), tailwindcss(), viteSingleFile()],
  build: { ... },
})
```
Follow the same `defineConfig` + ordered plugin array pattern. In `vite.config.lib.ts`, the order is `[react(), dts(...)]` (no styling plugin — CSS is built separately).

### GHA Job Pattern
**Source:** `.github/workflows/ci.yml` lines 30–49
**Apply to:** `.github/workflows/viewer-peer-compat.yml`
```yaml
jobs:
  job-name:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 'XX'
      - name: Step name
        working-directory: viewer
        run: npm ci
```
Prefer `working-directory` over `cd viewer &&` in multi-step jobs (the existing `ci.yml` uses `run: cd viewer && ...` inline — the peer-compat workflow uses the cleaner `working-directory` key since all steps operate in `viewer/`).

### TypeScript `tsconfig.json` Extension Pattern
**Source:** `viewer/tsconfig.json` lines 1–23
**Apply to:** `viewer/tsconfig.lib.json`
```json
{
  "extends": "./tsconfig.json",
  "compilerOptions": {
    /* only the keys that differ from the base */
  },
  "include": ["src"],
  "exclude": ["src/__tests__", "src/main.tsx", "src/sample-data.ts"]
}
```

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `package.json` (root) | config | — | No root `package.json` exists in the repo; file does not exist at all today. Pattern is from npm workspaces documentation (trivial 3-line file). |

---

## Critical Constraints Summary

These are the load-bearing correctness requirements identified from CONTEXT.md and RESEARCH.md:

1. **`vite-plugin-singlefile` isolation** — Must ONLY appear in `vite.config.app.ts`. Its presence in `vite.config.lib.ts` will corrupt library output silently.

2. **`useStore` singleton preservation** — The existing `export const useStore = create<StoreState>(...)` in `store.ts` MUST remain exported. Zero test changes allowed (RESEARCH.md confirms 130 passing tests depend on direct `.setState`/`.getState` calls on the singleton).

3. **`'use client'` via banner, not source** — The directive in `dist/lib/index.js` must come from `output.banner`, not from a source-level string. Rollup's optimizer strips source-level bare string statements.

4. **`postbuild` script preservation** — `viewer/package.json` `postbuild: cp dist/index.html ../cli/infracanvas/export/viewer_template.html` must survive unmodified. The CLI Python layer reads `viewer_template.html` and does a string-replace of `window.__INFRACANVAS_DATA__ = null;` — this contract is byte-for-byte sensitive.

5. **`allowImportingTsExtensions` + `noEmit` coupling** — `tsconfig.lib.json` MUST override both `allowImportingTsExtensions: false` AND `noEmit: false` together. Flipping one without the other causes `tsc` to fail.

6. **`sideEffects: ["**/*.css"]`** — Must be in `viewer/package.json`. Without it, Webpack/Turbopack in Next.js may tree-shake the `import '@infracanvas/viewer/styles.css'` statement.

---

## Metadata

**Analog search scope:** `viewer/`, `.github/workflows/`
**Files read:** 14 source files + 2 context files
**Pattern extraction date:** 2026-04-21

---

## PATTERN MAPPING COMPLETE

**Phase:** 05 - viewer-extraction
**Files classified:** 14
**Analogs found:** 13 / 14

### Coverage
- Files with exact analog: 8 (vite.config.app.ts, tsconfig.lib.json, viewer/package.json, main.tsx, store.ts, App.tsx, 8 unchanged components, ci workflow)
- Files with role-match analog: 4 (vite.config.lib.ts, src/index.ts, lib-styles.css, viewer-peer-compat.yml)
- Files with no analog: 1 (root package.json)

### Key Patterns Identified
- All Vite configs use `defineConfig` + ordered plugin array; split into two files to isolate `vite-plugin-singlefile` from library output.
- All components use named exports (`export function Foo()`) — no default exports except `App.tsx`; barrel `index.ts` re-exports all 13 with one named alias (`ResourceNode` component → `ResourceNodeComponent`).
- Zustand store uses coexistence pattern: module singleton (`useStore`) stays for CLI HTML + tests; factory (`createViewerStore`) + Context (`ViewerProvider`) added alongside for dashboard.
- GHA workflows follow `actions/checkout@v4` + `actions/setup-node@v4` + `working-directory` structure; peer-compat adds `strategy.matrix` on top.
- Tailwind v4 library CSS is built by `@tailwindcss/cli` (not the Vite plugin) with `@source` scoping to prevent class over-inclusion.

### File Created
`/Users/bhushan/Documents/Projects/Infracanvas/.planning/phases/05-viewer-extraction/05-PATTERNS.md`

### Ready for Planning
Pattern mapping complete. Planner can now reference analog patterns in PLAN.md files.
