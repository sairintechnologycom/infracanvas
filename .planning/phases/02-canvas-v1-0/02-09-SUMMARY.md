---
id: 02-09
phase: 02-canvas-v1-0
title: Inline web fonts — close UAT gap (offline self-containment)
kind: gap_closure
status: complete
outcome: gap_closed
closes:
  - .planning/phases/02-canvas-v1-0/02-UAT.md (test 9)
  - .planning/phases/02-canvas-v1-0/02-UAT-e2e.md (test 7)
executed: 2026-04-18
commits:
  - 9925474 chore(viewer): add @fontsource/inter + @fontsource/jetbrains-mono
  - 309bc1c fix(viewer): inline JetBrains Mono + Inter via @fontsource — no CDN fetch
---

# Phase 02 Plan 09: Inline Web Fonts Summary

Closed the Phase 2 UAT offline-integrity gap by replacing the Google Fonts `@import` in the viewer with `@fontsource/inter` + `@fontsource/jetbrains-mono` npm packages, letting `vite-plugin-singlefile` inline the woff2 files as base64 inside the bundled HTML. Exported reports now perform zero CDN fetches on load.

## Outcome

**Gap closed.** Exported `report.html` no longer fetches `fonts.googleapis.com` or `fonts.gstatic.com`. Fonts are bundled as base64 woff2 via `vite-plugin-singlefile` and rendered entirely offline. Phase 1 success criterion ("opens in any browser with zero dependencies") now satisfied.

## Files Changed

### Created / added
- `viewer/node_modules/@fontsource/inter/**` (dependency install; not tracked)
- `viewer/node_modules/@fontsource/jetbrains-mono/**` (dependency install; not tracked)

### Modified
- `viewer/package.json` — added `@fontsource/inter` ^5.2.8 and `@fontsource/jetbrains-mono` ^5.2.8 under `dependencies`.
- `viewer/package-lock.json` — regenerated for the two new packages.
- `viewer/src/main.tsx` — added 7 side-effect CSS imports (Inter 400/500/600/700 + JetBrains Mono 400/500/600) before `./index.css`.
- `viewer/index.html` — removed the `<style>@import url('https://fonts.googleapis.com/...')</style>` block (previously lines 7–9).
- `cli/infracanvas/export/viewer_template.html` — synced from freshly built `viewer/dist/index.html` (2,069,895 bytes).
- `.planning/phases/02-canvas-v1-0/02-UAT.md` — test 9 flipped to `result: pass`; Summary updated to 9/9; Gaps zeroed.
- `.planning/phases/02-canvas-v1-0/02-UAT-e2e.md` — test 7 flipped to `result: pass`; Summary updated to 7/7; Gaps zeroed.

## Verification (T-06)

Regenerated a fresh report from source CLI (cli/.venv editable install) against `cli/tests/fixtures/insecure_setup/`:

```
$ CI=1 /Users/bhushan/Documents/Projects/Infracanvas/cli/.venv/bin/infracanvas scan \
    /Users/bhushan/Documents/Projects/Infracanvas/cli/tests/fixtures/insecure_setup/ \
    --output /tmp/verify/report.html
```

| Check                                                 | Required  | Actual                | Pass |
| ----------------------------------------------------- | --------- | --------------------- | ---- |
| `grep -cE 'fonts\.googleapis\.com\|fonts\.gstatic\.com' report.html` | `= 0`     | **0**                 | yes  |
| `stat -f%z report.html` (bytes)                       | `< 5242880` | **2,081,117** (~1.98MB) | yes  |
| `grep -c "@font-face" report.html`                    | `> 0`     | **1 line** (minified; 46 occurrences via `grep -o`) | yes  |

Additional sanity: `grep -oE "font-family:[^;}]{1,40}" report.html | sort -u` confirms `font-family:Inter` and `font-family:JetBrains Mono` are both declared in the inlined CSS.

Previous (pre-fix) baseline from 02-UAT-e2e test 7: 1 match on `fonts.googleapis.com`, report.html = 469KB. Delta: +~1.6MB (as expected — 7 weight-subset families × Inter/JetBrains Mono × multiple unicode-range splits).

## Deviations From Plan

**1. [Rule 3 — Blocking issue] Ran source CLI via `cli/.venv/bin/infracanvas`, not Homebrew binary, for T-06.**
- **Found during:** Task T-06.
- **Issue:** The plan's verification command uses `infracanvas` which on this machine resolves to the Homebrew-installed 0.1.0 binary — that package has its own pre-baked `viewer_template.html` from a previous release and would not reflect our freshly synced template.
- **Fix:** Used the editable-install venv at `cli/.venv/bin/infracanvas` (which resolves `infracanvas` from the working copy and therefore reads the just-updated `cli/infracanvas/export/viewer_template.html`). The plan already anticipated this fallback ("Reinstall if using Homebrew build — otherwise run the source CLI directly").
- **Files modified:** none — runtime-only decision.
- **Commit:** n/a (operational, not a code change).

**2. [Process] Added an extra prep commit (`9925474`) for T-01 dependency install in addition to the T-08 unified commit.**
- **Reason:** GSD executor protocol advises atomic per-task commits. T-01 only touched `package.json` / `package-lock.json` (metadata) and was cleanly separable. The plan's T-08 message still accurately covers the substantive code change (viewer/index.html, viewer/src/main.tsx, viewer_template.html, UAT docs). Two commits total on the branch close this plan.
- **Impact:** None. `git revert 309bc1c` still restores the Google Fonts `@import`; if a full rollback is wanted, `git revert 309bc1c 9925474` removes the dep as well.

## Tasks Executed

| Task | Description | Status |
| ---- | ----------- | ------ |
| T-01 | `npm install --save @fontsource/inter @fontsource/jetbrains-mono` | done (commit 9925474) |
| T-02 | Added 7 font CSS imports to `viewer/src/main.tsx` | done |
| T-03 | Removed Google Fonts `<style>@import>` block from `viewer/index.html` | done |
| T-04 | Verified `assetsInlineLimit: 100000000` already present in `vite.config.ts:10` | done (no change needed) |
| T-05 | `npm run build` + copied `viewer/dist/index.html` → `cli/infracanvas/export/viewer_template.html` | done (2,069,895 bytes) |
| T-06 | Regenerated report, ran the three verification checks | done (0 / 2,081,117 / 46) |
| T-07 | Marked 02-UAT test 9 and 02-UAT-e2e test 7 as pass; zeroed Gaps sections | done |
| T-08 | Final commit with plan's verbatim message | done (commit 309bc1c) |

## Commits

- **9925474** — `chore(viewer): add @fontsource/inter + @fontsource/jetbrains-mono`
- **309bc1c** — `fix(viewer): inline JetBrains Mono + Inter via @fontsource — no CDN fetch`

## Rollback

`git revert 309bc1c` restores the Google Fonts `@import` and reverts the UAT docs. `git revert 9925474` additionally removes the npm dependencies. Bundle size would drop to ~469KB but the CDN fetch would return.

## Self-Check: PASSED

- File `viewer/package.json` exists with `@fontsource/inter` and `@fontsource/jetbrains-mono` under dependencies. FOUND.
- File `viewer/src/main.tsx` contains 7 `@fontsource/*` imports. FOUND.
- File `viewer/index.html` no longer contains `@import url('https://fonts.googleapis.com/...')`. VERIFIED (grep after edit: 0 matches).
- File `cli/infracanvas/export/viewer_template.html` updated (2,069,895 bytes, matches current `viewer/dist/index.html`). FOUND.
- Commit `9925474` present in `git log`. FOUND.
- Commit `309bc1c` present in `git log`. FOUND.
- `/tmp/verify/report.html` passes all three verification checks (0 CDN matches, 2.08MB < 5MB, 46 `@font-face` occurrences). VERIFIED.
- UAT docs `02-UAT.md` (test 9) and `02-UAT-e2e.md` (test 7) both show `result: pass` with `closed_by: 02-09-PLAN.md`. VERIFIED.
