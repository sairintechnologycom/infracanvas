---
phase: 12
slug: path-asymmetric-routing
status: approved
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-17
revised: 2026-05-17
---

# Phase 12 — Validation Strategy

> Per-phase validation contract derived from PLAN files 12-01..12-07.
> All paths and commands mirror each plan's `<automated>` block verbatim.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend + cli), vitest 4.1 (viewer) |
| **Config file** | `backend/pyproject.toml`, `cli/pyproject.toml`, `viewer/vitest.config.ts` |
| **Quick run command** | `cd backend && pytest tests -x -q` |
| **Full suite command** | `cd backend && pytest -q && cd ../viewer && npx vitest run && cd ../cli && pytest -q` |
| **Estimated runtime** | ~120 seconds (full); ~15 seconds (quick scoped per task) |

---

## Sampling Rate

- **After every task commit:** Run the task's `<automated>` block (see per-task table below)
- **After every plan wave:** Run the full suite command above
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds (quick), 120 seconds (full)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 12-01-01 | 01 | 0 | PTH-01..03,ASY-01..03,NET-010,NFN-02 | T-12-01-01 / T-12-01-02 | Test scaffold + fixtures; collection-RED via pytest.importorskip | unit | `cd backend && pytest tests/security/pathcompute/ tests/jobs/test_path_compute_alerts.py tests/queue/test_path_compute_schedule.py tests/routes/test_paths_read.py tests/routes/test_paths_recompute.py tests/routes/test_agent_routes_persist.py tests/migrations/test_path_compute_rls.py tests/notifications/test_slack_dispatcher.py --collect-only -q` | ❌ W0 | ⬜ pending |
| 12-01-02 | 01 | 0 | NET-010, FMV-02 | — | cli + viewer scaffold (NET-010 detector stub + PathEdge/PathDetailPanel FMV-02 it.skip) | unit | `cd cli && pytest tests/test_net_010_detector.py --collect-only -q && cd ../viewer && npx vitest run src/__tests__/flowmap/PathEdge.test.tsx src/__tests__/flowmap/PathDetailPanel.test.tsx` | ❌ W0 | ⬜ pending |
| 12-02-01 | 02 | 1 | PTH-01..03,ASY-01..03 | T-12-02-* | migrations 012/013 land 5 tables with RLS ENABLE+FORCE, ORMs importable, FlowRecord pydantic-validated | integration | `cd backend && alembic upgrade head && pytest tests/migrations/test_path_compute_rls.py -q` | ❌ W0 | ⬜ pending |
| 12-02-02 | 02 | 1 | PTH-01..03 | T-12-02-* | agent push handlers persist routes/flows idempotent (snapshot_id) under team_id RLS | integration | `cd backend && pytest tests/routes/test_agent_routes_persist.py tests/test_agent.py tests/test_routes_firewall.py -q` | ❌ W0 | ⬜ pending |
| 12-03-01 | 03 | 2 | PTH-01..03,ASY-01..03 | — | NetworkPath/PathHop re-exported from cli (Pitfall 9); response schemas typed, MyPy strict | unit | `cd backend && python -c "from app.schemas.paths import NetworkPath, PathHop, PathsListItem, AsymmetryFindingResponse, PathDivergenceResponse, RecomputeResp" && ruff check app/schemas/paths.py && mypy --strict app/schemas/paths.py` | ❌ W0 | ⬜ pending |
| 12-03-02 | 03 | 2 | PTH-01..03,ASY-01..03 | T-12-03-* | GET /paths + /asymmetries + POST /paths/recompute behind Clerk JWT + site-membership 404-before-403; ImportError branch returns 503 (no silent fake job_id) | integration | `cd backend && pytest tests/routes/test_paths_read.py tests/routes/test_paths_recompute.py tests/test_routes_firewall_read.py -q` | ❌ W0 | ⬜ pending |
| 12-04-01 | 04 | 2 | NFN-02 | T-12-04-* | extracted send_team_slack helper in app/notifications/slack.py — redacted device names, retry+drop | unit | `cd backend && pytest tests/notifications/test_slack_dispatcher.py -q` | ❌ W0 | ⬜ pending |
| 12-04-02 | 04 | 2 | NFN-02 | — | scan_repo refactored to call shared helper (Phase 8 regression-safe) | integration | `cd backend && pytest tests/jobs/test_scan_repo.py tests/notifications/test_slack_dispatcher.py -q` | ❌ W0 | ⬜ pending |
| 12-05-01 | 05 | 2 | PTH-01..03,ASY-01..03 | — | 7 pure-compute modules (lpm/forward/pair/correlate/asymmetry/classify/impact) under app/security/pathcompute/; ECMP lex-lowest determinism (Pitfall 3); endpoint-only NetFlow correlation (Q2 v1.1) | unit | `cd backend && pytest tests/security/pathcompute/ -q` | ❌ W0 | ⬜ pending |
| 12-05-02 | 05 | 2 | NET-010 | — | cli/infracanvas/security/network/net_010.py Python detector emits findings with rule_id="NET-010", source="network"; YAML catalog count stays 51 (Q3/D-11) | unit | `cd cli && pytest tests/test_net_010_detector.py tests/test_flowmap_network_rules.py tests/test_security.py -q` | ❌ W0 | ⬜ pending |
| 12-06-01 | 06 | 3 | PTH-01..03,ASY-01..03 | T-12-06-* | path_compute taskiq job skeleton: cron */15 fan-out + module helpers + _leg_routes() helper + migration cause-enum extension admitting 'NET-010'; idempotent on snapshot tuple | integration | `cd backend && alembic upgrade head && pytest tests/queue/test_path_compute_schedule.py tests/security/pathcompute/ -q` | ❌ W0 | ⬜ pending |
| 12-06-02 | 06 | 3 | ASY-01..03, NET-010, NFN-02 | T-12-06-* | per-site body: classify() called via _leg_routes(fwd/ret) for cross-device BGP_LOCAL_PREF + ROUTE_LEAK; NET-010 findings persisted to asymmetry_findings with cause='NET-010'; flap suppression (detection_count >= 2, Pitfall 4) — 4-cycle test asserts exactly 1 alert; removes Plan 12-03's 503 placeholder | integration | `cd backend && pytest tests/jobs/test_path_compute_alerts.py tests/routes/test_paths_recompute.py tests/security/pathcompute/test_classify.py -q` | ❌ W0 | ⬜ pending |
| 12-07-01 | 07 | 4 | FMV-02 | — | PathEdge dual-strand red dashed when asymmetricForward/asymmetricReturn flags set | unit | `cd viewer && npx vitest run src/__tests__/flowmap/PathEdge.test.tsx` | ❌ W0 | ⬜ pending |
| 12-07-02 | 07 | 4 | FMV-02 | — | PathDetailPanel Asymmetry tab + AsymmetryPayload type on NetworkPath | unit | `cd viewer && npx vitest run src/__tests__/flowmap/PathDetailPanel.test.tsx` | ❌ W0 | ⬜ pending |
| 12-07-03 | 07 | 4 | FMV-02 | T-12-07-* | viewer/src/lib/asymmetryFetcher.ts + Zustand setAsymmetries action + FlowMapCanvas useEffect hydration + dashboard ViewerBootstrap installs window.__INFRACANVAS_BACKEND_FETCH__ | unit | `cd viewer && npx vitest run src/__tests__/flowmap/asymmetryFetcher.test.ts && cd ../dashboard && npm test -- --run __tests__/viewer-bootstrap.test.tsx` | ❌ W0 | ⬜ pending |
| 12-07-04 | 07 | 4 | PTH-01..03,ASY-01..03,FMV-02,NFN-02,NET-010 | T-12-07-* | smoke: full multi-suite GREEN; NET-010 visible in GET /asymmetries + viewer Asymmetry tab; NET-010 YAML reservation test GREEN; FMV-02 dual-strand red dashed PathEdge visible in browser | manual+integration | `cd backend && pytest -q && cd ../viewer && npx vitest run && cd ../cli && pytest -q && cd ../dashboard && npm test -- --run` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Wave 0 (Plan 12-01) is the fat scaffolding wave — it lands 21 backend test files + 5 `__init__.py` package markers + `cli/tests/test_net_010_detector.py` (4 stubs) + appends FMV-02 `it.skip` blocks to existing viewer test files. All stubs are collection-RED via `pytest.importorskip` or `pytest.skip()` so `pytest --collect-only` is clean. Downstream Wave 1+ plans each remove specific guards as they implement the real modules.

Concretely, Wave 0 creates:

**Backend (Plan 12-01 Task 1):**
- `backend/tests/security/pathcompute/__init__.py` + `conftest.py` (fixture helpers `mk_route_record`, `mk_flow`, `mk_path`, `mk_nat_rule`)
- `backend/tests/security/pathcompute/test_lpm.py`
- `backend/tests/security/pathcompute/test_forward.py`
- `backend/tests/security/pathcompute/test_pair.py`
- `backend/tests/security/pathcompute/test_correlate.py`
- `backend/tests/security/pathcompute/test_asymmetry.py`
- `backend/tests/security/pathcompute/test_classify.py`
- `backend/tests/security/pathcompute/test_impact.py`
- `backend/tests/security/pathcompute/test_reconcile.py`
- `backend/tests/jobs/test_path_compute_alerts.py`
- `backend/tests/queue/__init__.py` + `test_path_compute_schedule.py`
- `backend/tests/routes/__init__.py` + `test_paths_read.py` + `test_paths_recompute.py` + `test_agent_routes_persist.py`
- `backend/tests/migrations/__init__.py` + `test_path_compute_rls.py`
- `backend/tests/notifications/__init__.py` + `test_slack_dispatcher.py`

**CLI (Plan 12-01 Task 2):**
- `cli/tests/test_net_010_detector.py` (4 stubs)
- Touches `cli/tests/test_flowmap_network_rules.py` and `cli/tests/test_security.py` ONLY to confirm existing reservation tests stay GREEN (no edits per D-11 + Pitfall 6/7)

**Viewer (Plan 12-01 Task 2):**
- Appends FMV-02 `it.skip` blocks to existing `viewer/src/__tests__/flowmap/PathEdge.test.tsx` and `PathDetailPanel.test.tsx`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| FMV-02 divergence marker visible end-to-end in browser | FMV-02 | Visual QA against real fixture | Smoke checkpoint in 12-07 Task 3 step 5-9: open viewer with asymmetry-bearing fixture, confirm dual-strand red dashed PathEdge + Asymmetry tab populated from `/v1/sites/{id}/asymmetries` |
| NFN-02 Slack delivery to a real workspace | NFN-02 | Slack API delivery cannot be unit-tested without a workspace token | Smoke checkpoint in 12-07 Task 3 step 8: configure team Slack webhook in env; force route churn in lab; confirm Slack message arrives with redacted device names within 60s |
| End-to-end asymmetry detection on a lab topology | PTH-01..03,ASY-01..03 | Requires real BGP + NetFlow exporter | Smoke checkpoint in 12-07 Task 3 step 6-7: run DC agent against staging lab; trigger asymmetry by changing local-pref on one peer; confirm cron tick at next */15 surfaces a finding |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies (15 of 16 auto; row 12-07-03 chains both asymmetryFetcher.test.ts and viewer-bootstrap.test.tsx covering Plan 12-07 Tasks 3 and 3b; 12-07-04 is checkpoint:human-verify gating with multi-suite automated underneath)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify (every task has one)
- [x] Wave 0 covers all MISSING references (21 backend + 1 cli + 2 viewer test files explicitly created in Plan 12-01)
- [x] No watch-mode flags (`pytest -q`, `vitest run`, `--collect-only -q` — all single-run)
- [x] Feedback latency < 120s (full), 15s (quick per-task)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-05-17 (post-checker revision iteration 2 — Plan 12-06 split into 12-06-01/02; Plan 12-07 hydration task inserted as 12-07-03; smoke renumbered to 12-07-04; dashboard ViewerBootstrap added)
