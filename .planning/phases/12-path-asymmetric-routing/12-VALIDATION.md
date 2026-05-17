---
phase: 12
slug: path-asymmetric-routing
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-17
---

# Phase 12 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: derived from `12-RESEARCH.md` §Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend), vitest 4.1 (viewer), go test (agent) |
| **Config file** | `backend/pyproject.toml`, `viewer/vitest.config.ts`, `agent/go.mod` |
| **Quick run command** | `cd backend && pytest tests/unit -x -q` |
| **Full suite command** | `cd backend && pytest && cd ../viewer && npm test -- --run && cd ../agent && go test ./...` |
| **Estimated runtime** | ~90 seconds (full); ~10 seconds (quick) |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && pytest tests/unit -x -q` (or the matching viewer/agent quick command for that task's file scope)
- **After every plan wave:** Run the full suite command above
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds (quick), 90 seconds (full)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 12-01-01 | 01 | 0 | — | — | Test scaffold present | unit | `cd backend && pytest tests/unit/test_phase12_scaffold.py -q` | ❌ W0 | ⬜ pending |
| 12-02-01 | 02 | 1 | PTH-01,PTH-02,PTH-03 | T-12-01 | route_records RLS on team_id | unit | `cd backend && pytest tests/unit/test_route_records_model.py -q` | ❌ W0 | ⬜ pending |
| 12-02-02 | 02 | 1 | PTH-03 | T-12-01 | netflow_records RLS on team_id | unit | `cd backend && pytest tests/unit/test_netflow_records_model.py -q` | ❌ W0 | ⬜ pending |
| 12-02-03 | 02 | 1 | PTH-01..03 | T-12-02 | agent push handler persists routes idempotent on snapshot_id | integration | `cd backend && pytest tests/integration/test_agent_route_push.py -q` | ❌ W0 | ⬜ pending |
| 12-02-04 | 02 | 1 | PTH-03 | T-12-02 | agent push handler persists flows idempotent | integration | `cd backend && pytest tests/integration/test_agent_flow_push.py -q` | ❌ W0 | ⬜ pending |
| 12-02-05 | 02 | 1 | — | T-12-03 | retention prune job drops snapshots > 7d | unit | `cd backend && pytest tests/unit/test_route_flow_prune.py -q` | ❌ W0 | ⬜ pending |
| 12-03-01 | 03 | 2 | PTH-01 | — | forward-path compute LPM correct on canonical fixture | unit | `cd backend && pytest tests/unit/test_path_compute_forward.py -q` | ❌ W0 | ⬜ pending |
| 12-03-02 | 03 | 2 | PTH-02 | — | return-path compute LPM correct on canonical fixture | unit | `cd backend && pytest tests/unit/test_path_compute_return.py -q` | ❌ W0 | ⬜ pending |
| 12-03-03 | 03 | 2 | PTH-01,02 | — | ECMP resolved deterministically (lex-lowest) | unit | `cd backend && pytest tests/unit/test_path_compute_ecmp.py -q` | ❌ W0 | ⬜ pending |
| 12-03-04 | 03 | 2 | PTH-03 | — | NetFlow correlation flags divergence | unit | `cd backend && pytest tests/unit/test_netflow_correlation.py -q` | ❌ W0 | ⬜ pending |
| 12-04-01 | 04 | 3 | ASY-01 | — | asymmetry detector flags forward≠return | unit | `cd backend && pytest tests/unit/test_asymmetry_detector.py -q` | ❌ W0 | ⬜ pending |
| 12-04-02 | 04 | 3 | ASY-02 | — | classifier emits BGP_LOCAL_PREF on fixture | unit | `cd backend && pytest tests/unit/test_asymmetry_classifier_local_pref.py -q` | ❌ W0 | ⬜ pending |
| 12-04-03 | 04 | 3 | ASY-02 | — | classifier emits ROUTE_LEAK on AS-path fixture | unit | `cd backend && pytest tests/unit/test_asymmetry_classifier_route_leak.py -q` | ❌ W0 | ⬜ pending |
| 12-04-04 | 04 | 3 | ASY-02 | — | classifier emits NAT_ASYMMETRY when NAT signal present | unit | `cd backend && pytest tests/unit/test_asymmetry_classifier_nat.py -q` | ❌ W0 | ⬜ pending |
| 12-04-05 | 04 | 3 | ASY-03 | — | impact scoring assigns affected_flow_count + asymmetric_firewall_set | unit | `cd backend && pytest tests/unit/test_asymmetry_impact.py -q` | ❌ W0 | ⬜ pending |
| 12-04-06 | 04 | 3 | NET-010 | — | NET-010 detector emits finding with rule_id="NET-010" | unit | `cd backend && pytest tests/unit/test_net_010_detector.py -q` | ❌ W0 | ⬜ pending |
| 12-04-07 | 04 | 3 | — | T-12-04 | classifier evidence values redacted in serialized output | unit | `cd backend && pytest tests/unit/test_classifier_redaction.py -q` | ❌ W0 | ⬜ pending |
| 12-05-01 | 05 | 3 | PTH-01..03,ASY-01..03 | T-12-05 | compute job idempotent on same snapshot tuple | integration | `cd backend && pytest tests/integration/test_path_compute_job.py -q` | ❌ W0 | ⬜ pending |
| 12-05-02 | 05 | 3 | NFN-02 | T-12-06 | route-change alert dispatched on churn delta | integration | `cd backend && pytest tests/integration/test_route_change_alert.py -q` | ❌ W0 | ⬜ pending |
| 12-05-03 | 05 | 4 | — | — | taskiq 15-min cron schedule wired | integration | `cd backend && pytest tests/integration/test_path_compute_schedule.py -q` | ❌ W0 | ⬜ pending |
| 12-06-01 | 06 | 4 | FMV-02 | — | PathEdge renders divergence marker on asymmetry payload | unit | `cd viewer && npm test -- --run src/components/PathEdge.test.tsx` | ❌ W0 | ⬜ pending |
| 12-06-02 | 06 | 4 | FMV-02 | — | FlowMap reads asymmetry from store and toggles overlay | unit | `cd viewer && npm test -- --run src/components/FlowMap.test.tsx` | ❌ W0 | ⬜ pending |
| 12-07-01 | 07 | 4 | NFN-02 | T-12-06 | Slack dispatcher extracted to app/notifications/slack.py and reused | unit | `cd backend && pytest tests/unit/test_slack_dispatcher.py -q` | ❌ W0 | ⬜ pending |
| 12-07-02 | 07 | 4 | NFN-02 | — | route-change alert payload formatted with redacted device names | unit | `cd backend && pytest tests/unit/test_route_change_alert_payload.py -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/unit/test_phase12_scaffold.py` — pytest skeleton + fixture registration
- [ ] `backend/tests/fixtures/routing/` — canonical RIB + NetFlow + AS-path + NAT fixtures (JSON)
- [ ] `backend/tests/fixtures/conftest.py` — shared fixture helpers `load_rib()`, `load_netflow()`, `make_snapshot_id()`
- [ ] `backend/tests/integration/conftest.py` — DB session + team_id GUC fixture for RLS testing (verify Phase 11 helpers reusable; extend only if needed)
- [ ] All 24 per-task test files above — stub form (function defined, body `pytest.skip("Wave N task pending")`) — created in Wave 0 so the planner agent sees them when picking up Wave 1+

*Wave 0 is intentionally fat: 24 test stubs + fixture scaffolding. Per Nyquist this is mandatory — every later task either turns a red stub green or fails the sampling rate gate.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| FMV-02 divergence marker is visually distinguishable (color contrast, hover affordance) | FMV-02 | Visual QA cannot be automated to design-language standards | Open viewer, load asymmetric-routing fixture scan, confirm marker visible on at least one edge, hover shows tooltip with classifier label |
| End-to-end DC-agent → backend → FlowMap viewer asymmetry detection on a real lab topology | PTH-01..03,ASY-01..03 | Requires live router + NetFlow exporter | UAT script: run agent against staging lab BGP/NetFlow, trigger asymmetry by changing local-pref on one peer, confirm FlowMap surfaces divergence within 15 min cron tick |
| Slack alert delivery (NFN-02) reaches a configured channel | NFN-02 | Slack API delivery cannot be verified without a real workspace token | UAT script: configure team Slack webhook, force route churn in lab, confirm Slack message arrives within 60s |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 90s (full), 10s (quick)
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
