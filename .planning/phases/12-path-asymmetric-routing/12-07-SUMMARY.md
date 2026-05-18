---
phase: 12
plan: 07
subsystem: viewer + dashboard
tags: [FMV-02, NFN-02, viewer, asymmetry, smoke-checkpoint]
dependency_graph:
  requires:
    - 12-01 (viewer it.skip stubs for PathEdge + PathDetailPanel)
    - 12-03 (GET /v1/sites/{id}/asymmetries read API)
    - 12-06 (path_compute job persisting AsymmetryFindings + NET-010 cause)
  provides:
    - "Viewer renders asymmetric edges with red dashed leg (FMV-02 visualization)"
    - "PathDetailPanel exposes Asymmetry tab with side-by-side hop table"
    - "asymmetryFetcher + setAsymmetries store hydration (Blocker 3 closed)"
    - "Dashboard ViewerBootstrap installs window.__INFRACANVAS_BACKEND_FETCH__ (Blocker 1 closed)"
  affects:
    - viewer/src/components/flowmap/edges/PathEdge.tsx
    - viewer/src/components/flowmap/PathDetailPanel.tsx
    - viewer/src/components/flowmap/FlowMapCanvas.tsx
    - viewer/src/store.ts
    - viewer/src/types.ts
    - dashboard/components/scans/ScanViewerClient.tsx
tech_stack:
  added:
    - "viewer/src/lib/asymmetryFetcher.ts (new module — fetches AsymmetryPayload[] via window-injected backendFetch)"
    - "dashboard/components/viewer/ViewerBootstrap.tsx (new component — installs window.__INFRACANVAS_BACKEND_FETCH__)"
  patterns:
    - "Hash-anchored conditional render (hasRoutes/hasCost/hasAsymmetry)"
    - "Window-injected callable as cross-bundle auth boundary"
    - "Zustand action-driven payload-to-entity merge (setAsymmetries by forward_path_id)"
key_files:
  created:
    - viewer/src/lib/asymmetryFetcher.ts
    - viewer/src/__tests__/flowmap/asymmetryFetcher.test.ts
    - dashboard/components/viewer/ViewerBootstrap.tsx
    - dashboard/__tests__/viewer-bootstrap.test.tsx
    - .planning/phases/12-path-asymmetric-routing/12-07-SUMMARY.md
  modified:
    - viewer/src/components/flowmap/edges/PathEdge.tsx
    - viewer/src/components/flowmap/PathDetailPanel.tsx
    - viewer/src/components/flowmap/FlowMapCanvas.tsx
    - viewer/src/store.ts
    - viewer/src/types.ts
    - viewer/src/__tests__/flowmap/PathEdge.test.tsx
    - viewer/src/__tests__/flowmap/PathDetailPanel.test.tsx
    - dashboard/components/scans/ScanViewerClient.tsx
decisions:
  - "AsymmetryPayload.cause kept as plain string (not enum) — wire-format stays loose-coupled with backend; viewer surface treats it as a label."
  - "ViewerBootstrap mounted at every ScanViewerClient return branch (loading / error / hydrated) so install runs at the same lifecycle moment regardless of state."
  - "site_id resolved from graph.metadata.site_id with fallback to graph.site_id; null fallback is a no-op fetch (offline-safe)."
  - "Test color assertions use rgb() form (jsdom normalizes hex stroke writes through React style prop to rgb())."
metrics:
  duration_seconds: ~900
  completed_at: 2026-05-18
---

# Phase 12 Plan 07: Viewer FMV-02 Asymmetric Routing Visualization — Summary

**One-liner:** Lands the viewer surface for FMV-02 — PathEdge dashed-red leg
override, PathDetailPanel Asymmetry tab with side-by-side hop table,
asymmetryFetcher + Zustand setAsymmetries hydration (Blocker 3), and the
dashboard's `window.__INFRACANVAS_BACKEND_FETCH__` install (Blocker 1).
Phase 12 backend pipeline is now observable end-to-end through the viewer.

## Status

**4/5 tasks complete. Awaiting human smoke checkpoint (Task 4) for Phase 12 closure.**

The 4 code tasks are committed atomically; the plan is `autonomous: false`
because the final task is a 12-step human-driven UAT that exercises the
complete Phase 12 pipeline (DB migration → agent push → 15-min compute →
NET-010 finding → Slack alert → viewer rendering). This SUMMARY documents
both the completed code and the awaiting-verification checkpoint state.

## Completed Tasks

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | PathEdge.tsx asymmetric leg styling + 3 it.skip → it() flips | `5281841` | viewer/src/components/flowmap/edges/PathEdge.tsx, viewer/src/__tests__/flowmap/PathEdge.test.tsx |
| 2 | PathDetailPanel Asymmetry tab + AsymmetryPayload type + 3 stubs flipped | `1850d8d` | viewer/src/types.ts, viewer/src/components/flowmap/PathDetailPanel.tsx, viewer/src/__tests__/flowmap/PathDetailPanel.test.tsx |
| 3 | asymmetryFetcher.ts + setAsymmetries store action + FlowMapCanvas hydration useEffect + 5 fetcher tests (Blocker 3 closed) | `2fceacd` | viewer/src/lib/asymmetryFetcher.ts, viewer/src/store.ts, viewer/src/components/flowmap/FlowMapCanvas.tsx, viewer/src/__tests__/flowmap/asymmetryFetcher.test.ts |
| 3b | dashboard ViewerBootstrap installs window.__INFRACANVAS_BACKEND_FETCH__ + 3 tests (Blocker 1 closed) | `89704af` | dashboard/components/viewer/ViewerBootstrap.tsx, dashboard/components/scans/ScanViewerClient.tsx, dashboard/__tests__/viewer-bootstrap.test.tsx |
| 4 | Smoke checkpoint — human UAT | **awaiting** | — |

## What Got Built

### Viewer

**`viewer/src/components/flowmap/edges/PathEdge.tsx`** — Extends the Phase 3
dual-strand renderer with `asymmetricForward` + `asymmetricReturn` data
props. When either flag is set, the matching strand renders with stroke
`#DC2626` (tailwind red-600) and `stroke-dasharray: 4 3`. When both flags
are falsy/absent, the existing Phase 3 dual-color (forward `#3B82F6`,
return `#F97316`) is preserved unchanged.

**`viewer/src/types.ts`** — New `AsymmetryPayload` interface mirroring the
Plan 12-03 `AsymmetryFindingResponse` wire shape (finding_id, cause,
cause_confidence, impact_bytes_per_sec, impact_firewall_count, evidence,
return_path, forward_path_id, return_path_id) plus a `NetworkPath.asymmetry?:
AsymmetryPayload` UI-only attachment.

**`viewer/src/components/flowmap/PathDetailPanel.tsx`** — Adds a conditional
"Asymmetry" tab gated by `hasAsymmetry = selectedPath !== null &&
selectedPath?.asymmetry !== undefined` (mirrors the existing
`hasRoutes`/`hasCost` pattern at lines 65-66). The new `AsymmetryTab`
sub-component renders cause + confidence + impact summary and a side-by-side
Forward/Return hop table; rows where `forward.hops[i].node_id !==
return.hops[i].node_id` get backgroundColor `rgba(127, 29, 29, 0.25)` (red
tint per PATTERNS.md) plus `data-mismatched="true"` for test targeting.
The `AlertTriangle` icon is added to the existing lucide-react imports.

**`viewer/src/store.ts`** — New `setAsymmetries(asymmetries:
AsymmetryPayload[])` action. Iterates `graph.network_paths`, indexes
incoming payloads by `forward_path_id`, and re-emits `network_paths` with
matching entries carrying `asymmetry: payload`. Synchronously rebinds
`selectedPath` if its id matches, so the Asymmetry tab + red dashed PathEdge
surface populated data without a re-render bounce.

**`viewer/src/lib/asymmetryFetcher.ts` (NEW)** — Exports
`fetchAsymmetries(siteId): Promise<AsymmetryPayload[]>`. Reads a callable
from `window.__INFRACANVAS_BACKEND_FETCH__` and uses it to GET
`/v1/sites/{siteId}/asymmetries`. Maps the wire response to
`AsymmetryPayload[]` preserving `forward_path_id` / `return_path_id` for
store matching. Returns `[]` when the injectable is absent (offline /
standalone bundle) or on network/auth error — viewer continues to render.
Never references or logs the Authorization header (T-12-07-07 mitigation).

**`viewer/src/components/flowmap/FlowMapCanvas.tsx`** — New
`useSetAsymmetries()` + `resolveSiteId(graph)` helpers, plus a hydration
`useEffect` that resolves `site_id` from `graph.metadata.site_id` or
`graph.site_id`, calls `fetchAsymmetries(siteId)`, and dispatches the
returned payloads via `setAsymmetries`. Guarded by `lastFetchedSiteIdRef`
to prevent redundant fetches; re-fetches when the user picks a new path
so newly-selected paths get hydrated.

### Dashboard

**`dashboard/components/viewer/ViewerBootstrap.tsx` (NEW)** — A `'use
client'` render-null component that runs a single `useEffect` on mount to
install `window.__INFRACANVAS_BACKEND_FETCH__ = backendFetch`, where
`backendFetch` is the dashboard's Clerk-JWT-authenticated helper from
`@/lib/backend`. The viewer's `asymmetryFetcher.ts:getInjectableFetch()`
reads that slot. T-12-07-07 is upheld at the `backendFetch` boundary;
this component only forwards the reference and never inspects headers.

**`dashboard/components/scans/ScanViewerClient.tsx`** — Mounts
`<ViewerBootstrap />` at every return branch (loading / error / hydrated)
so the install effect runs at the same lifecycle moment regardless of
which UI state the host is in. The bundled viewer's `FlowMapCanvas`
hydration `useEffect` only dispatches `fetchAsymmetries(siteId)` after
the graph hydrates, so the install always wins the race.

## Tests Added / Flipped

| File | Added | Flipped from it.skip | Status |
|------|-------|----------------------|--------|
| viewer/src/__tests__/flowmap/PathEdge.test.tsx | 0 | 3 | 7/7 GREEN |
| viewer/src/__tests__/flowmap/PathDetailPanel.test.tsx | 0 | 3 | 13/13 GREEN |
| viewer/src/__tests__/flowmap/asymmetryFetcher.test.ts | 5 | 0 | 5/5 GREEN |
| dashboard/__tests__/viewer-bootstrap.test.tsx | 3 | 0 | 3/3 GREEN |

**Full viewer suite:** 167 tests passing across 19 files; `tsc --noEmit`
clean.

**Full dashboard suite:** 209 prior tests + 3 new ViewerBootstrap =
212 passed. One pre-existing failure (`compare-layout.test.tsx` — unbuilt
`@infracanvas/viewer` package dist in worktree) and one pre-existing tsc
warning (`scan-filters.test.tsx` unused `screen` import) are out of scope
for this plan (Rule: scope boundary — pre-existing failures unrelated to
the current task are documented and deferred).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] Installed missing viewer + dashboard node_modules**
- **Found during:** Task 1 / Task 3b
- **Issue:** Test runner couldn't resolve `@testing-library/react` in either
  worktree (per-checkout `node_modules` not seeded by the worktree
  bootstrap).
- **Fix:** `npm install` in both `viewer/` and `dashboard/`.
- **Files modified:** `viewer/node_modules`, `dashboard/node_modules`
  (gitignored; no commit).
- **Commit:** N/A (transient runtime state).

**2. [Rule 1 — Bug] PathEdge tests used wrong selector for the stroke check**
- **Found during:** Task 1 verify step
- **Issue:** Initial test draft used `getAttribute('stroke')`, but jsdom
  normalizes hex stroke values that React writes through the `style` prop
  into an `style="stroke: rgb(R, G, B); ..."` attribute — there is no
  separate `stroke` attribute on the rendered `<path>`.
- **Fix:** Switched assertions to inspect the inline `style` attribute and
  introduced `RGB_DC2626` / `RGB_3B82F6` / `RGB_F97316` constants in the
  rgb() form. Also targeted `path[id$="-forward"]` / `path[id$="-return"]`
  instead of best-effort marker-end heuristics, since BaseEdge renders two
  paths per leg (visible + invisible interaction strip).
- **Files modified:** `viewer/src/__tests__/flowmap/PathEdge.test.tsx`
- **Commit:** Folded into `5281841`.

### Deferred Issues

**1. Pre-existing `dashboard/__tests__/compare-layout.test.tsx` failure**
- Cannot resolve `@infracanvas/viewer` package entry (no dist built in this
  worktree's viewer package). Unrelated to Plan 12-07 changes. Verified
  pre-existing via `git stash` + re-run on prior HEAD.

**2. Pre-existing `dashboard/__tests__/scan-filters.test.tsx` tsc warning**
- Unused `screen` import. TS6133. Unrelated to Plan 12-07 changes.
  Verified pre-existing via `git stash`.

## Self-Check: PASSED

- Created file `viewer/src/lib/asymmetryFetcher.ts` — FOUND
- Created file `viewer/src/__tests__/flowmap/asymmetryFetcher.test.ts` — FOUND
- Created file `dashboard/components/viewer/ViewerBootstrap.tsx` — FOUND
- Created file `dashboard/__tests__/viewer-bootstrap.test.tsx` — FOUND
- Modified files all present and tracked.
- All 4 task commits present in `git log --oneline`: 5281841, 1850d8d, 2fceacd, 89704af.

---

## CHECKPOINT STATE — Task 4 Smoke UAT (awaiting human operator)

Plan 12-07 is `autonomous: false`. The final task is a 12-step end-to-end
smoke verification of the entire Phase 12 pipeline (DB migration → agent
push → 15-min compute → NET-010 finding → Slack alert → viewer rendering).
This requires a live backend + DC agent + (optionally) Slack webhook and
cannot be performed by the executor. The orchestrator should present these
exact steps to the human operator:

### What the human needs to do (verbatim from PLAN.md `<how-to-verify>`)

1. **DB sanity** — `cd backend && alembic current` reports
   `013_path_compute_tables (head)` (Plan 12-06 edits migration 013 in
   place; no 014 migration exists). `psql ... -c "\dt" | grep -E
   'route_records|netflow_records|computed_paths|asymmetry_findings|path_divergence_findings'`
   returns all 5 tables.

2. **Agent push persistence (Blocker 1 closed)** — Configure DC agent
   against a fixture or staging lab. Push routes via POST
   `/v1/agent/routes`; SQL-probe `SELECT count(*) FROM route_records WHERE
   site_id=...` returns N > 0. Same for `/v1/agent/flows` →
   `netflow_records` (endpoint-only columns per Warning 4 — no
   `exporter_interface` yet).

3. **15-min cron fires** — Wait one quarter-hour (or trigger via `taskiq
   scheduler` direct invocation in dev). Check structlog output for
   `path_compute_complete` event with `site_id` + `pair_count > 0`.

4. **Read API returns paths** — Authenticate with Clerk JWT (use existing
   test credential or staging). `curl -H "Authorization: Bearer <jwt>"
   https://<env>/v1/sites/<site_id>/paths` returns JSON array of
   `PathsListItem` with hops populated.

5. **Read API returns asymmetries (if any)** — `curl ...
   /v1/sites/<site_id>/asymmetries` returns array (may be empty if lab
   symmetric). For deliberate asymmetry: introduce route divergence (e.g.,
   flip BGP local-pref on one peer); wait 30 min (2 cron cycles for
   Pitfall 4 flap suppression to clear); confirm finding appears in
   response with `cause` field set.

6. **NFN-02 Slack alert fires** — Configure `teams.slack_webhook_url` for
   the test team. After deliberate asymmetry introduced (step 5), confirm
   Slack channel receives the NFN_02_TEMPLATE message within 30 min (2
   cron cycles). Verify swallow behavior: temporarily set
   `slack_webhook_url` to unreachable URL; job log shows
   `path_compute.slack_alert_failed` + sentry breadcrumb but job exits
   cleanly.

7. **POST /paths/recompute coalesces** — `curl -X POST -H "Authorization:
   Bearer <owner-jwt>" .../sites/<site_id>/paths/recompute` twice within
   60s. First returns `coalesced: false` + `job_id`; second returns
   `coalesced: true` + different `job_id`.

8. **Viewer FMV-02 dual-strand renders** — Open the dashboard against the
   staging asymmetric pair. Load the FlowMap view. Confirm the asymmetric
   edge renders with a red dashed stroke on the divergent leg (visually
   distinct from the blue+orange solid Phase 3 default). The dashboard
   ViewerBootstrap (Task 3b) installs `window.__INFRACANVAS_BACKEND_FETCH__`
   automatically on mount; the Task 3b vitest already proves the install
   — no manual install step is required here.

9. **Viewer PathDetailPanel Asymmetry tab** — Click the asymmetric path
   edge. Confirm the detail panel shows an Asymmetry tab (alongside
   Overview/Findings/Attributes). Click it. Confirm side-by-side
   Forward/Return hop table renders; row(s) where forward node differs
   from return node have a red tint background. (The fetcher +
   `setAsymmetries` store action from Task 3 populates
   `selectedPath.asymmetry` on mount + selectedPath change.)

10. **NET-010 finding emitted AND surfaced (Warning 6)** — In the
    deliberate-asymmetry lab setup with a stateful firewall on one leg
    only, confirm BOTH:
    - **Backend:** `curl -H "Authorization: Bearer <jwt>"
      .../v1/sites/<site_id>/asymmetries` includes at least one row with
      `"cause": "NET-010"` and `"cause_confidence": 1.0` (Plan 12-06
      persistence + Plan 12-03 surface).
    - **Viewer:** Click the same asymmetric path → Asymmetry tab shows the
      NET-010 finding in the cause line (e.g., "Cause: NET-010 (100%)")
      and/or a NET-010-flagged stateful firewall appears in the hop table
      side.
    - The prior "NET-010 appears in scan output" (CLI) expectation is
      dropped per D-01 (server-side persistence only; CLI integration is
      a future enhancement).

11. **YAML catalog regression** — `cd cli && pytest
    tests/test_flowmap_network_rules.py::TestNetworkRulesYAML::test_net_010_reserved_for_phase_3b
    -q` is GREEN (reservation test stays valid; D-11 contract holds —
    NET-010 stays OUT of YAML catalog).

12. **Full test suite GREEN** — `cd backend && pytest -q && cd ../viewer
    && npx vitest run && cd ../cli && pytest -q` — all suites pass.

### Resume Signal

Operator types one of:
- **`approved`** — all 12 checks pass; Phase 12 fully closes.
- **`approved-with-flags <comma-separated step IDs>`** — most checks pass
  but specific items deferred (e.g., `approved-with-flags 5,6` means
  steps 5 and 6 deferred to a follow-up because lab not available).
- **`blocked <reason>`** — a check failed in a way that requires a code
  fix; operator describes what failed.
