---
phase: 05-viewer-extraction
plan: 03
subsystem: viewer
tags: [viewer, build-verification, ci-matrix, cli-integration, react-peer-compat]

# Dependency graph
dependency_graph:
  requires:
    - "05-01 (dual-build scaffolding — vite.config.app.ts + vite.config.lib.ts + tsconfig.lib.json + lib-styles.css + @infracanvas/viewer package + root workspaces)"
    - "05-02 (viewer/src/index.ts barrel + store factory + ViewerProvider — vite.config.lib.ts entry resolves)"
  provides:
    - "Proven end-to-end dual build: single-file HTML (3,559,123 B) + library ESM (2,580,607 B) + .d.ts (1,197 B) + library CSS (16,039 B)"
    - "CLI viewer_template.html post-extraction (byte-for-byte sync'd with viewer/dist/index.html; CLI contract preserved — window.__INFRACANVAS_DATA__ placeholder-replace works end-to-end)"
    - ".github/workflows/viewer-peer-compat.yml — React 18/19 matrix CI with T-05-01/T-05-02 artifact assertions per push"
    - "lib-styles.css @source inline() directives emit theme-token utility classes (bg-sev-critical, text-canvas-bg, etc.) so Phase 7 consumers can reference them by class name"
  affects:
    - "Phase 7 (SaaS dashboard) — can now `import { DiagramCanvas, FlowMapCanvas, ... } from '@infracanvas/viewer'` + `import '@infracanvas/viewer/styles.css'`; Next.js 15 RSC directive present (`'use client'` normalized to `\"use client\";` at line 1 of dist/lib/index.js)"
    - "CLI HTML export (`infracanvas scan ... --format html`) now consumes the extracted template; no behavior change but proven via smoke test"
    - "Future Vite/Rollup upgrades that change banner quoting style will NOT break CI (matrix assertion accepts both quote forms)"

# Tech tracking
tech-stack:
  added:
    - "(No new dependencies — Plan 03 is verification + CI only)"
  patterns:
    - "Tailwind v4 @source inline() for consumer-facing library CSS — force-emit utility classes by name without requiring a component file to reference them (works around JIT stripping theme tokens used only by downstream consumers)"
    - "Rollup ESM directive canonicalization: a source banner `'use client'` is re-emitted as `\"use client\";` — semantically identical Next.js RSC marker; CI assertion must accept either quote style for future-proofing"
    - "GHA matrix with --legacy-peer-deps for React version swap: npm ci installs default peers, then per-job `npm install react@X --legacy-peer-deps` re-pins to matrix version without fighting npm 10 strict peer resolution"
    - "Command-injection-safe workflow input: matrix values passed via `env:REACT_VERSION` rather than direct `${{ matrix.react-version }}` interpolation in shell (defensive even though matrix literals are workflow-trusted)"

key-files:
  created:
    - ".github/workflows/viewer-peer-compat.yml"
  modified:
    - "viewer/src/lib-styles.css (added @source inline() directives for theme-token utilities)"
    - "cli/infracanvas/export/viewer_template.html (post-build sync from viewer/dist/index.html — 3,557,199 → 3,559,123 B)"
  generated_not_committed:
    - "viewer/dist/index.html (3,559,123 B)"
    - "viewer/dist/lib/index.js (2,580,607 B)"
    - "viewer/dist/lib/index.d.ts (1,197 B)"
    - "viewer/dist/lib/styles.css (16,039 B)"
    - "viewer/dist/lib/index.css (15,849 B — lib-build-time React-component-scoped CSS, separate from @source inline library styles.css)"

decisions:
  - "Use `insecure_setup` fixture for CLI end-to-end smoke (plan specified `s3-critical` which does not exist in the fixture tree; `insecure_setup` contains 7 resources exercising S3/IAM/SG/RDS/KMS rules — a richer end-to-end smoke than a single-resource fixture)"
  - "Accept both `'use client'` (source banner) and `\"use client\";` (Rollup's canonical ESM directive form) in assertions. Rollup normalizes bare-string banners into canonical ESM directives with semicolon terminator. Both forms are valid Next.js RSC markers; asserting only the source form would fail CI without semantic benefit."
  - "Force-emit theme-token utilities via `@source inline(\"{bg,text,border}-...\")`. The Plan 01 @theme tokens (sev-critical, canvas-bg, etc.) were designed for Phase 7 consumers to reference as classes, but no current viewer/src file uses them (components use hex inline styles). Without @source inline(), Tailwind JIT strips the tokens from the shipped styles.css."

metrics:
  duration_min: ~20
  tasks_completed: 2  # Task 2 is verification-only, no atomic commit
  tasks_verified: 3
  files_changed: 3  # lib-styles.css, viewer_template.html (post-build), viewer-peer-compat.yml
  completed_date: "2026-04-21"

requirements:
  - DSH-01
requirements_completed: [DSH-01]
---

# Phase 05 Plan 03: End-to-End Dual Build + CI Matrix + CLI Contract Verification Summary

Executed the first end-to-end dual build of `@infracanvas/viewer`, validated all nine artifact contracts (size, banner, path leakage, declarations, CSS theme tokens, CLI template sync, placeholder preservation, peer-dep externalization, non-empty styles), ran the Python CLI HTML export smoke end-to-end on the extracted template, confirmed the Vitest baseline is unchanged, and shipped the React 18/19 peer-compat CI matrix — closing all four DSH-01 success criteria for Phase 5.

## Artifact Sizes (exact byte counts)

| Artifact                                       | Pre-phase      | Post-phase     | Delta       | Constraint         |
| ---------------------------------------------- | -------------- | -------------- | ----------- | ------------------ |
| `viewer/dist/index.html` (CLI single-file)     | 3,557,199 B    | 3,559,123 B    | **+1,924 B** | < 5,000,000 B ✓    |
| `cli/infracanvas/export/viewer_template.html`  | 3,557,199 B    | 3,559,123 B    | **+1,924 B** | cmp-equal to dist ✓ |
| `viewer/dist/lib/index.js`                     | N/A            | 2,580,607 B    | new         | External React ✓   |
| `viewer/dist/lib/index.d.ts`                   | N/A            |     1,197 B    | new         | DiagramCanvas ✓    |
| `viewer/dist/lib/styles.css`                   | N/A            |    16,039 B    | new         | Theme tokens ✓     |

**HTML delta rationale:** +1,924 B against the plan's "≤ 200 KB" target is well under budget. The Plan 02 `ViewerProvider` wrap around `<App />` and the `viewer/src/index.ts` barrel (imported transitively) add ~2 KB of React Context boilerplate — the exact expected order-of-magnitude.

## Task Commits

| Task | Description                                         | Commit    | Files                                                                              |
| ---- | --------------------------------------------------- | --------- | ---------------------------------------------------------------------------------- |
| 1    | Full dual-build + 9 artifact assertions + CLI sync  | `5390226` | `viewer/src/lib-styles.css`, `cli/infracanvas/export/viewer_template.html`         |
| 2    | CLI end-to-end HTML smoke + Vitest regression gate  | _no-op_   | (verification-only; plan spec: "no file modifications — verification only")        |
| 3    | React 18/19 peer-compat CI matrix workflow          | `792e314` | `.github/workflows/viewer-peer-compat.yml`                                         |

Task 2 intentionally has no commit — the `<files>` spec in `05-03-PLAN.md` declares "no file modifications — verification only". Its results are captured under **Task 2 Outcomes** below.

## Task 1 Outcome — Build + Assertions

All nine build-artifact assertions green:

1. `viewer/dist/index.html` exists and 3,559,123 B < 5,000,000 B (PROJECT.md bundle constraint) ✓
2. `viewer/dist/lib/index.js` exists (2,580,607 B) ✓
3. **T-05-01 mitigation** — Line 1 of `dist/lib/index.js` is `"use client";` (Rollup's canonical ESM directive form; equivalent to source `'use client'`) ✓
4. **T-05-02 mitigation** — No `/viewer/src/` substring in `dist/lib/index.js` (no private absolute-path leakage) ✓
5. **Peer externalization** — `dist/lib/index.js` contains `from "react"`, `from "react-dom"`, `from "react/jsx-runtime"`, `from "@xyflow/react"`, `from "zustand"`, `from "lucide-react"`, `from "aws-react-icons"` — all externalized; no inlined React internals ✓
6. `viewer/dist/lib/index.d.ts` exists; exports `DiagramCanvas`, `FlowMapCanvas`, `createViewerStore`, `ViewerProvider`, and all 15 types from `./types` ✓
7. `viewer/dist/lib/styles.css` non-empty (16,039 B) and contains the theme-token utility classes `sev-critical`, `canvas-bg`, `card-bg`, `flow-forward` — after Rule 1 fix ✓
8. `cli/infracanvas/export/viewer_template.html` is `cmp`-equal to `viewer/dist/index.html` (postbuild `cp` ran) ✓
9. `cli/infracanvas/export/viewer_template.html` contains the literal string `window.__INFRACANVAS_DATA__ = null;` (CLI Python string-replace contract preserved) ✓

## Task 2 Outcome — CLI End-to-End + Vitest

**Python CLI HTML export end-to-end:**

- Fixture used: `cli/tests/fixtures/insecure_setup/` (plan specified `s3-critical/`; substituted — `s3-critical` does not exist in the fixture tree; `insecure_setup` has 7 resources exercising 5 security categories).
- Command: `infracanvas scan cli/tests/fixtures/insecure_setup --format html --output /tmp/infracanvas-p5/scan.html`
- Output: `/tmp/infracanvas-p5/scan.html` written, 3,568,479 B (slightly larger than template due to injected graph JSON).
- Placeholder `window.__INFRACANVAS_DATA__ = null;` GONE in output ✓
- Replacement form `window.__INFRACANVAS_DATA__ = {...}` present (graph JSON injected) ✓
- `window.__INFRACANVAS_GATE__ = true;` present (gate_mode=True default) ✓

**End-to-end CLI contract holds:** the Python string-replace consumes the extracted template and produces a valid scan report. DSH-01 success criterion #2 proven.

**Vitest suite — no regressions vs. pre-phase baseline:**

```
Test Files  3 failed | 14 passed (17)
Tests       6 failed | 130 passed (136)
Duration    6.03s
```

This is **byte-identical** to the pre-phase baseline (documented in 05-RESEARCH.md § Validation and confirmed in 05-02-SUMMARY.md). The 6 pre-existing failures are all in `src/__tests__/flowmap/PathEdge.test.tsx` (2 tests) and 4 other path-rendering tests surfaced by the project's Vitest baseline — none introduced by Plans 01–03. DSH-01 success criterion #4 proven.

## Task 3 Outcome — CI Matrix Workflow

Workflow `.github/workflows/viewer-peer-compat.yml` committed. Characteristics:

- **Triggers:** push to `main` + pull_request to `main`, path-scoped to `viewer/**`, root `package.json`, and the workflow file itself (keeps feedback fast for CLI-only changes).
- **Matrix:** `react-version: ['18', '19']`, `fail-fast: false` (both legs run to completion; a React 19 break surfaces separately from a React 18 break).
- **React version swap:** `npm ci` at repo root (uses Plan 01's workspaces), then per-job `npm install react@$REACT_VERSION ... --legacy-peer-deps` scoped to `working-directory: viewer`.
- **Command-injection defense:** matrix value flows through `env: REACT_VERSION: ${{ matrix.react-version }}` + shell `"${REACT_VERSION}"` interpolation, avoiding the `${{ matrix.* }}`-in-shell antipattern (defensive — matrix values are workflow-literal `'18'` / `'19'`, but consistent with the command-injection hardening guidance for GHA).
- **Pre-test artifact assertions (run BEFORE tests so banner/size/path issues surface with clear error messages):**
  1. `'use client'` / `"use client";` banner at line 1 (regex accepts either quote form)
  2. No `/viewer/src/` substring (T-05-02 per-push gate)
  3. `dist/index.html` < 5,000,000 B (PROJECT.md performance constraint)
- **Test step:** `npm test -- --run` (Vitest run mode, same command `ci.yml` uses for `test-viewer`).

YAML parses cleanly (validated via `yaml.safe_load`).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `lib-styles.css` @theme tokens were not emitted to `dist/lib/styles.css`**

- **Found during:** Task 1 assertion 7 (styles.css theme tokens check)
- **Issue:** The `@theme { --color-sev-critical: ...; --color-canvas-bg: ...; ... }` block in `viewer/src/lib-styles.css` defined 13 custom CSS variables, but none of them appeared in the generated `dist/lib/styles.css`. Reason: Tailwind v4 JIT only emits utility classes that are actually USED by scanned source files (`@source "./App.tsx"`, `@source "./components"`). The components in `viewer/src/components/**` use hex inline styles (`#ef4444`, `#FAFBFC`, etc. — 15 occurrences across 6 files) rather than Tailwind classes like `bg-sev-critical` or `text-canvas-bg`. Result: the theme tokens were defined-but-unused from the JIT scanner's perspective and stripped from the shipped CSS.
- **Why this is a bug:** The whole point of the library CSS is to let Phase 7 consumers (Next.js dashboard) import `@infracanvas/viewer/styles.css` and reference theme tokens by class name for a consistent visual language across CLI and dashboard. Without these tokens in the output, the dashboard would render with a different color palette than the CLI viewer.
- **Fix:** Added `@source inline("{bg,text,border}-{canvas-bg,card-bg,card-border,card-hover}")`, `@source inline("{bg,text,border}-sev-{critical,high,medium,info,clean}")`, and `@source inline("{bg,text,border}-flow-{forward,return,divergence}")` directives to `lib-styles.css`. Tailwind v4's `@source inline(...)` force-emits named utility classes regardless of JIT scan detection.
- **Verification:** Post-fix `dist/lib/styles.css` grew from 13,796 B → 16,039 B and now contains `sev-critical`, `canvas-bg`, `card-bg`, `flow-forward` (and all their sibling tokens).
- **Files modified:** `viewer/src/lib-styles.css`
- **Commit:** `5390226` (bundled with the Task 1 build + artifact sync)

**2. [Rule 1 - Bug, minor] 'use client' banner assertion regex was too strict**

- **Found during:** Task 1 assertion 3 (banner check)
- **Issue:** The plan's assertion `head -1 dist/lib/index.js | grep -q "^'use client'"` requires single-quoted bare-string form. Reality: Rollup re-emits the source banner `'use client'\n` (from `vite.config.lib.ts` `rollupOptions.output.banner`) as the canonical ESM directive `"use client";` (double-quoted, semicolon-terminated). Both forms are valid Next.js RSC directives; the double-quoted form is the canonical Rollup output for ES modules.
- **Why this is a bug:** Asserting only one quote style would fail CI without any semantic benefit. A future Rollup version might flip the convention again; making the assertion quote-agnostic is future-proof.
- **Fix:** Adjusted assertion regex to `^['\"]use client['\"];?` (accepts either quote, optional semicolon). Applied in Task 1 verification AND in Task 3's GHA workflow so CI uses the same future-proof check.
- **Files modified:** `.github/workflows/viewer-peer-compat.yml` (assertion regex)
- **Commit:** `792e314` (bundled with Task 3)

### Deviation from Plan's Specified Fixture

**Task 2 fixture substitution** (not a bug, plan-sanctioned fallback):

- Plan specified: `cli/tests/fixtures/s3-critical/`
- Reality: `s3-critical/` does not exist in the fixture tree. Available: `azure/`, `clean_infra/`, `demo_infra/`, `empty_blocks/`, `flowmap/`, `insecure_setup/`, `large/`, `malformed/`, `multi_module/`, `policies/`, `prod_infra/`, `rules/`, `simple_vpc/`, `single_resource/`.
- Substituted: `insecure_setup/` — richest small fixture (7 resources, 21 findings across 5 security categories). Exercises the CLI template injection on a real-world-shaped input.
- Per plan instruction: "If `s3-critical` doesn't exist, substitute the first available fixture and document the substitution in the summary."

## Authentication Gates

None — plan executed fully autonomously.

## Python CLI Environment Note

The worktree doesn't have its own Python venv; verification was run via the main-repo venv at `/Users/bhushan/Documents/Projects/Infracanvas/cli/.venv/bin/python` + the `infracanvas` console script. This does not affect the CLI contract verification — `export_html()` reads the extracted template from the worktree's `cli/infracanvas/export/viewer_template.html` (the one we just postbuild-synced), proving the extracted template is byte-compatible with the Python CLI's string-replace logic.

## Phase 5 Success Criteria Closure

All four ROADMAP Phase 5 success criteria proven:

1. ✓ `@infracanvas/viewer` package builds both single-file HTML AND React component library (Task 1 — all 9 assertions green).
2. ✓ CLI HTML export uses the package; bundle < 5 MB (Task 1 artifact sync + Task 2 end-to-end smoke).
3. ✓ Next.js-ready: `DiagramCanvas` / `FlowMapCanvas` exported with `.d.ts` (9 components), CSS subpath export via `./styles.css`, `"use client";` ESM directive at line 1 (Task 1, asserted in CI Task 3).
4. ✓ Viewer tests pass at pre-phase baseline — 130 passing / 6 pre-existing failures, delta zero (Task 2).

Plus threat-model assertions:

- **T-05-01** `'use client'` directive: asserted at build-time (Task 1) AND in CI per-push (Task 3).
- **T-05-02** path leakage: asserted at build-time (Task 1) AND in CI per-push (Task 3).
- **T-05-03** runtime-Tailwind DoS: structurally prevented (lib build uses `@tailwindcss/cli` — pre-compiled `styles.css`; no runtime Tailwind reaches the consumer; Rule 1 `@source inline()` fix ensures tokens are in the pre-compiled output).
- **T-05-06** CLI template stale: asserted via `cmp` in Task 1; CI runs `npm run build` which includes `postbuild` sync.
- **T-05-07** React 19 silent break: mitigated by matrix CI with `fail-fast: false` + `--legacy-peer-deps` + three pre-test artifact assertions.

## Manual Verification Recommended

The following human smoke checks are **not blocking** but useful before Phase 5 merge to main:

1. Open `/tmp/infracanvas-p5/scan.html` in a modern browser. Expect: Canvas renders with 7 resource nodes (S3, SG, RDS, EC2, KMS, IAM). Tabs should show only "Canvas" (no FlowMap data in `insecure_setup` fixture). Click a resource → DetailPanel opens with findings. Toggle filters. Press `Cmd+\` — should be no-op since FlowMap tab is disabled.
2. Open `viewer/dist/index.html` directly in a browser (no CLI data injected — the placeholder remains `null`). Expect: the viewer gracefully handles a null `__INFRACANVAS_DATA__` (empty-state or sample-data fallback per existing behavior). This verifies the CLI template is standalone-openable for debugging.
3. (Future Phase 7 verification, not this plan.) In a Next.js 15 RSC context, `import { DiagramCanvas } from '@infracanvas/viewer'` and `import '@infracanvas/viewer/styles.css'`. The `"use client";` directive at line 1 of `dist/lib/index.js` should make the whole module tree client-bounded without a per-file directive.

These are documented in `05-VALIDATION.md` § Manual-Only Verifications.

## Self-Check: PASSED

- FOUND: `viewer/dist/index.html` (3,559,123 B — < 5 MB)
- FOUND: `viewer/dist/lib/index.js` (2,580,607 B, line 1 = `"use client";`)
- FOUND: `viewer/dist/lib/index.d.ts` (1,197 B, exports DiagramCanvas + 12 more components + 15 types + store API)
- FOUND: `viewer/dist/lib/styles.css` (16,039 B, contains sev-critical / canvas-bg / card-bg / flow-forward theme tokens)
- FOUND: `cli/infracanvas/export/viewer_template.html` (3,559,123 B — cmp-equal to dist/index.html; contains `window.__INFRACANVAS_DATA__ = null;` placeholder)
- FOUND: `.github/workflows/viewer-peer-compat.yml` (YAML valid; matrix ['18','19']; all 3 pre-test assertions; --legacy-peer-deps; working-directory: viewer; fail-fast: false)
- FOUND: `/tmp/infracanvas-p5/scan.html` (CLI-injected real graph JSON; placeholder replaced)
- FOUND commit: `5390226` (Task 1 — build + CLI sync + Rule 1 lib-styles fix)
- FOUND commit: `792e314` (Task 3 — peer-compat workflow)
- Task 2: verification-only per plan spec; no atomic commit expected.
- `git log --oneline HEAD~2..HEAD` shows both commits landed.

---
*Phase: 05-viewer-extraction*
*Completed: 2026-04-21*
