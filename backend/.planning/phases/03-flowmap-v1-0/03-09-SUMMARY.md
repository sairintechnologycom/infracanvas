---
phase: 03-flowmap-v1-0
plan: 09
gap_closure: true
status: complete
completed: 2026-04-19
---

# 03-09 SUMMARY — Rebundle viewer_template.html + install drift guards

## What was broken

Phase 3 UAT (2026-04-19) found that `infracanvas scan` was serving a stale
Apr-18 Phase-2 viewer bundle even though every Phase 3 viewer source component
(TabBar, FlowMapCanvas, FlowMapFilterPanel, PathDetailPanel, FlowMapEmptyState)
had already landed in `viewer/src/`.

Root cause: no automated sync from `viewer/dist/index.html` into
`cli/infracanvas/export/viewer_template.html`. The CLI template was last copied
in by hand during Phase 2 and never refreshed. UAT tests 8–13 failed because
the shipped HTML contained zero `FlowMap` / `BETA` / `activeTab` tokens.

## What was fixed

**Task 1 — one-time rebundle** (commit `69f1ed6`)

Ran `npm run build` in `viewer/` and copied the resulting `dist/index.html`
into `cli/infracanvas/export/viewer_template.html`. The file grew from the
stale ~2 MB Phase-2 bundle to a fresh 3.5 MB Phase-3 bundle. Post-copy grep
confirmed all four required tokens are present: `FlowMap` (3), `BETA` (1),
`No network topology collected yet` (1), `activeTab` (2).

**Task 2 — postbuild sync hook** (commit `8d98e71`)

Added `"postbuild": "cp dist/index.html ../cli/infracanvas/export/viewer_template.html"`
to `viewer/package.json`. npm runs any `postX` script automatically after `X`,
so every future `npm run build` now re-syncs the bundle into the CLI package
with zero manual steps. Proven end-to-end with a sentinel test: injected a
marker into the CLI template, ran `npm run build`, confirmed the marker was
gone (postbuild overwrote it with the fresh bundle).

**Task 3 — pytest regression guard** (commit `e5ca3c5`)

Created `cli/tests/test_viewer_template_bundle.py` with three tests:

- `test_viewer_template_contains_flowmap_tokens` — asserts all four Phase 3
  UI tokens are present in the bundled template.
- `test_viewer_template_placeholder_intact` — asserts the
  `window.__INFRACANVAS_DATA__ = null;` placeholder (replaced by `html.py` at
  export time) still exists.
- `test_viewer_template_not_trivially_small` — asserts file size ≥ 1 MB so a
  future sync that copied an empty or error page would fail CI.

Verified the guard is collected by the default `pytest cli/tests/` invocation
(threat T-03-09-02 mitigation) and that moving the template away causes a
descriptive failure.

## What prevents recurrence

- **Automatic:** `viewer/package.json` postbuild hook copies the bundle on
  every `npm run build`. The bundled CLI template can no longer silently drift
  from `viewer/src` HEAD unless someone bypasses `npm run build` entirely.
- **Detective:** The pytest guard fails CI the moment the bundled template
  drifts, is truncated, or loses the data-injection placeholder. Three
  independent assertions cover the three most likely regression modes.

## UAT status

- UAT tests 8–13 (FlowMap UI reachable through `infracanvas scan`) — **unblocked**.
  End-to-end verification:
  `infracanvas scan tests/fixtures/simple_vpc --output /tmp/uat-3-gap-closed.html`
  produces HTML containing all four FlowMap tokens.
- UAT tests 5–6 (Azure VWAN collector — live API) — remain third-party blocked
  (no Azure tenant access). Out of scope for this gap closure.

## Test results

- `pytest cli/tests/test_viewer_template_bundle.py -q` → 3 passed
- `pytest cli/tests/ -q` → 271 passed (no regressions elsewhere)

## Commits

| SHA | Type | Description |
|-----|------|-------------|
| `69f1ed6` | fix | rebundle viewer_template.html with Phase 3 FlowMap UI |
| `8d98e71` | build | add postbuild hook to sync viewer bundle into CLI template |
| `e5ca3c5` | test | add regression guard for bundled viewer_template.html |

## Key files

**Created:**
- `cli/tests/test_viewer_template_bundle.py` — regression guard (3 tests)

**Modified:**
- `cli/infracanvas/export/viewer_template.html` — refreshed to Phase 3 bundle
- `viewer/package.json` — added postbuild sync hook
