---
phase: 5
slug: viewer-extraction
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-21
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Full details in `05-RESEARCH.md § Validation Architecture`.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Vitest 4.1.4 (existing) |
| **Config file** | `viewer/vite.config.app.ts` (in `test` block — split from current `vite.config.ts`) |
| **Quick run command** | `cd viewer && npm test` |
| **Full suite command** | `cd viewer && npm run build && npm test` |
| **Estimated runtime** | ~30 seconds (test); ~40 seconds (build+test) |

---

## Sampling Rate

- **After every task commit:** Run `cd viewer && npm test`
- **After every plan wave:** Run `cd viewer && npm run build && npm test` plus build-artifact assertions
- **Before `/gsd-verify-work`:** Full suite green + build assertions + React 18/19 matrix green
- **Max feedback latency:** 40 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 05-XX-XX | — | 0 | DSH-01 | — | N/A | scaffold | `test -f viewer/vite.config.app.ts && test -f viewer/vite.config.lib.ts` | ❌ W0 | ⬜ pending |
| 05-XX-XX | — | 0 | DSH-01 | — | N/A | scaffold | `test -f viewer/tsconfig.lib.json` | ❌ W0 | ⬜ pending |
| 05-XX-XX | — | 0 | DSH-01 | — | N/A | scaffold | `test -f viewer/src/index.ts` | ❌ W0 | ⬜ pending |
| 05-XX-XX | — | 0 | DSH-01 | — | N/A | scaffold | `test -f viewer/src/lib-styles.css` | ❌ W0 | ⬜ pending |
| 05-XX-XX | — | 0 | DSH-01 | — | N/A | scaffold | `test -f package.json && grep -q '"workspaces"' package.json` | ❌ W0 | ⬜ pending |
| 05-XX-XX | — | 1 | DSH-01 | — | CLI HTML byte-for-byte preserved | build smoke | `ls viewer/dist/index.html` | ❌ W0 | ⬜ pending |
| 05-XX-XX | — | 1 | DSH-01 | — | CLI HTML < 5 MB | build gate | `[ $(wc -c < viewer/dist/index.html) -lt 5000000 ]` | ❌ W0 | ⬜ pending |
| 05-XX-XX | — | 1 | DSH-01 | T-05-01 | `'use client'` preserved in library entry | build assertion | `head -1 viewer/dist/lib/index.js \| grep -q "use client"` | ❌ W0 | ⬜ pending |
| 05-XX-XX | — | 1 | DSH-01 | — | Library ESM entry exists | build smoke | `test -f viewer/dist/lib/index.js` | ❌ W0 | ⬜ pending |
| 05-XX-XX | — | 1 | DSH-01 | — | Pre-compiled CSS non-empty | build smoke | `test -s viewer/dist/lib/styles.css` | ❌ W0 | ⬜ pending |
| 05-XX-XX | — | 1 | DSH-01 | — | TypeScript declarations emitted | type check | `test -f viewer/dist/lib/index.d.ts` | ❌ W0 | ⬜ pending |
| 05-XX-XX | — | 1 | DSH-01 | — | 130 existing Vitest tests still pass (6 pre-existing failures excluded) | unit | `cd viewer && npm test` | ✅ | ⬜ pending |
| 05-XX-XX | — | 2 | DSH-01 | — | React 18 peer compat | matrix CI | GHA matrix — React 18 job green | ❌ W0 | ⬜ pending |
| 05-XX-XX | — | 2 | DSH-01 | — | React 19 peer compat | matrix CI | GHA matrix — React 19 job green | ❌ W0 | ⬜ pending |
| 05-XX-XX | — | 2 | DSH-01 | T-05-02 | Bundle does not expose private paths | build gate | `grep -L "/viewer/src/" viewer/dist/lib/index.js` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*
*Task IDs fill in once PLAN.md files are written — placeholders above mirror the DSH-01 coverage matrix from RESEARCH.md § Validation Architecture.*

---

## Wave 0 Requirements

- [ ] `viewer/vite.config.app.ts` — app build config (split from current `vite.config.ts`; preserves `vite-plugin-singlefile`)
- [ ] `viewer/vite.config.lib.ts` — library build config (`build.lib` + `output.banner: "'use client';"`)
- [ ] `viewer/tsconfig.lib.json` — separate TS config with `noEmit: false` for declaration emit via `vite-plugin-dts`
- [ ] `viewer/src/index.ts` — library entry point re-exporting D-04 components and D-05 types
- [ ] `viewer/src/lib-styles.css` — Tailwind CSS entry with `@import "tailwindcss" source(none)` + explicit `@source` scoping to `viewer/src/`
- [ ] `package.json` (root) — npm workspaces declaration listing `["viewer"]`
- [ ] `.github/workflows/viewer-peer-compat.yml` — React 18/19 matrix CI
- [ ] devDeps: `vite-plugin-dts@^4.5.4`, `@tailwindcss/cli` (pinned to `@tailwindcss/vite` major)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| CLI HTML tab wiring (Phase 4 WRG-03) survives store factory refactor | DSH-01 | URL hash + keyboard shortcut integration spans store+App+browser; existing Vitest coverage asserts store mutations but cannot assert browser-side hash/keyboard wiring end-to-end | Run `python -m infracanvas scan cli/tests/fixtures/s3-critical --format html --output /tmp/canvas.html && open /tmp/canvas.html` → toggle tabs via click, URL hash (`#flowmap`), and `1`/`2` keyboard shortcut; verify all three mutate `activeTab` and persist across reload |
| Dashboard import smoke (Phase 7 prep) | DSH-01 | Phase 5 does not ship a dashboard; validate resolvability with an ad-hoc `npm ls @infracanvas/viewer` from a sibling workspace member created transiently | Create `dashboard-smoke/package.json` with `"dependencies": {"@infracanvas/viewer": "*"}`, run `npm install` at repo root, then `node -e "import('@infracanvas/viewer').then(m => console.log(Object.keys(m)))"` — expect component names from D-04 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (8 items above)
- [ ] No watch-mode flags (`--watch`, `test:watch`) anywhere in verify commands
- [ ] Feedback latency < 40s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
