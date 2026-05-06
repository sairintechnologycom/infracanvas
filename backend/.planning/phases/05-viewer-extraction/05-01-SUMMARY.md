---
phase: 05-viewer-extraction
plan: 01
subsystem: infra
tags: [viewer, vite, library-mode, tailwind, workspace, monorepo, npm-workspaces, vite-plugin-dts]

# Dependency graph
requires:
  - phase: 04-e2e-wiring-hardening
    provides: Stable viewer source tree with Canvas/FlowMap tab wiring that must not regress
provides:
  - Dual Vite build configs (vite.config.app.ts for CLI single-file HTML, vite.config.lib.ts for library ESM)
  - tsconfig.lib.json for declaration-only emit via vite-plugin-dts
  - Tailwind v4 library CSS entry (src/lib-styles.css) with source(none) scoping
  - @infracanvas/viewer package rename with peerDependencies and exports map
  - Root monorepo package.json with npm workspaces
  - node_modules hoisted with vite-plugin-dts and @tailwindcss/cli installed
affects:
  - 05-02 (needs src/index.ts barrel pointed at by vite.config.lib.ts)
  - 05-03 (runs end-to-end dual build and asserts artifacts)
  - 07 (Next.js dashboard consumes @infracanvas/viewer via workspace link)

# Tech tracking
tech-stack:
  added:
    - vite-plugin-dts@^4.5.4 (declaration-only emit for library build)
    - "@tailwindcss/cli@^4.1.4 (build-time CSS compilation, no runtime Tailwind on consumer)"
    - npm workspaces (root package.json with workspaces:[viewer])
  patterns:
    - Dual Vite build — one source tree, two configs (app + lib) via --config flag
    - "'use client' banner emitted from rollup output.banner (NOT source-level bare string; Rollup strips those)"
    - Tailwind v4 library CSS via source(none) + explicit @source scoping (excludes main.tsx, tests, sample-data)
    - Peer deps externalized in lib build; kept in dependencies so CLI HTML build still resolves them
    - "files:[dist/lib] + sideEffects:[**/*.css] combo prevents src/ leakage and allows CSS import"

key-files:
  created:
    - viewer/vite.config.app.ts (CLI single-file HTML build config)
    - viewer/vite.config.lib.ts (library ESM build with externalized peers and 'use client' banner)
    - viewer/tsconfig.lib.json (extends root tsconfig, emitDeclarationOnly:true)
    - viewer/src/lib-styles.css (Tailwind v4 library entry, source(none) + three @source dirs)
    - package.json (root monorepo with workspaces:[viewer])
    - package-lock.json (hoisted root lockfile)
  modified:
    - viewer/package.json (renamed to @infracanvas/viewer, dual build scripts, peer deps, exports map)
  deleted:
    - viewer/vite.config.ts (contents migrated to vite.config.app.ts)
    - viewer/package-lock.json (replaced by root-hoisted lockfile under npm workspaces)

key-decisions:
  - "Use npm workspaces (not file: reference) — one array edit adds Phase 7 dashboard; single root lockfile prevents drift"
  - "vite-plugin-dts over separate tsc --emitDeclarationOnly pass — single plugin, single config source"
  - "formats:['es'] only in lib build — modern consumers (Next.js 15) need ESM; CJS adds surface area not needed"
  - "@tailwindcss/cli (build-time) over @tailwindcss/vite (runtime) in lib build — consumer must not re-run Tailwind on every render (T-05-03 mitigation)"
  - "Keep react/react-dom in dependencies even though peerDependencies is declared — CLI HTML build needs them present; peerDependencies communicates version flexibility to library consumers"
  - "emptyOutDir:true + copyPublicDir:false on lib build — dist/lib owned exclusively by lib pipeline; no public/ leakage"

patterns-established:
  - "Dual Vite build: `npm run build:app` → dist/index.html (for CLI viewer_template.html); `npm run build:lib` → dist/lib/index.js + .d.ts; `npm run build:css` → dist/lib/styles.css"
  - "'use client' directive injected via rollupOptions.output.banner callback (chunk.isEntry gate)"
  - "Tailwind v4 library CSS: @import 'tailwindcss' source(none) + explicit @source directives scoped to App.tsx + components dirs only"
  - "Workspace root holds package-lock.json; child packages no longer carry their own lockfile"

requirements-completed: [DSH-01]

# Metrics
duration: ~15min
completed: 2026-04-21
---

# Phase 05 Plan 01: Dual-Build Scaffolding Summary

**Split viewer Vite config into app + lib targets, renamed package to @infracanvas/viewer with peer deps and exports map, established npm workspaces root — unlocking Next.js dashboard consumption in Phase 7.**

## Performance

- **Duration:** ~15 min (includes 55s npm install)
- **Started:** 2026-04-21T01:50:00Z (approx)
- **Completed:** 2026-04-21T02:05:46Z
- **Tasks:** 3
- **Files modified:** 7 (5 created, 1 modified, 2 deleted, 1 renamed)

## Accomplishments

- Dual Vite build scaffolding in place: `vite.config.app.ts` preserves the CLI single-file HTML pipeline; `vite.config.lib.ts` emits the library ESM build with peer deps externalized and `'use client'` banner via `rollupOptions.output.banner`.
- `viewer/package.json` renamed to `@infracanvas/viewer` with `peerDependencies: react ^18||^19`, `exports` map for `.` and `./styles.css`, `files: ["dist/lib"]` scope, and `sideEffects: ["**/*.css"]` — addressing T-05-02 (info disclosure) and T-05-03 (DoS from runtime Tailwind).
- Root monorepo `package.json` with `workspaces: ["viewer"]` created; single hoisted `package-lock.json` replaces per-workspace lockfiles. `vite-plugin-dts@^4.5.4` and `@tailwindcss/cli@^4.1.4` installed.
- No source files touched — Phase 4 Canvas↔FlowMap tab wiring regression-protected.

## Task Commits

Each task was committed atomically:

1. **Task 1: Split Vite config + tsconfig.lib.json + lib-styles.css** — `3f52213` (feat)
2. **Task 2: Rewrite viewer/package.json for dual-build + peer deps + exports** — `d418e20` (feat)
3. **Task 3: Root monorepo package.json + npm install** — `6cd2f8e` (feat)

## Files Created/Modified

- `viewer/vite.config.app.ts` (new) — CLI single-file HTML build: react + tailwindcss + viteSingleFile plugins; Vitest test block.
- `viewer/vite.config.lib.ts` (new) — Library ESM build; externalizes react, react-dom, react/jsx-runtime, @xyflow/react, zustand, zustand/vanilla, dagre, elkjs, lucide-react, aws-react-icons; `'use client'` banner; vite-plugin-dts for `.d.ts` emit.
- `viewer/tsconfig.lib.json` (new) — Extends root tsconfig; flips `allowImportingTsExtensions:false` and `noEmit:false` together (TypeScript couples them); `emitDeclarationOnly:true`; excludes `__tests__`, `main.tsx`, `sample-data.ts`.
- `viewer/src/lib-styles.css` (new) — `@import "tailwindcss" source(none)` + full `@theme` token block + three explicit `@source` dirs (App.tsx, components, components/flowmap). Excludes main.tsx and tests from Tailwind scan.
- `viewer/package.json` (modified) — Renamed to `@infracanvas/viewer`; `build` now chains `tsc -b && build:app && build:lib && build:css`; added peerDependencies (react/react-dom ^18||^19), exports map, main/module/types fields, files:["dist/lib"], sideEffects:["**/*.css"]; added `vite-plugin-dts` and `@tailwindcss/cli` devDeps; `postbuild` unchanged byte-for-byte (CLI template sync preserved).
- `viewer/vite.config.ts` (deleted) — Contents migrated to `vite.config.app.ts`; deletion removes ambiguity about which config is active. Git detected the move as a rename.
- `viewer/package-lock.json` (deleted) — Replaced by root-hoisted lockfile under npm workspaces.
- `package.json` (new, repo root) — `{ name: "infracanvas-monorepo", private: true, workspaces: ["viewer"] }`.
- `package-lock.json` (new, repo root) — Generated by `npm install` at root; 284 packages, 0 vulnerabilities.

## Decisions Made

See `key-decisions` in frontmatter. Key rationale recap:

- Workspaces over `file:` link — Phase 7 dashboard adds with one array edit; prevents version drift.
- `vite-plugin-dts` chosen over separate `tsc --emitDeclarationOnly` pass — single plugin, single source of truth.
- `formats: ['es']` only — modern consumers (Next.js 15) want ESM.
- `@tailwindcss/cli` (build-time) in lib pipeline, NOT `@tailwindcss/vite` (runtime) — consumer must receive pre-compiled `styles.css`, never re-run Tailwind on render (T-05-03).
- `react`/`react-dom` remain in `dependencies` alongside `peerDependencies` — CLI HTML build needs them resolvable locally; peerDependencies communicates version flexibility to library consumers.

## Deviations from Plan

None — plan executed exactly as written.

Per the plan's explicit instruction (`<success_criteria>`: "No build commands attempted (Plan 03 runs the end-to-end build)"), no build was attempted. The lib build would fail until Plan 02 creates `viewer/src/index.ts` — this is intentional and documented in the plan.

## Issues Encountered

None. `npm install` completed successfully: 284 packages added, 0 vulnerabilities reported, no peer-dep warnings surfaced at the workspace root.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

Ready for Plan 05-02 (store factory + barrel):
- `viewer/vite.config.lib.ts` is pointed at `src/index.ts` and will fail until Plan 02 creates that barrel — expected.
- `viewer/tsconfig.lib.json` already excludes the files Plan 02 won't touch (`__tests__`, `main.tsx`, `sample-data.ts`).
- `@infracanvas/viewer` package name and `exports` map in place — Plan 02's barrel exports will flow into `dist/lib/index.js` + `.d.ts`, and Plan 03 can assert the `'use client'` banner and Tailwind CSS artifact.
- Monorepo root is set up — Phase 7 dashboard can add `"dashboard"` to `workspaces: [...]` and immediately `import { ... } from '@infracanvas/viewer'`.

No blockers.

## Self-Check: PASSED

- FOUND: viewer/vite.config.app.ts
- FOUND: viewer/vite.config.lib.ts
- FOUND: viewer/tsconfig.lib.json
- FOUND: viewer/src/lib-styles.css
- FOUND: viewer/package.json (modified, name=@infracanvas/viewer)
- FOUND: package.json (root monorepo)
- FOUND: package-lock.json (root)
- MISSING (intentional): viewer/vite.config.ts (deleted per plan)
- MISSING (intentional): viewer/package-lock.json (replaced by root lockfile)
- FOUND commit: 3f52213 (Task 1)
- FOUND commit: d418e20 (Task 2)
- FOUND commit: 6cd2f8e (Task 3)

---
*Phase: 05-viewer-extraction*
*Completed: 2026-04-21*
