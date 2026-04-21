# Phase 5: Viewer Extraction - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-21
**Phase:** 05-viewer-extraction
**Areas discussed:** Package layout, Export surface, Styling strategy, Store & React version

---

## Area selection

| Option | Description | Selected |
|--------|-------------|----------|
| Package layout | Repo organization to produce both builds | ✓ |
| Export surface | Public API — components, types, icons, CSS entry | ✓ |
| Styling strategy | Tailwind v4 delivery, theming, dark mode | ✓ |
| Store & React version | Zustand store pattern + React peer range + SSR | ✓ |

**User's choice:** All four areas selected.

---

## Area 1 — Package layout

### Q1: How should the repo be physically organized for Phase 5?

| Option | Description | Selected |
|--------|-------------|----------|
| Stay in `viewer/`, add lib build (Recommended) | Extend vite.config.ts with library build target alongside singlefile | ✓ |
| Split into `packages/` workspace | npm workspaces: packages/viewer + packages/viewer-html | |
| Sibling `packages/viewer-core` | viewer/ becomes a thin app consuming viewer-core | |
| Let Claude decide after research | Research first, pick after | |

**User's choice:** Stay in viewer/, add lib build (Recommended).

### Q2: Publish to npm or workspace-internal?

| Option | Description | Selected |
|--------|-------------|----------|
| Workspace-internal only (Recommended) | No npm publish; dashboard consumes via workspace link | ✓ |
| Publish @infracanvas/viewer to npm public | Public package, versioning + changelog discipline | |
| Publish to npm private registry | GitHub Packages or private scope | |
| Decide at Phase 7 time | Defer the publishing question | |

**User's choice:** Workspace-internal only (Recommended).

### Q3: How should the CLI pick up the built single-file HTML?

| Option | Description | Selected |
|--------|-------------|----------|
| Keep postbuild copy to cli/ (Recommended) | Preserve current `cp dist/index.html ../cli/...` script | ✓ |
| CLI reads from node_modules at build time | CI step copies dist into Python sdist before release | |
| Python package downloads HTML from GitHub release | Decouple Python + JS release cadence; adds runtime network dep | |

**User's choice:** Keep postbuild copy to cli/ (Recommended).

---

## Area 2 — Export surface

### Q1: Which components should the package export?

| Option | Description | Selected |
|--------|-------------|----------|
| Full component set (Recommended) | All 13 canvas + chrome components | ✓ |
| Two canvases + `<Viewer>` wrapper | Pre-composed convenience wrapper | |
| Just canvases, dashboard rebuilds chrome | Dashboard builds its own TabBar/FilterPanel/DetailPanel | |

**User's choice:** Full component set (Recommended).

### Q2: Should types be part of the public export?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, export all types from types.ts (Recommended) | ResourceGraph, Finding, NetworkPath, etc. re-exported | ✓ |
| Export only runtime-used types | Only prop-accepted types; helpers stay package-private | |
| No types, structural interop | Consumer defines its own types | |

**User's choice:** Yes, export all types from types.ts (Recommended).

### Q3: Are icons part of the public API?

| Option | Description | Selected |
|--------|-------------|----------|
| Bundled internally, not re-exported (Recommended) | Icons stay inside the package | ✓ |
| Re-export the custom icon set | Dashboard can render matching icons outside the canvas | |
| Claude's Discretion | Decide based on dashboard needs later | |

**User's choice:** Bundled internally, not re-exported (Recommended).

### Q4: Single CSS file or multiple entry points?

| Option | Description | Selected |
|--------|-------------|----------|
| Single `@infracanvas/viewer/styles.css` (Recommended) | One CSS import covers everything | ✓ |
| Per-component CSS with tree-shaking | Smaller CSS, more complex bundler setup | |
| Claude's Discretion | Pick during styling-strategy area | |

**User's choice:** Single `@infracanvas/viewer/styles.css` (Recommended).

---

## Area 3 — Styling strategy

### Q1: How should Tailwind CSS be delivered?

| Option | Description | Selected |
|--------|-------------|----------|
| Pre-compiled CSS bundled (Recommended) | Tailwind runs at package build; consumer imports one CSS file | ✓ |
| Ship Tailwind source, consumer configures | Consumer adds package path to tailwind content config | |
| Convert to CSS modules / vanilla-extract | Drop Tailwind; refactor 3,150 LOC | |

**User's choice:** Pre-compiled CSS bundled (Recommended).

### Q2: Theme tokens — fixed or overridable?

| Option | Description | Selected |
|--------|-------------|----------|
| Fixed tokens for Phase 5 (Recommended) | Current severity/zone colors baked in | ✓ |
| Expose CSS custom properties for theming | Dashboard overrides per its brand | |

**User's choice:** Fixed tokens for Phase 5 (Recommended).

### Q3: Dark mode — change or stay as today?

| Option | Description | Selected |
|--------|-------------|----------|
| Keep exactly as today (Recommended) | No dark-mode scope in Phase 5 | ✓ |
| Add dark mode in scope | Scope creep; deferred to later phase | |

**User's choice:** Keep exactly as today (Recommended).

---

## Area 4 — Store & React version

### Q1: How should the Zustand store work in Next.js?

| Option | Description | Selected |
|--------|-------------|----------|
| createStore() factory + <ViewerProvider> (Recommended) | Per-mount store via React Context; default singleton for CLI HTML | ✓ |
| Keep module singleton, document caveats | Reset on page mount via useEffect; risks SSR bugs | |
| Per-component local state | Props + callbacks only; invalidates 79 tests | |

**User's choice:** createStore() factory + <ViewerProvider> (Recommended).

### Q2: Which React versions as peer deps?

| Option | Description | Selected |
|--------|-------------|----------|
| React 18 || 19 peer range (Recommended) | Support both; CI smoke-tests both | ✓ |
| React 18 only | Pin to ^18; forces dashboard to React 18 | |
| React 19 only, upgrade viewer now | Layers a React upgrade on an extraction phase | |

**User's choice:** React 18 || 19 peer range (Recommended).

### Q3: SSR or client-only?

| Option | Description | Selected |
|--------|-------------|----------|
| Client-only with 'use client' directive (Recommended) | Mark package entry; dashboard wraps in Suspense | ✓ |
| Attempt SSR with ssr-safe guards | typeof window guards; hydration mismatch risk | |

**User's choice:** Client-only with 'use client' directive (Recommended).

---

## Claude's Discretion

Captured in CONTEXT.md `<decisions>` section:
- Exact Vite library-mode config (`build.lib` entry, formats, externals, rollup options)
- Whether to introduce a root `npm workspaces` declaration vs. `file:` reference
- TypeScript declaration-generation approach (`vite-plugin-dts` vs. separate `tsc` pass)
- `'use client'` directive emission mechanics under Vite library mode
- CI wiring for the React 18 vs 19 smoke-test
- Tailwind v4 `@source` scoping for pre-compiled CSS
- `package.json` `exports` map shape for the CSS subpath

## Deferred Ideas

Captured in CONTEXT.md `<deferred>` section:
- Dark mode support
- CSS-variable theming / dashboard brand tokens
- Per-component CSS with tree-shaking
- Convert styles to CSS Modules / vanilla-extract
- Publish @infracanvas/viewer to npm (public or private)
- Upgrade viewer/CLI to React 19
- `<Viewer>` convenience wrapper
- Icon re-export for dashboard scan-history rows
- Theme-override API / `useTheme` hook
