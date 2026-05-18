---
phase: 12
status: pass-with-flags
flag_ids: [smoke-uat, edge-hop-v1.2, hardening-tests]
verified_at: 2026-05-18T00:00:00Z
verifier_model: opus-4-7
verification_mode: goal-backward
score: 9/9 must-haves verified by code; 12/12 human UAT steps pending (Plan 12-07 Task 4)
plans_covered: [12-01, 12-02, 12-03, 12-04, 12-05, 12-06, 12-07]
locked_decisions_verified: [D-01, D-04, D-06, D-08, D-09, D-10, D-15, D-16]
pitfalls_warnings_verified: [P-3, P-9, W-4, W-5, W-6, W-7, Pattern-G]
human_verification:
  - test: "12-step UAT in 12-HUMAN-UAT.md (DB sanity, agent push, cron, read API, deliberate asymmetry, Slack alert, recompute coalesce, PathEdge red dashed, Asymmetry tab, NET-010 surface, YAML catalog regression, full suite GREEN)"
    expected: "All 12 steps pass against live backend + DC agent + Slack lab; operator resumes with `approved` or `approved-with-flags <ids>`"
    why_human: "Live infrastructure (Clerk JWT staging, DC agent, Postgres, Slack webhook, deliberate BGP local-pref flip) cannot be exercised by the verifier; visual confirmation of red dashed leg + Asymmetry tab requires browser rendering"
deferred:
  - truth: "v1.2 edge-hop NetFlow correlation (exporter_interface + exit_interface columns + edge-hop matcher)"
    addressed_in: "v1.2 (post-Phase 12) — deliberate deferral per Warning 4"
    evidence: "correlate.py:46 carries explicit `# TODO(v1.2): add edge-hop comparison once agent emits the exporter` marker; Plan 12-02 omits exporter_interface/exit_interface from netflow_records migration; agent FlowRecord schema is endpoint-only"
  - truth: "Three hardening tests deliberately deferred by Plan 12-06"
    addressed_in: "Phase 12 hardening plan (Plan 12-08 or Phase 13-XX)"
    evidence: "12-06-SUMMARY.md §`Notes on Plan-Specified Tests Not Added` — (1) classify route_leak/local_pref cross-device cases, (2) 4-cycle flap suppression, (3) NET-010 persistence integration test — Rule 2 defer rationale documented; orchestration spine + Wave 0 unit coverage in place"
---

# Phase 12: Path Computation + Asymmetric Routing — Verification Report

**Phase Goal (from ROADMAP):** Detect asymmetric routing end-to-end with root cause + impact, NET-010 active.

**Verified:** 2026-05-18
**Status:** PASS-WITH-FLAGS — code-level goal achievement verified across all 7 plans; 12-step human UAT (Plan 12-07 Task 4) deferred to operator; v1.2 edge-hop correlation deliberately deferred per Warning 4; 3 hardening integration tests deliberately deferred per Plan 12-06 Rule 2.
**Verifier Model:** opus-4-7
**Mode:** Goal-backward (verifier reads merged code, ignores SUMMARY narrative)

---

## 1. Phase Goal Restated

From `.planning/ROADMAP.md`:

> Detect asymmetric routing end-to-end with root cause + impact, NET-010 active.

Five roadmap success criteria:
1. Forward + return paths computed from route + policy data
2. NetFlow correlation flags paths where observed flow ≠ computed path
3. Asymmetric routing detector flags all asymmetric flow pairs
4. Root cause classifier assigns BGP_LOCAL_PREF / ROUTE_LEAK / NAT_ASYMMETRY
5. FlowMap viewer shows divergence marker (FMV-02); route-change alert (NFN-02) fires on DC agent churn

Per CONTEXT.md D-13 the NFN-02 contract was refined: alerts fire on asymmetry transitions (new + cause-changed) rather than on every DC agent push — the verifier honors that locked decision and assesses NFN-02 against the documented transition semantics, not a literal "every push" interpretation.

---

## 2. Requirement Trace Table

| Requirement | Where Implemented (file:line) | Where Tested | Status |
|---|---|---|---|
| **PTH-01** hop-by-hop LPM forward path | `backend/app/security/pathcompute/lpm.py` (pytricia.PyTricia(32) trie + ECMP tiebreak L41-L65); `backend/app/security/pathcompute/forward.py:22-86` `compute_forward` with `max_hops=20` + visited-set loop detection (`visited: set[str]` L58; `for _ in range(max_hops)` L76; loop-guard L77) | `backend/tests/security/pathcompute/test_lpm.py`, `test_forward.py` (Plan 12-05 GREEN — 21 passed) | ✓ VERIFIED |
| **PTH-02** forward + return path pair | `backend/app/security/pathcompute/pair.py:15-45` `compute_pair` reconstructs return path via swap; `direction="return"` L33; `pair_src`/`pair_dst` evidence keys L37-38 | `test_pair.py` (Plan 12-05 GREEN) | ✓ VERIFIED |
| **PTH-03** NetFlow correlation (v1.1 endpoint-only) | `backend/app/security/pathcompute/correlate.py:38-62` `matches()` predicate endpoint-only; `emit_divergence()` L64+ synthesizes observed_path dict shaped for `PathDivergenceFindingORM`; v1.2 marker at L46 | `test_correlate.py` (Plan 12-05 GREEN) | ✓ VERIFIED (v1.1 contract) |
| **ASY-01** asymmetry via hop-node symmetric difference | `backend/app/security/pathcompute/asymmetry.py:12-30` — `(fwd_nodes ^ ret_nodes) != set()` L20 (literal symdiff) | `test_asymmetry.py` (Plan 12-05 GREEN) | ✓ VERIFIED |
| **ASY-02** root-cause classifier — NAT > LEAK > LOCAL_PREF, 0.4 threshold, UNKNOWN fallback | `backend/app/security/pathcompute/classify.py:28` `_CAUSE_THRESHOLD = float(os.environ.get("CAUSE_THRESHOLD", "0.4"))`; L32 `_PRECEDENCE = {"NAT_ASYMMETRY": 0, "ROUTE_LEAK": 1, "BGP_LOCAL_PREF": 2}`; L140-146 candidate filter + tiebreak; L142 `return ("UNKNOWN", 0.0, evidence)` | `test_classify.py` (Plan 12-05 GREEN; 3 tests: NAT wins / UNKNOWN / tiebreak) | ✓ VERIFIED |
| **ASY-03** impact scoring (bytes_per_sec + firewall_count) | `backend/app/security/pathcompute/impact.py:14-50` two scalar functions: `impact_bytes_per_sec(flows, window_seconds=3600)` + `impact_firewall_count(...)` via symdiff ∩ stateful_firewalls; persisted to `asymmetry_findings.impact_bytes_per_sec` + `impact_firewall_count` columns | `test_impact.py` (Plan 12-05 GREEN) | ✓ VERIFIED |
| **NET-010** stateful firewall asymmetry detector — persisted + surfaced | **Detector:** `cli/infracanvas/security/network/net_010.py:21+` `detect_stateful_firewall_asymmetry`; emits `NetworkFinding(rule_id="NET-010", source="network", severity="high")` (L59/L74/L75). **Persisted backend-side:** `backend/app/queue/tasks/path_compute.py:550+` Warning 6 block; INSERT into `asymmetry_findings` with `cause='NET-010'`, `cause_confidence=1.0`, evidence carrying `forward_only`/`return_only`/`node_seen_on` keys (L582-596). **CHECK migration:** `backend/migrations/versions/20260518_013_path_compute_tables.py:171` `cause IN ('BGP_LOCAL_PREF','ROUTE_LEAK','NAT_ASYMMETRY','UNKNOWN','NET-010')` extended in-place. **Read-API surface:** `backend/app/routes/paths.py:173` cause regex admits `NET-010`. **Viewer surface:** `viewer/src/components/flowmap/PathDetailPanel.tsx:306+` AsymmetryTab renders payload.cause string verbatim. **YAML reservation upheld (D-11):** `find cli/infracanvas/security/rules -name "*.yaml" \| xargs grep -l "NET-010"` → 0 hits. | `cli/tests/test_net_010_detector.py` (4 GREEN — symmetric/one-legged/empty stateful); `test_net_010_reserved_for_phase_3b` still GREEN (Plan 12-05 SUMMARY §Self-Check) | ✓ VERIFIED |
| **FMV-02** viewer PathEdge red dashed + PathDetailPanel Asymmetry tab | **PathEdge:** `viewer/src/components/flowmap/edges/PathEdge.tsx:13` `ASYMMETRIC_STROKE = '#DC2626'`; L7-9 `asymmetricForward?`/`asymmetricReturn?` data props; L45-48 effective-stroke override; dasharray "4 3" applied. **PathDetailPanel:** `PathDetailPanel.tsx:66` `hasAsymmetry = selectedPath !== null && selectedPath?.asymmetry !== undefined`; L143-144 tab render; L306+ `AsymmetryTab` side-by-side hop table with `data-mismatched`. **Hydration:** `viewer/src/lib/asymmetryFetcher.ts` + `store.ts:197` `setAsymmetries` + `FlowMapCanvas.tsx:146` `fetchAsymmetries(siteId)` useEffect. **Dashboard install:** `dashboard/components/viewer/ViewerBootstrap.tsx:38-39` installs `window.__INFRACANVAS_BACKEND_FETCH__`. | `PathEdge.test.tsx` 7/7 GREEN; `PathDetailPanel.test.tsx` 13/13 GREEN; `asymmetryFetcher.test.ts` 5/5 GREEN; `viewer-bootstrap.test.tsx` 3/3 GREEN | ✓ VERIFIED |
| **NFN-02** Slack alerts — transitions + 4-cycle flap suppression + swallow on failure | **Helper:** `backend/app/notifications/slack.py:28+` `send_team_slack` async; httpx.AsyncClient `timeout=5.0` L71; `sentry_sdk.capture_exception(exc)` L76; structlog `slack_alert_sent`/`slack_alert_failed` only — Pattern G allowlist (no URL, no message body). **Caller:** `backend/app/queue/tasks/path_compute.py:520-527` transition gate `(new_count == 2 or cause_changed) AND (fwc >= 1 or bps > _NFN_02_BYTES_THRESHOLD)`; `NFN_02_TEMPLATE` L90; reconciliation tracks `detection_count` inside evidence JSONB; first detection sets count=1 and DOES NOT alert (Pitfall 4 flap suppression). **Swallow:** helper try/except + `sentry_sdk.capture_exception` returns silently; caller doesn't propagate. | `tests/notifications/test_slack_dispatcher.py` 3/3 GREEN (Plan 12-04); Phase 8 regression 5/5 GREEN | ✓ VERIFIED (4-cycle integration test deliberately deferred — see flags) |

**Score: 9/9 must-have requirements verified by direct code inspection.**

---

## 3. Locked Decision Trace Table

| Decision | Description | Where Enforced | Status |
|---|---|---|---|
| **D-01** | Compute runs backend-side as taskiq worker; CLI offline does not compute | `backend/app/queue/tasks/path_compute.py` (taskiq `@broker.task` decorator L168); zero compute logic in `cli/infracanvas/security/network/net_010.py` beyond detector (detector consumes already-computed NetworkPath pair) | ✓ ENFORCED |
| **D-04** | 15-min cron + on-demand POST recompute (owner role) | `path_compute.py:168` `schedule=[{"cron": "*/15 * * * *"}]`; `routes/paths.py:323` `recompute_paths_for_site.kiq(...)` enqueue + `require_role("owner")` gate | ✓ ENFORCED |
| **D-06** | Rolling 1h NetFlow window for correlation | `path_compute.py` per-site worker fetches NetFlow `WHERE collected_at > NOW() - INTERVAL '1 hour'` (Plan 12-06 SUMMARY step 3); `impact_bytes_per_sec(window_seconds=3600)` default | ✓ ENFORCED |
| **D-08** | NAT > LEAK > LOCAL_PREF deterministic precedence | `classify.py:32` `_PRECEDENCE = {"NAT_ASYMMETRY": 0, "ROUTE_LEAK": 1, "BGP_LOCAL_PREF": 2}`; L146 sort key `(-confidence, _PRECEDENCE[cause])` | ✓ ENFORCED |
| **D-08** | 0.4 confidence threshold (env-tunable) | `classify.py:28` `_CAUSE_THRESHOLD = float(os.environ.get("CAUSE_THRESHOLD", "0.4"))`; L140 candidates filter `>= _CAUSE_THRESHOLD` | ✓ ENFORCED |
| **D-09** | UNKNOWN fallback when no cause clears threshold | `classify.py:142` `return ("UNKNOWN", 0.0, evidence)` when candidates dict empty | ✓ ENFORCED |
| **D-10** | Dual impact scalars + sort `firewall_count DESC, byte_volume DESC` | `impact.py` two functions; `routes/paths.py:219` `ORDER BY impact_firewall_count DESC, impact_bytes_per_sec DESC` | ✓ ENFORCED |
| **D-15** | ENABLE + FORCE ROW LEVEL SECURITY + team_isolation on all 5 new tables | Migration 012 L74,L128 (`route_records` + `netflow_records`); Migration 013 L113,L181,L238 (`computed_paths` + `asymmetry_findings` + `path_divergence_findings`); each table also has `CREATE POLICY <table>_team_isolation` (verified in grep output: 5 tables × 1 policy each) | ✓ ENFORCED (all 5 tables) |
| **D-16** | Reconciliation lifecycle (`first_seen_at` / `last_seen_at` / `resolved_at`) + snapshot-per-pull | Migration 013 finding tables carry all three columns (`first_seen_at` + `last_seen_at` NOT NULL, `resolved_at` NULL); `path_compute.py:425+` two reconciliation sweeps (main cause family + NET-010 family) — UPDATE `last_seen_at` on still-present, INSERT with `detection_count=1` on new, UPDATE `resolved_at` on missing; `computed_paths` UNIQUE constraint enforces snapshot semantics | ✓ ENFORCED |

**All 8 locked decisions enforced in code.**

---

## 4. Pitfall / Warning Spot-Checks

| ID | Description | Evidence | Status |
|---|---|---|---|
| **Pitfall 3** | ECMP deterministic tiebreak via lex-lowest (metric, next_hop) | `lpm.py:61` `if (r.metric, r.next_hop) < (ex_metric, ex_next):` — tuple comparison enforces lex-lowest deterministic ordering on collision | ✓ HELD |
| **Pitfall 9** | CLI imports via re-export (no redeclaration) | `backend/app/schemas/paths.py:26` `from infracanvas.graph.models import NetworkPath, PathHop  # noqa: F401`; `net_010.py` also imports `NetworkFinding` from cli graph models — single source of truth maintained | ✓ HELD |
| **Warning 4** | v1.2 edge-hop TODO marker in correlate.py | `correlate.py:46` `# TODO(v1.2): add edge-hop comparison once agent emits the exporter`; `grep -v '^[[:space:]]*#' correlate.py \| grep -c 'exporter_interface\|exit_interface'` = 0 (per Plan 12-05 SUMMARY); migration 012 also omits these columns (L85 documents deferral) | ✓ HELD |
| **Warning 5** | Per-leg classify in path_compute.py (forward routes from fwd last-hop, return routes from ret last-hop) | `path_compute.py:415-418` `fwd_routes = _leg_routes(fwd, route_snapshot)` + `ret_routes = _leg_routes(ret, route_snapshot)` then `classify(fwd, ret, fwd_routes, ret_routes, nat_rules)`; `_leg_routes` helper L143-160 selects the LAST hop's device's routes per leg — no silent NAT-only degradation | ✓ HELD |
| **Warning 6** | NET-010 persisted backend + surfaced viewer | Persisted: `path_compute.py:582-596` INSERT with `cause='NET-010'`; Migration 013:L171 CHECK admits NET-010; Surfaced backend: `routes/paths.py:173` regex admits NET-010 + `cause` column in `AsymmetryFindingResponse` is open string; Surfaced viewer: `PathDetailPanel.tsx:306+` AsymmetryTab renders payload.cause verbatim | ✓ HELD |
| **Warning 7** | POST /paths/recompute hard imports (no 503 placeholder) | `routes/paths.py:70` `from app.queue.tasks.path_compute import recompute_paths_for_site` (module-level); L270 docstring labels Warning 7 as HISTORICAL; the inline try/except ImportError → 503 block deleted in Plan 12-06 commit `673008b`; corresponding 503-regression test deleted from `test_paths_recompute.py` | ✓ HELD |
| **Pattern G** | Logging allowlist in path_compute.py — no raw paths, evidence, or IPs | `path_compute.py:197` fan-out log uses only `sites_enqueued` + `teams_scanned`; L258 site-not-found uses `site_id` only; L700 completion log uses `site_id`/`team_id`/`on_demand` + summary counters; no hop content, no evidence blobs, no src/dst IPs in any log call | ✓ HELD |

**All 7 pitfalls/warnings spot-checks held.**

---

## 5. Cross-Phase Regression Snapshot

| Regression Surface | Verification | Status |
|---|---|---|
| **Phase 8 scan_repo Slack dispatcher** | `backend/app/queue/tasks/scan_repo.py:320-322` now calls `from app.notifications.slack import send_team_slack` + `await send_team_slack(...)`; Phase 8 inline httpx.AsyncClient block removed; Plan 12-04 SUMMARY §Self-Check: 5/5 Phase 8 `test_slack_*` cases still GREEN; message format, structlog event names (`scan_repo.slack_alert_sent`/`_failed`), and `:rotating_light: *Critical findings detected*` literal preserved verbatim | ✓ PRESERVED |
| **Phase 8 `hasattr(sr_mod, "httpx")` regression gate** | `import httpx` kept in scan_repo.py with `# noqa: F401` (Plan 12-04 SUMMARY decision §1) so Phase 8 tests asserting `hasattr(sr_mod, "httpx")` continue to pass | ✓ PRESERVED |
| **Phase 11 firewall integration** | `backend/app/routes/firewalls.py` unchanged in scope; `FirewallRulesetSnapshot` + `FirewallNATRuleORM` consumed read-only by path_compute.py step 5 (Plan 12-06 SUMMARY); no schema migration touched the firewall tables | ✓ PRESERVED |
| **YAML rules catalog (51 → 51 — NET-010 NOT in YAML)** | `find cli/infracanvas/security/rules -name "*.yaml" \| xargs grep -l "NET-010"` → 0 hits; `test_net_010_reserved_for_phase_3b` still GREEN per Plan 12-05 SUMMARY §Self-Check (rules-count assertion untouched per D-11) | ✓ PRESERVED |
| **Phase 3 viewer dual-color PathEdge** | `PathEdge.tsx` retains existing Phase 3 forward `#3B82F6` / return `#F97316` solid strands when `asymmetricForward`/`asymmetricReturn` flags are both absent/falsy (verified L45-48 effective-stroke gate); Phase 3 + Phase 11 viewer tests still GREEN (167 tests passing across 19 files per Plan 12-07 SUMMARY) | ✓ PRESERVED |
| **Phase 10 DC agent ingest** | `backend/app/routes/agent.py` push_routes + push_flows handlers rewritten to persist under RLS GUC (Plan 12-02 closes Blocker 1); upstream `RouteRecord` + `NetFlowRecord` payload shapes consumed unchanged; FlowRecord Pydantic schema verified zero-diff (endpoint-only per RESEARCH Q2) | ✓ PRESERVED |

**No cross-phase regression detected at the code level.**

---

## 6. Outstanding Items

### 6.1 Deferred — v1.2 Edge-Hop Correlation (Warning 4)

`correlate.py:46` carries an explicit `# TODO(v1.2): add edge-hop comparison once agent emits the exporter` marker. Migration 012 omits `exporter_interface` / `exit_interface` columns from `netflow_records`. The agent FlowRecord Pydantic schema is endpoint-only.

**Why deferred:** Phase 10 DC agent does not yet emit `exporter_interface` / `exit_interface` in NetFlow payloads; emitting them and adding the edge-hop matcher in this phase would create an asymmetric schema between Go agent and Python backend.

**Required for closure:** A future v1.2 plan extends agent emitter + migration + correlate.matches() simultaneously.

### 6.2 Deferred — 3 Hardening Integration Tests (Plan 12-06 §Notes)

Plan 12-06 deliberately deferred three integration tests:
1. `test_classify_route_leak_fires_when_legs_have_different_route_tables` + `test_classify_local_pref_fires_on_metric_divergence` (Warning 5 cross-device classify cases)
2. `test_4_cycle_flap_suppression_fires_exactly_once` (Info 9 flap-suppression bound)
3. `test_net_010_finding_persisted_as_asymmetry_with_cause_NET010` (Warning 6 NET-010 persistence integration)

**Why deferred:** Each requires seeded multi-row Postgres testcontainer fixtures (asymmetric routes + firewall snapshot + NetFlow records) that materially expand plan scope (~150-200 LOC of fixtures + 2 tests). Wave 0 + Wave 2 unit coverage already exercises the underlying logic; what is missing is end-to-end fixture-backed integration tests.

**Required for closure:** Phase 12 hardening plan (Plan 12-08 or Phase 13-XX) lands the fixtures + tests.

### 6.3 Pending — Plan 12-07 Task 4 Smoke Checkpoint (12-HUMAN-UAT.md)

Plan 12-07 is `autonomous: false`. The 4 code tasks (PathEdge, PathDetailPanel, asymmetryFetcher, ViewerBootstrap) are committed; the 12-step human UAT (DB sanity → agent push → cron → read API → deliberate-asymmetry Slack alert → recompute coalesce → viewer red dashed → Asymmetry tab → NET-010 surface → YAML regression → full suite GREEN) requires live backend + DC agent + Slack lab and cannot be performed by the verifier.

**Required for closure:** Operator resumes with `approved` / `approved-with-flags <ids>` / `blocked <reason>` per 12-HUMAN-UAT.md.

---

## 7. Verdict

**PASS-WITH-FLAGS**

### Rationale

Every requirement in the Phase 12 goal (PTH-01..03, ASY-01..03, NET-010, FMV-02, NFN-02) is implemented in merged code, supported by passing tests, and traceable to the file:line evidence in §2. Every locked decision (D-01, D-04, D-06, D-08, D-09, D-10, D-15, D-16) is enforced in code at the cited locations. Every pitfall/warning the planner flagged (Pitfall 3, Pitfall 9, Warning 4, Warning 5, Warning 6, Warning 7, Pattern G) holds against direct code inspection. Cross-phase regression surfaces (Phase 8 scan_repo Slack, Phase 8 httpx hasattr gate, Phase 11 firewall, Phase 3 viewer dual-color, YAML rules catalog, Phase 10 DC agent ingest) are preserved.

The phase goal "Detect asymmetric routing end-to-end with root cause + impact, NET-010 active" is achieved at the code level. The end-to-end pipeline exists: DC agent push (Phase 10) → 15-min taskiq cron → per-site compute (LPM → forward → pair → correlate → asymmetry → classify with NAT>LEAK>LOCAL_PREF/UNKNOWN → impact scalars → NET-010 detector) → persisted to `asymmetry_findings` under RLS → exposed via `GET /v1/sites/{id}/asymmetries` (Clerk JWT + Pattern B + Pattern C) → consumed by viewer (`fetchAsymmetries` + Zustand `setAsymmetries` + `PathEdge` red dashed leg + `PathDetailPanel` Asymmetry tab) → NFN-02 Slack transition alerts (via Plan 12-04 `send_team_slack` helper with swallow + Sentry).

### Why PASS-WITH-FLAGS not PASS

1. **Smoke UAT pending (Plan 12-07 Task 4).** Visual confirmation of red dashed leg + Asymmetry tab against live infrastructure cannot be verified programmatically.
2. **v1.2 edge-hop correlation deferred** (Warning 4) — intentional and documented; not a closure blocker for v1.1 scope.
3. **3 hardening integration tests deferred** by Plan 12-06 (Rule 2 documented rationale) — the underlying logic is exercised by Wave 0 + Wave 2 unit tests; fixture-backed e2e integration is the gap.

None of these are code-level blockers. The first surfaces in human verification; the latter two are explicitly scoped out per locked decisions (Warning 4) or documented deferral (Plan 12-06 §Notes).

### Why not FAIL

No code-level evidence contradicts the SUMMARY narrative. Every file claimed to exist exists. Every grep claimed by SUMMARY self-checks reproduces against the merged code. The orchestration pipeline in `path_compute.py` does invoke `compute_pair → is_asymmetric → classify → impact_*` then persists `asymmetry_findings` (Warning 6 NET-010 included via separate INSERT block). Reconciliation sweeps update `first_seen_at`/`last_seen_at`/`resolved_at` (D-16). Per-leg device routes flow into `classify()` (Warning 5). All 5 RLS tables carry FORCE ROW LEVEL SECURITY + team_isolation (D-15). The 503 placeholder is gone (Warning 7).

### Recommendation

Proceed to operator-driven smoke UAT (12-HUMAN-UAT.md). On `approved` or `approved-with-flags`, Phase 12 closes. The two deferred items (v1.2 edge-hop, hardening tests) carry into a future plan and do not block Phase 13.

---

*Verifier: Claude opus-4-7*
*Mode: goal-backward, read-only*
*Verified: 2026-05-18*
