---
status: pending
phase: 12-path-asymmetric-routing
source:
  - 12-01-SUMMARY.md
  - 12-02-SUMMARY.md
  - 12-03-SUMMARY.md
  - 12-04-SUMMARY.md
  - 12-05-SUMMARY.md
  - 12-06-SUMMARY.md
  - 12-07-SUMMARY.md
started: 2026-05-18T08:30:00Z
updated: 2026-05-18T08:30:00Z
---

## Current Test

[awaiting human operator]

## Resume signal (when done)

Reply with one of:
- **approved** — all 12 checks pass; Phase 12 fully closes
- **approved-with-flags <ids>** — most checks pass but specific items deferred (e.g., `approved-with-flags 2,3,5,6,10` if lab not available)
- **blocked <reason>** — a check failed in a way that requires a code fix; describe what failed

## Tests

### 1. DB sanity — migrations 012 + 013 land cleanly
expected: `cd backend && alembic current` reports `013_path_compute_tables (head)`. `psql ... -c "\dt" | grep -E 'route_records|netflow_records|computed_paths|asymmetry_findings|path_divergence_findings'` returns all 5 tables. asymmetry_findings.cause CHECK admits BGP_LOCAL_PREF, ROUTE_LEAK, NAT_ASYMMETRY, UNKNOWN, AND NET-010 (Plan 12-06 extension).
result: pending

### 2. Agent push persistence — routes + flows land under RLS
expected: Configure DC agent against a fixture or staging lab. Push routes via POST /v1/agent/routes; `SELECT count(*) FROM route_records WHERE site_id=...` returns N > 0. Same for /v1/agent/flows → netflow_records (endpoint-only columns per Warning 4 — no exporter_interface yet; deferred to v1.2). Cross-team RLS isolation: another team's JWT cannot read these rows (404, not 403).
result: pending

### 3. 15-min cron fires
expected: Wait one quarter-hour (or trigger via `taskiq scheduler` direct invocation in dev). Check structlog output for `path_compute_complete` event with `site_id` + `pair_count > 0`. Pattern G allowlist holds — no raw paths or evidence in log payload.
result: pending

### 4. Read API GET /paths returns computed paths
expected: Authenticate with Clerk JWT (test credential or staging). `curl -H "Authorization: Bearer <jwt>" https://<env>/v1/sites/<site_id>/paths` returns JSON array of PathsListItem with hops populated. Cross-team site_id resolves to 404 (Pattern C site-membership probe). RLS GUC `set_config('app.current_team_id', :t, true)` runs BEFORE SELECT.
result: pending

### 5. Read API GET /asymmetries surfaces findings (with deliberate asymmetry)
expected: `curl ... /v1/sites/<site_id>/asymmetries` returns array (may be empty if lab is symmetric). For deliberate asymmetry: introduce route divergence (e.g., flip BGP local-pref on one peer); wait 30 min (2 cron cycles for flap suppression); confirm finding appears with `cause` set (BGP_LOCAL_PREF / ROUTE_LEAK / NAT_ASYMMETRY / UNKNOWN / NET-010).
result: pending

### 6. NFN-02 Slack alert fires + failure swallow
expected: Configure `teams.slack_webhook_url` for the test team. After deliberate asymmetry from step 5, Slack channel receives NFN_02_TEMPLATE message within 30 min (2 cron cycles). Swallow behavior: set slack_webhook_url to an unreachable URL → job log shows `path_compute.slack_alert_failed` + sentry breadcrumb, job exits cleanly (no exception propagation).
result: pending

### 7. POST /paths/recompute coalesces on-demand calls
expected: `curl -X POST -H "Authorization: Bearer <owner-jwt>" .../sites/<site_id>/paths/recompute` twice within 60s. First returns `coalesced: false` + job_id. Second returns `coalesced: true` + different job_id. Owner-role gated (non-owner JWT → 403).
result: pending

### 8. Viewer FMV-02 — PathEdge renders red dashed leg
expected: Open the dashboard against the staging asymmetric pair. Load FlowMap view. Asymmetric edge renders with red dashed stroke (#DC2626, dasharray "4 3") on the divergent leg — visually distinct from blue+orange solid Phase 3 default. ViewerBootstrap auto-installs `window.__INFRACANVAS_BACKEND_FETCH__` on mount (no manual install needed).
result: pending

### 9. Viewer FMV-02 — PathDetailPanel Asymmetry tab
expected: Click the asymmetric path edge. Detail panel shows Asymmetry tab alongside Overview/Findings/Attributes. Click it. Side-by-side Forward/Return hop table renders. Rows where forward node differs from return node have red tint background (#7F1D1D40). The fetcher + setAsymmetries store action populates `selectedPath.asymmetry` on mount + selectedPath change.
result: pending

### 10. NET-010 finding emitted AND surfaced (Warning 6 — backend + viewer)
expected: In deliberate-asymmetry lab with a stateful firewall on one leg only, BOTH:
- **Backend:** `curl -H "Authorization: Bearer <jwt>" .../v1/sites/<site_id>/asymmetries` includes ≥1 row with `"cause": "NET-010"` and `"cause_confidence": 1.0` (Plan 12-06 persistence + Plan 12-03 surface).
- **Viewer:** Click same asymmetric path → Asymmetry tab shows NET-010 finding in cause line (e.g., "Cause: NET-010 (100%)") and/or a NET-010-flagged stateful firewall appears in hop table.
- (Prior expectation "NET-010 appears in CLI scan output" is dropped per D-01.)
result: pending

### 11. YAML catalog regression
expected: `cd cli && pytest tests/test_flowmap_network_rules.py::TestNetworkRulesYAML::test_net_010_reserved_for_phase_3b -q` is GREEN. Reservation contract holds — NET-010 stays OUT of YAML catalog per D-11.
result: pending

### 12. Full test suite GREEN
expected: `cd backend && pytest -q && cd ../viewer && npx vitest run && cd ../cli && pytest -q` — all 3 suites pass. Phase 8 scan_repo regression tests GREEN after Plan 12-04 Slack extraction. Phase 3 + Phase 11 viewer tests GREEN after Plan 12-07 PathEdge / PathDetailPanel extensions.
result: pending
