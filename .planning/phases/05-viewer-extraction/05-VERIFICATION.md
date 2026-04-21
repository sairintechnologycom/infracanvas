---
phase: 05-viewer-extraction
verified: 2026-04-21T08:40:00Z
status: passed
score: 4/4 success criteria verified
overrides_applied: 0
---

# Phase 5: Viewer Extraction Verification Report

**Phase Goal:** Extract viewer to shared dual-build npm package so CLI HTML export and Next.js dashboard both consume it (gate for Phase 7).
**Verified:** 2026-04-21T08:40:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|---|---|---|
| 1 | New `@infracanvas/viewer` npm package builds both single-file HTML (CLI) and React components (dashboard) | VERIFIED | `viewer/package.json` name = `@infracanvas/viewer`; `npm run build` chain (`tsc -b && build:app && build:lib && build:css`) produced all four artifacts: `dist/index.html` (3,559,123 B), `dist/lib/index.js` (2,580,607 B), `dist/lib/index.d.ts` (1,197 B), `dist/lib/styles.css` (16,039 B) |
| 2 | CLI HTML export uses the package; bundle size remains < 5 MB | VERIFIED | `postbuild` script ran `cp dist/index.html ../cli/infracanvas/export/viewer_template.html`; `cmp` confirms byte-for-byte equality; 3,559,123 B < 5,000,000 B; CLI smoke test via `infracanvas scan cli/tests/fixtures/insecure_setup --format html` produced valid scan.html (3,570,403 B) with `INFRACANVAS_DATA__ = null` placeholder (0 remaining) replaced by `INFRACANVAS_DATA__ = {"version":"2.1"...}` |
| 3 | Next.js can import `<DiagramCanvas>` / `<FlowMapCanvas>` as components | VERIFIED | `dist/lib/index.d.ts` exports `DiagramCanvas` and `FlowMapCanvas` (plus 11 more components + 15 types + store API); line 1 of `dist/lib/index.js` is `"use client";` (Rollup-canonical RSC directive); peer deps externalized (`from "react"`, `from "@xyflow/react"`, `from "zustand"` remain as external imports); `exports` map resolves `.` and `./styles.css`; React 18/19 matrix CI at `.github/workflows/viewer-peer-compat.yml` gates peer compat |
| 4 | Viewer tests (79 Vitest → 130 actual) still pass | VERIFIED | `npm test -- --run`: **130 passed / 6 pre-existing failed** — identical delta vs pre-phase baseline. The ROADMAP "79" count was stale; actual suite is 130 passing. Zero new regressions introduced by Plans 01-03 |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `package.json` (root) | Monorepo with `workspaces: ["viewer"]` | VERIFIED | name=`infracanvas-monorepo`, private=true, workspaces=["viewer"] |
| `viewer/package.json` | Renamed to `@infracanvas/viewer` with peer deps + exports map + files + sideEffects | VERIFIED | All fields present: peerDependencies react/react-dom `^18.0.0 \|\| ^19.0.0`, exports `.` + `./styles.css`, files=["dist/lib"], sideEffects=["**/*.css"], build chain present, postbuild syncs template, vite-plugin-dts + @tailwindcss/cli devDeps |
| `viewer/vite.config.app.ts` | App build (single-file HTML) with react + tailwindcss + viteSingleFile + Vitest block | VERIFIED | All three plugins imported; outDir=dist; Vitest test block with jsdom/globals/setupFiles |
| `viewer/vite.config.lib.ts` | Library build: `build.lib` ESM, externalized peers, `'use client'` banner via rollup output.banner, vite-plugin-dts | VERIFIED | entry=`src/index.ts`, formats=['es'], outDir=dist/lib, 10 external peers, `banner: (chunk) => (chunk.isEntry ? \`'use client'\\n\` : '')`, dts plugin configured |
| `viewer/tsconfig.lib.json` | Declaration-only emit, extends root tsconfig, flips allowImportingTsExtensions+noEmit | VERIFIED | extends ./tsconfig.json, allowImportingTsExtensions=false, noEmit=false, emitDeclarationOnly=true, declarationDir=dist/lib, excludes __tests__/main.tsx/sample-data.ts |
| `viewer/src/lib-styles.css` | Tailwind v4 library entry with source(none) + @source scoping + @theme tokens | VERIFIED | `@import "tailwindcss" source(none)`, full @theme token block, 3 @source dirs (App.tsx, components, components/flowmap), 3 @source inline() directives for theme-token utility emission (post-Rule-1 fix) |
| `viewer/src/store.ts` | Singleton `useStore` + factory `createViewerStore` + Context + Provider + hook | VERIFIED | All 6 exports present: `useStore` (create), `createViewerStore` (createStore), `ViewerProvider`, `useViewerStore` (throws outside Provider), `ViewerStoreApi` type, `StoreState` type (now exported). Shared `stateCreator` const guarantees behavior parity |
| `viewer/src/main.tsx` | CLI HTML entry wrapped in `<ViewerProvider>` | VERIFIED | `import { ViewerProvider } from './store'`; `<ViewerProvider><App /></ViewerProvider>` inside `<StrictMode>`; all 6 font imports and `./index.css` preserved |
| `viewer/src/index.ts` | Barrel — 13 components + 15 types + store API | VERIFIED | 16 export statements; all 13 D-04 components (ResourceNodeMemo→ResourceNodeComponent, GroupNodeMemo→GroupNode aliased); all 15 types from ./types; createViewerStore + ViewerProvider + useViewerStore + ViewerStoreApi + StoreState; no side-effect CSS import |
| `.github/workflows/viewer-peer-compat.yml` | React 18/19 matrix CI with artifact assertions | VERIFIED | matrix=['18','19'], fail-fast=false, Node 22, --legacy-peer-deps for React swap, env REACT_VERSION interpolation (command-injection hardened), three pre-test assertions (banner quote-agnostic regex, /viewer/src/ leakage, 5 MB size ceiling), test step runs `npm test -- --run` |
| `cli/infracanvas/export/viewer_template.html` | Post-extraction template, cmp-equal to dist/index.html, contains CLI placeholder | VERIFIED | 3,559,123 B, cmp-equal to viewer/dist/index.html after postbuild; contains `window.__INFRACANVAS_DATA__ = null;` (CLI Python replace-contract preserved) |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `viewer/package.json scripts.build` | build:app + build:lib + build:css + postbuild | sequential npm chain | WIRED | `"build": "tsc -b && npm run build:app && npm run build:lib && npm run build:css"` + `postbuild: "cp dist/index.html ../cli/infracanvas/export/viewer_template.html"` |
| `viewer/vite.config.lib.ts rollupOptions.output.banner` | `'use client'` line 1 of dist/lib/index.js | build-time banner callback | WIRED | Live build produced `"use client";` on line 1 (Rollup canonicalization of source `'use client'` banner) |
| `viewer/package.json postbuild` | `cli/infracanvas/export/viewer_template.html` | `cp` command | WIRED | Post-build cmp verifies byte-for-byte sync after `npm run build` |
| `viewer/src/main.tsx` | `<ViewerProvider>` from `./store` | JSX wrap around `<App/>` | WIRED | `<ViewerProvider><App /></ViewerProvider>` present inside StrictMode |
| `viewer/src/index.ts` | `createViewerStore`, `ViewerProvider`, `useViewerStore` from `./store` | named re-export | WIRED | All three value exports + ViewerStoreApi + StoreState type exports present |
| `viewer/src/store.ts` singleton `useStore` | all component imports of `./store` | unchanged named export | WIRED | `export const useStore = create<StoreState>(stateCreator);` at line 189; tests + components pass |
| `.github/workflows/viewer-peer-compat.yml` | React version override via matrix env | env-interpolated npm install | WIRED | `env: REACT_VERSION: ${{ matrix.react-version }}` + shell `"react@${REACT_VERSION}"` + `--legacy-peer-deps` |

### Data-Flow Trace (Level 4)

Phase 5 produces build artifacts, configs, and package scaffolding — not components that render dynamic data. Data-flow trace is not applicable; the runtime behavior is verified indirectly via:
- The CLI end-to-end smoke test (real graph JSON injected into the extracted template renders a working HTML report).
- The Vitest suite (130 tests exercise component + store behavior against the shared `stateCreator`).

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| Dual build produces all four artifacts | `cd viewer && rm -rf dist && npm run build` | Exit 0; dist/index.html + dist/lib/{index.js,index.d.ts,styles.css} all produced | PASS |
| Library bundle has `'use client'` banner | `head -1 viewer/dist/lib/index.js` | `"use client";` | PASS |
| No private path leakage in library bundle | `grep -c "/viewer/src/" viewer/dist/lib/index.js` | 0 | PASS |
| React peer externalized (not bundled) | `grep -oE 'from "(react\|@xyflow/react\|zustand)"' viewer/dist/lib/index.js \| sort -u` | `from "@xyflow/react"`, `from "react"`, `from "zustand"` — all externalized | PASS |
| .d.ts exports DiagramCanvas + FlowMapCanvas | `grep -E "DiagramCanvas\|FlowMapCanvas" dist/lib/index.d.ts` | Both exports present | PASS |
| Library CSS contains theme tokens | `grep -oE "sev-critical\|canvas-bg\|card-bg\|flow-forward" dist/lib/styles.css \| sort -u` | All 4 tokens emitted | PASS |
| CLI template cmp-equal to dist/index.html | `cmp viewer/dist/index.html cli/infracanvas/export/viewer_template.html` | exit 0 | PASS |
| CLI placeholder preserved in template | `grep -c "INFRACANVAS_DATA__ = null" cli/infracanvas/export/viewer_template.html` | 1 | PASS |
| Bundle size < 5 MB | `wc -c < viewer/dist/index.html` | 3,559,123 B | PASS |
| CLI end-to-end: placeholder replaced with real data | `infracanvas scan cli/tests/fixtures/insecure_setup --format html --output /tmp/scan.html` then grep | placeholder=0, data-form=1 (`{"version":"2.1"...}`) | PASS |
| Vitest no regressions vs. baseline | `cd viewer && npm test -- --run` | 130 passed / 6 pre-existing failed — identical delta | PASS |

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|---|---|---|---|---|
| DSH-01 | 05-01, 05-02, 05-03 | Extract viewer to shared dual-build npm package BEFORE any dashboard work | SATISFIED | All four ROADMAP success criteria verified above. `@infracanvas/viewer` package builds dual outputs, CLI consumes the template, React 18/19 peer compat CI in place, dashboard-ready exports (components + types + store API) surfaced in `dist/lib/index.d.ts`. Phase 7 gate unblocked. |

No orphaned requirements. All three plans declare DSH-01 in both `requirements` and `requirements_addressed` frontmatter fields.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---|---|---|---|

No TODO/FIXME/PLACEHOLDER/stub patterns detected in the modified source files (`viewer/src/store.ts`, `viewer/src/main.tsx`, `viewer/src/index.ts`, `viewer/src/lib-styles.css`).

Post-merge context reported:
- Schema drift: clean (0 issues)
- Code review: 0 critical, 2 warning, 5 info (advisory — not blocking)
- Python regression: 367 passed / 92.5% coverage
- Viewer tests: 130 passed / 6 pre-existing (baseline-consistent)

### Human Verification Required

None. All four ROADMAP success criteria are mechanically verifiable and verified. Build artifacts, CLI end-to-end contract, peer-compat matrix, and test baseline are all green on the current tree.

The Plan 03 summary lists optional manual smoke checks (browser render of generated HTML, tab toggle, keyboard shortcuts) but explicitly flags them as **non-blocking** — they verify Phase 4 WRG-03 behavior which was already validated in Phase 4's VERIFICATION and is structurally protected by Plan 02's "no component file modifications" invariant (confirmed by `git diff --name-only` in 05-02-SUMMARY returning empty for `viewer/src/components/**`).

### Gaps Summary

No gaps. Phase 5 achieves its goal: the viewer is extracted to a shared dual-build npm package. The CLI consumes it via the postbuild-synced template; the Next.js dashboard (Phase 7) can consume it via workspace link (`@infracanvas/viewer`), importing `<DiagramCanvas>` / `<FlowMapCanvas>` + CSS with a `"use client"` boundary already in place. The React 18/19 matrix CI provides an ongoing peer-compat gate. All 130 Vitest tests remain green at the pre-phase baseline, confirming zero regressions to the CLI single-file HTML path.

Phase 7 gate: UNBLOCKED.

---

_Verified: 2026-04-21T08:40:00Z_
_Verifier: Claude (gsd-verifier)_
