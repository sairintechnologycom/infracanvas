---
phase: 05-viewer-extraction
reviewed: 2026-04-21T00:00:00Z
depth: standard
files_reviewed: 10
files_reviewed_list:
  - .github/workflows/viewer-peer-compat.yml
  - package.json
  - viewer/package.json
  - viewer/src/index.ts
  - viewer/src/lib-styles.css
  - viewer/src/main.tsx
  - viewer/src/store.ts
  - viewer/tsconfig.lib.json
  - viewer/vite.config.app.ts
  - viewer/vite.config.lib.ts
findings:
  critical: 0
  warning: 2
  info: 5
  total: 7
status: issues_found
---

# Phase 5: Code Review Report

**Reviewed:** 2026-04-21
**Depth:** standard
**Files Reviewed:** 10
**Status:** issues_found

## Summary

Phase 5 landed the dual-build scaffolding (single-file CLI HTML + npm library), a Zustand store factory + `ViewerProvider` Context + `useViewerStore` hook alongside the existing singleton, the `viewer/src/index.ts` library barrel, and a React 18/19 peer-compat CI matrix. The shared `stateCreator` pattern for both `useStore` and `createViewerStore` is a strong choice — it guarantees behavioral parity between the singleton and factory. The non-breaking "singleton stays" posture is explicitly documented in `05-02-SUMMARY.md` and matches the code.

No critical bugs or security issues were found. Two warning-level issues are worth addressing before Phase 7 consumes the library: (1) `@xyflow/react` subpath CSS imports are not covered by the Rollup `external` list (exact-string match), which will likely cause the xyflow stylesheet to be inlined into `dist/lib/` assets — a double-style hazard for downstream Next.js consumers; and (2) the CI matrix's cross-version install step relies on lockfile-less workspace mutation, which is fragile. Remaining findings are informational — minor polish items around test tooling, script invocation, and config separation.

## Warnings

### WR-01: Rollup `external` misses `@xyflow/react` CSS subpath import

**File:** `viewer/vite.config.lib.ts:29-40`
**Issue:** The `external` array uses exact-string package names:
```ts
external: [
  'react',
  'react-dom',
  'react/jsx-runtime',
  '@xyflow/react',
  'zustand',
  ...
],
```
But `DiagramCanvas.tsx:14` and `flowmap/FlowMapCanvas.tsx:17` contain `import '@xyflow/react/dist/style.css'`. Rollup treats `@xyflow/react/dist/style.css` as a distinct module ID from `@xyflow/react`, so this subpath import will NOT be externalized — Vite will either bundle the xyflow CSS into a `dist/lib/style.css` asset or inline it into the library's emitted CSS, depending on processing order. Downstream Phase 7 consumers that also import `@xyflow/react/dist/style.css` on the dashboard side will double-load the stylesheet (and the CI `assert bundle size` step only checks `dist/index.html`, not `dist/lib`, so this slips through). It also defeats the `"sideEffects": ["**/*.css"]` contract: consumers expect first-party CSS only via `./styles.css`.

**Fix:** Switch to regex externals so all subpaths of each externalized package are covered:
```ts
external: [
  /^react($|\/)/,
  /^react-dom($|\/)/,
  /^@xyflow\/react($|\/)/,
  /^zustand($|\/)/,
  /^dagre($|\/)/,
  /^elkjs($|\/)/,
  /^lucide-react($|\/)/,
  /^aws-react-icons($|\/)/,
],
```
Then add a CI assertion that `dist/lib/` contains no xyflow CSS bytes, e.g. `grep -q "@xyflow" dist/lib/styles.css && exit 1 || true`.

### WR-02: Peer-compat CI override mutates workspace install, risking lockfile drift and hoist conflicts

**File:** `.github/workflows/viewer-peer-compat.yml:32-45`
**Issue:** The workflow runs `npm ci` at repo root (which installs the `viewer` workspace via hoisting), then in step 2 runs `npm install react@${REACT_VERSION} ... --legacy-peer-deps` inside `viewer/`. Because `viewer/` is a workspace (root `package.json:4` declares `"workspaces": ["viewer"]`) and no lockfile lives inside `viewer/`, this second `npm install` mutates the root `package-lock.json` and can either hoist the new React versions to root `node_modules/react` or create nested copies depending on npm's de-dup heuristics. Two concrete risks:
1. The second install can fail the CI run's cache integrity since `npm ci` demands the lockfile exactly match `node_modules`, and the mutation happens after `npm ci` but before type-check/build — any tool that re-runs `npm ci` (e.g. a shared action) would now fail.
2. `--legacy-peer-deps` suppresses peer-conflict warnings that are the actual signal the matrix is meant to catch (since `react-dom@19` with `react@18` would otherwise error). Using `--legacy-peer-deps` partially defeats the purpose of a peer-compat matrix.

**Fix:** Install from the root with workspace targeting and avoid saving:
```yaml
- name: Override React version
  env:
    REACT_VERSION: ${{ matrix.react-version }}
  run: |
    npm install --workspace=@infracanvas/viewer --no-save \
      "react@${REACT_VERSION}" \
      "react-dom@${REACT_VERSION}" \
      "@types/react@${REACT_VERSION}" \
      "@types/react-dom@${REACT_VERSION}"
```
Drop `--legacy-peer-deps` — if the matrix hits a genuine peer conflict (e.g. a transitive dep requiring `react@^18`), that is a signal the peer-range claim in `viewer/package.json:30-32` is wrong and the CI should fail.

## Info

### IN-01: `useViewerStore` is exported but no in-repo component consumes it

**File:** `viewer/src/store.ts:203-227`, `viewer/src/main.tsx:16-19`
**Issue:** `ViewerProvider` wraps `<App/>` in `main.tsx`, and `useViewerStore` is exported from `index.ts:55-59`, but every existing component (`DiagramCanvas`, `FilterPanel`, `DetailPanel`, `SummaryBar`, `TabBar`, `SearchBar`, `ResourceNode`, `FlowMapCanvas`, `FlowMapFilterPanel`, `PathDetailPanel`, and `App.tsx:25-30`) still calls the singleton `useStore`. For the CLI HTML path this is fine because the singleton's state is per-page-load anyway, but it means the `<ViewerProvider store={...}>` slot that Phase 7 plans to use will have zero effect on the bundled components — the dashboard will get per-route state isolation only for *new* components that opt into `useViewerStore`, while every existing component continues to share the singleton across all routes, silently re-introducing the DSH-01 cross-scan bleed the factory was meant to solve.

Per `05-02-SUMMARY.md:13` this is intentional for Phase 5 ("no component migrated"), but flagging it here so Phase 7's plan doesn't assume the wiring is complete.
**Fix:** No code change in Phase 5. Phase 7's plan should include either (a) migrating all 13 components from `useStore` to `useViewerStore` before the dashboard ships, or (b) adding a guard that `useStore` is not called by any component re-exported through `viewer/src/index.ts` (lint rule / grep assertion in CI) so the gap is caught before integration.

### IN-02: `build:css` uses `npx` for a direct devDependency

**File:** `viewer/package.json:23`
**Issue:** `"build:css": "npx @tailwindcss/cli -m -i src/lib-styles.css -o dist/lib/styles.css"` uses `npx`, which adds a package-lookup roundtrip on every CI run and could, in rare CI environments with a stale npm cache, fetch a different version than the one pinned in `devDependencies` (`@tailwindcss/cli: ^4.1.4`). Since the dep is already installed locally, `npx` is slower and slightly less deterministic than invoking the binary directly.
**Fix:** Drop `npx`:
```json
"build:css": "@tailwindcss/cli -m -i src/lib-styles.css -o dist/lib/styles.css"
```
npm runs scripts with `node_modules/.bin` on PATH, so the binary resolves directly.

### IN-03: `npm test -- --run` passes redundant `--run` to Vitest

**File:** `.github/workflows/viewer-peer-compat.yml:89`
**Issue:** The `test` script is already `"vitest run --config vite.config.app.ts"` (viewer/package.json:26), i.e. `run` is the subcommand. `npm test -- --run` appends `--run` as an extra arg, which Vitest tolerates but logs as a deprecation warning in some versions. Harmless but noisy.
**Fix:** `run: npm test` (no extra args), or change the script to `vitest --config ...` and rely on `--run` at call sites — pick one convention.

### IN-04: `vite.config.app.ts` mixes app-build and test config

**File:** `viewer/vite.config.app.ts:6-19`
**Issue:** The same config declares `plugins: [react(), tailwindcss(), viteSingleFile()]` AND `test: { environment: 'jsdom', ... }`. Vitest loads Vite plugins before deciding what to do, so every `vitest run` spins up `viteSingleFile()` — which is a no-op at test time but adds a few ms of plugin init and obscures the intent. Additionally, any future app-build-only plugin (e.g. a bundle analyzer) would auto-run during tests unless carefully guarded.
**Fix:** Split into `vite.config.app.ts` (build only) and `vitest.config.ts` (test only, extends app config and overrides `plugins` to exclude `viteSingleFile`). Low priority — purely hygienic.

### IN-05: `tsconfig.lib.json` excludes `src/main.tsx` and `src/sample-data.ts` but `include: ["src"]` will re-add any future sibling

**File:** `viewer/tsconfig.lib.json:10-11`
**Issue:** `exclude` lists three specific paths (`src/__tests__`, `src/main.tsx`, `src/sample-data.ts`). If someone adds a new dev-only file (e.g. `src/storybook-entry.tsx` or `src/dev-fixtures.ts`), it will be included in the `.d.ts` output unless explicitly added to the exclude list, which risks leaking internals via the published types. The exclude list mirrors `vite.config.lib.ts:14` (DTS plugin), so the two can drift.
**Fix:** Either (a) restrict `include` to the barrel entry only — `"include": ["src/index.ts", "src/types.ts", "src/components", "src/lib"]` — so only explicitly-tracked dirs are typed; or (b) add a unit test that asserts `dist/lib/index.d.ts` contains only the 17 expected exports and fails on any addition. Today's footprint is fine; this is defense for future drift.

---

_Reviewed: 2026-04-21_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
