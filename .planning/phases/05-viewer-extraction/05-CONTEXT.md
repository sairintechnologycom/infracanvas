# Phase 5: Viewer Extraction - Context

**Gathered:** 2026-04-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Extract the existing `viewer/` Vite app into a shared dual-build package `@infracanvas/viewer` that produces **two artifacts from one source of truth**:

1. The existing self-contained single-file HTML (CLI export path, bundle < 5 MB, drop-in replacement for `cli/infracanvas/export/viewer_template.html`).
2. An importable React component library (`<DiagramCanvas>`, `<FlowMapCanvas>`, plus supporting chrome) consumable by the Next.js 15 dashboard in Phase 7.

This is the **gate for Phase 7** per PROJECT.md Key Decision ("Extract viewer to shared dual-build package BEFORE any Next.js dashboard work") — divergence between CLI viewer and dashboard viewer is a long-term maintenance liability, and extraction happens once now rather than forever.

**In scope:** directory/packaging restructure, library build target, Zustand store refactor to factory + Context provider, CSS build, peer-dep widening to support React 18 || 19, preservation of the 79 Vitest tests and the `< 5 MB` single-file bundle.

**Out of scope:** new viewer features, dark mode, theme-override API, any dashboard UI (that's Phase 7), publishing to npm, React 19 upgrade of the CLI viewer.

</domain>

<decisions>
## Implementation Decisions

### Package layout (Area 1)
- **D-01:** Stay in `viewer/`. Extend `viewer/vite.config.ts` with a **second build target in library mode** so one `npm run build` produces both `dist/index.html` (CLI template, current behavior via `vite-plugin-singlefile`) and `dist/lib/` (ESM package entry + `.d.ts`). No file moves, tests stay in place, minimal churn.
- **D-02:** Rename `viewer/package.json` from `infracanvas-viewer` (`private: true`) to **`@infracanvas/viewer`**. Keep it **workspace-internal** — no npm publish (public or private). Dashboard consumes via workspace link (a root `package.json` with `workspaces: ["viewer"]` is acceptable; simpler alternatives like `file:../viewer` also work if no other JS packages enter the repo). Matches solo-founder ops constraint and open-core strategy (viewer shell is commercial).
- **D-03:** Preserve the existing `postbuild: cp dist/index.html ../cli/infracanvas/export/viewer_template.html` script. CLI release packaging (PyInstaller, sdist, Homebrew) picks up the template exactly as today — no release-workflow changes.

### Export surface (Area 2)
- **D-04:** Export the **full component set** from `@infracanvas/viewer`: `<DiagramCanvas>`, `<FlowMapCanvas>`, `<FilterPanel>`, `<FlowMapFilterPanel>`, `<DetailPanel>`, `<PathDetailPanel>`, `<TabBar>`, `<SearchBar>`, `<SummaryBar>`, `<GroupNode>`, `<ResourceNode>`, `<FindingCard>`, `<FlowMapEmptyState>`. Dashboard reuses the exact same UX as the CLI HTML — zero re-composition, zero divergence.
- **D-05:** Re-export all public types from `viewer/src/types.ts`: `ResourceGraph`, `ResourceNode`, `Finding`, `NetworkFinding`, `NetworkPath`, `PathHop`, `DCSite`, `Severity`, `DriftStatus` (+ any sibling union types the exported components accept as props). Schema drift surfaces at TypeScript compile time, not runtime.
- **D-06:** Icons (`aws-react-icons` + `viewer/src/icons/*`) are **bundled internally, not re-exported**. Dashboard uses its own icon system for non-canvas UI. Smaller public API, no icon-library lock-in beyond what canvases require.
- **D-07:** Single CSS entry: consumer imports `'@infracanvas/viewer/styles.css'`. One file, no tree-shaking complexity.

### Styling strategy (Area 3)
- **D-08:** Ship **pre-compiled CSS** bundled with the package. The library build runs Tailwind v4 (`@tailwindcss/vite`) over the viewer's components once and emits `dist/lib/styles.css` containing every utility class the exported components actually render. Consumer (Next.js dashboard) needs **no Tailwind peer dep** — their own Tailwind build for their own UI runs side-by-side with this static CSS file.
- **D-09:** **Fixed color tokens** for Phase 5. Current severity/zone/surface palette ships unchanged. CSS-variable theming is deferred to a later dashboard design phase once the visual language is locked.
- **D-10:** **No dark-mode changes.** Whatever light/dark behavior the viewer has today ships unchanged. Dark mode is a new capability — deferred.

### Store & React version (Area 4)
- **D-11:** Refactor `viewer/src/store.ts` to export a **`createViewerStore()` factory**. Components read the store via React Context wired by `<ViewerProvider>`. The current module-level singleton becomes a default instance used by the CLI HTML entry (`viewer/src/main.tsx` continues to render `<ViewerProvider store={defaultStore}>` around `<App/>`) so CLI HTML behavior is byte-for-byte unchanged. Next.js dashboard gets a fresh store per page mount — no cross-scan state bleed, no SSR hydration landmines.
- **D-12:** **Peer-dep range: `react: "^18.0.0 || ^19.0.0"`, `react-dom: "^18.0.0 || ^19.0.0"`.** Viewer/CLI stay on React 18 for this phase; Next.js 15 dashboard (Phase 7) can use React 19 default without requiring a viewer upgrade. CI smoke-tests the package build under both major versions.
- **D-13:** Package entry is marked **`'use client'`** (either at `dist/lib/index.js` header or per-component). @xyflow/react and Zustand both need browser APIs; SSR for a pan/zoom canvas is wasted work. Dashboard wraps the viewer in `<Suspense>` if a loading boundary is desired.

### Claude's Discretion
- Exact Vite library-mode config (`build.lib` entry, formats, `external` list for `react`/`react-dom`/`@xyflow/react`/`zustand`/etc., rollup `preserveModules` setting).
- Whether to introduce a root `package.json` with an `npm workspaces` declaration vs. a minimal `file:` reference — either satisfies D-02. Pick whichever keeps `cli/` + `viewer/` dependency graphs cleanly separated.
- Exact TypeScript declaration-generation approach (`vite-plugin-dts` vs. a separate `tsc --emitDeclarationOnly` pass) as long as the published `d.ts` files cover every component in D-04 and every type in D-05.
- Mechanics of `'use client'` directive emission under Vite library mode (header string banner, per-file, or package-level) — whatever survives Next.js 15 App Router bundling cleanly.
- How the CI smoke-test for React 18 vs 19 is wired (matrix job in GHA, two lockfiles, `npm install react@19 --no-save && vitest`, etc.) as long as the build passes under both.
- Tailwind v4 layer ordering and `@source` directive scoping for the library build so pre-compiled CSS covers every class actually used.
- Whether to ship a `package.json` `"exports"` map with `"./styles.css"` subpath or a flat import path — pick the form that Next.js 15 resolves without extra config.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Roadmap & requirements
- `.planning/ROADMAP.md` § Phase 5 — goal, success criteria (4 items), Depends on: Phase 4
- `.planning/REQUIREMENTS.md` (DSH-01) — "Extract viewer to shared dual-build npm package BEFORE any dashboard work"
- `.planning/PROJECT.md` § Key Decisions — "Extract viewer to shared dual-build package BEFORE any Next.js dashboard work" (gate rationale)
- `.planning/PROJECT.md` § Constraints — solo-founder ops minimization, bundle < 5 MB, Next.js 15 + uncached-by-default

### Viewer surfaces (what gets restructured)
- `viewer/package.json` — rename target (`@infracanvas/viewer`), add library build script, peer-dep widening, keep existing `postbuild` copy
- `viewer/vite.config.ts` — add second build target in library mode alongside existing `vite-plugin-singlefile` config
- `viewer/src/main.tsx` — CLI HTML entry; wraps `<App/>` with `<ViewerProvider store={defaultStore}>` after store refactor
- `viewer/src/App.tsx` — top-level composition; header tab control from Phase 4 (WRG-03) stays intact
- `viewer/src/store.ts` — refactor module singleton to `createViewerStore()` factory + default instance for CLI HTML
- `viewer/src/types.ts` — types re-exported from package root per D-05
- `viewer/src/components/*.tsx` (8 files) — exported per D-04
- `viewer/src/components/flowmap/*.tsx` (5 files) — exported per D-04
- `viewer/src/icons/*` + `aws-react-icons` dep — bundled internally, not re-exported (D-06)
- `viewer/src/__tests__/` — 79 Vitest tests that MUST still pass post-extraction (success criterion #4)

### CLI integration surfaces (must remain unchanged)
- `cli/infracanvas/export/html.py` — consumes `viewer_template.html` via string-replace of `window.__INFRACANVAS_DATA__ = null;`. Behavior must be byte-for-byte identical.
- `cli/infracanvas/export/viewer_template.html` — destination of `postbuild` copy; path preserved per D-03
- Bundle-size target: `< 5 MB` (current 3.5 MB baseline; PROJECT.md performance constraint)

### Prior-phase constraints (carry forward)
- `.planning/phases/04-e2e-wiring-hardening/04-CONTEXT.md` D-10..D-13 — Canvas ↔ FlowMap tab wiring (URL hash, keyboard shortcuts) lives in `App.tsx` / `store.ts`; must survive the store-factory refactor
- `.planning/phases/04-e2e-wiring-hardening/04-CONTEXT.md` D-14..D-17 — Python pytest coverage gate is CLI-side only; this phase does not touch those modules

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `viewer/vite.config.ts` already chains `@vitejs/plugin-react` + `@tailwindcss/vite` + `vite-plugin-singlefile`; adding a library-mode build target is a `build.lib` extension, not a rewrite.
- `viewer/package.json` already has a `postbuild` script copying to `cli/infracanvas/export/viewer_template.html` — the mechanism survives extraction verbatim.
- Zustand 5 supports store factories via `create(...)` returning independent stores — pairs naturally with a `<ViewerProvider>` Context; no library swap required.
- `@xyflow/react 12.6` exports client-only components and internally uses browser APIs (`ResizeObserver`, measured layout) — already aligns with the D-13 client-only decision.
- `viewer/src/__tests__/setup.ts` + jsdom environment in `vite.config.ts` `test` block — existing test infrastructure covers the component surface; tests will run against the factory/provider refactor with minimal shim.

### Established Patterns
- React 18 + TypeScript strict (`tsconfig.json` — strict, `noUnusedLocals`, `noUnusedParameters`, `isolatedModules`)
- 2-space indentation, no semicolons (TS/TSX), PascalCase components, camelCase hooks/utilities
- Tailwind v4 utility classes inline in JSX (no CSS Modules today)
- Zustand store via single `create<StoreState>(...)` call at module level; selectors via `useStore(s => s.foo)`
- Colocated tests under `viewer/src/__tests__/*.test.tsx`

### Integration Points
- **CLI HTML entry** — `viewer/src/main.tsx` renders `<StrictMode><App/></StrictMode>` into `#root`. Post-refactor it wraps with `<ViewerProvider store={createViewerStore(initialGraph)}>` so the singleton-style behavior is preserved for the single-file HTML.
- **Next.js dashboard (Phase 7)** — consumes `@infracanvas/viewer` via workspace link; imports `<DiagramCanvas>` / `<FlowMapCanvas>` inside a client component; imports `styles.css` once at the dashboard's root layout.
- **CLI template consumption** — `cli/infracanvas/export/html.py` reads `viewer_template.html` and replaces `window.__INFRACANVAS_DATA__ = null;` with the JSON graph. This contract is untouched by Phase 5.
- **Tab wiring from Phase 4** — `activeTab` state in `store.ts`, hash sync + keyboard shortcuts in `App.tsx`. The store factory refactor must preserve this exactly (regression-check via Phase 4's tab-wiring tests).

</code_context>

<specifics>
## Specific Ideas

- Two artifacts, one source tree — the dual-build ethos: `npm run build` emits both `dist/index.html` (CLI) and `dist/lib/` (ESM + CSS + d.ts). If either artifact breaks, both break — that is the point of extraction.
- CLI behavior must be **byte-for-byte identical** post-extraction: same single-file HTML, same `window.__INFRACANVAS_DATA__` injection, same bundle size envelope (< 5 MB, ~3.5 MB today). Regression-test the Phase 4 WRG-03 tab wiring end-to-end before declaring the phase done.
- React peer range `^18 || ^19` is load-bearing for Phase 7 being unblocked — if the package hard-pins React 18, Phase 7 inherits a React upgrade.
- `'use client'` directive at the library entry is load-bearing for Next.js 15 App Router to not try to SSR @xyflow/react.

</specifics>

<deferred>
## Deferred Ideas

- **Dark mode support** — not a Phase 5 concern; revisit during a dashboard UI polish phase.
- **CSS-variable theming / dashboard brand tokens** — deferred to the Phase 7 dashboard design phase once the visual language is locked.
- **Per-component CSS with tree-shaking** — reviewed, rejected in favor of the single `styles.css` import. Revisit only if measured bundle size becomes a problem.
- **Convert styles to CSS Modules / vanilla-extract** — reviewed, rejected. Would double the phase scope (3,150 LOC across 13 files) for an isolation benefit we don't need while Tailwind v4 is the only styling system in the repo.
- **Publish @infracanvas/viewer to npm (public or private)** — reviewed, rejected for Phase 5. Revisit only if the dashboard ever lives in a separate repo.
- **Upgrade viewer/CLI to React 19** — reviewed, rejected for Phase 5. Peer-dep range makes it possible without forcing the upgrade now.
- **`<Viewer>` convenience wrapper** that bundles TabBar + FilterPanel + DetailPanel internally — reviewed, rejected in favor of exposing the full component set (D-04) so the dashboard can re-layout without a package change.
- **Icon re-export for dashboard scan-history rows** — reviewed, deferred. Easy to add later if the dashboard needs matching AWS/Azure iconography outside the canvas.
- **Theme-override API / `useTheme` hook** — deferred with CSS-variable theming.

</deferred>

---

*Phase: 05-viewer-extraction*
*Context gathered: 2026-04-21*
