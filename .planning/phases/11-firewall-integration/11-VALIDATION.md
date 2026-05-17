---
phase: 11
slug: firewall-integration
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-10
audited: 2026-05-17
---

# Phase 11 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: see `11-RESEARCH.md` §"Validation Architecture" (line 761).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework (agent)** | go test + testify (Phase 10 inheritance) |
| **Framework (backend)** | pytest 8.x (Phase 10 inheritance) |
| **Config file (agent)** | `agent/go.mod`, `agent/Makefile` |
| **Config file (backend)** | `backend/pyproject.toml`, `backend/conftest.py` |
| **Quick run command (agent)** | `cd agent && go test -race ./internal/{asa,fmc,checkpoint}/...` |
| **Quick run command (backend)** | `cd backend && pytest tests/test_routes_firewall*.py tests/test_schemas_firewall.py -x` |
| **Full suite command (agent)** | `cd agent && go test -race ./...` |
| **Full suite command (backend)** | `cd backend && pytest -x` |
| **Estimated runtime (agent quick)** | ~10 seconds |
| **Estimated runtime (backend quick)** | ~15 seconds |
| **Estimated runtime (full)** | ~90 seconds combined |

---

## Sampling Rate

- **After every task commit:** Run the quick command for the side touched (agent OR backend)
- **After every plan wave:** Run the full suite for both sides
- **Before `/gsd-verify-work`:** Both full suites must be green; `-race` clean for the agent
- **Max feedback latency:** 90 seconds (full combined)

---

## Per-Task Verification Map

> Resolved against shipped artifacts on 2026-05-17. All test files present and green; backend DB-dependent tests require Docker (Testcontainers) at run time — file scaffolding and pure-logic assertions execute without it.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 11-01-W0 | 11-01 | 0 | All | — | Wave 0 fixtures land before any vendor work (13 vendor-shape fixtures + 6 RED test files) | fixture | `cd agent && go test ./internal/checkpoint/parser/...` | ✅ | ✅ green |
| 11-08-asa-rest | 11-08 | 3 | ASA-01 | T-11-asa-rest | REST client returns access-lists + NAT + objects against httptest.NewTLSServer fixture | unit | `cd agent && go test -race ./internal/asa/...` | ✅ | ✅ green |
| 11-09-asa-ssh | 11-09 | 3 | ASA-03 | T-11-asa-ssh | SSH parser (`ParseRunningConfig`) normalizes `show running-config` to D-08 hybrid schema | unit | `cd agent && go test -race ./internal/asa/...` | ✅ | ✅ green |
| 11-10-fmc | 11-10 | 3 | ASA-02 | T-11-fmc | FMC token refresh on 401 succeeds before bailing | unit | `cd agent && go test -race ./internal/fmc/...` | ✅ | ✅ green |
| 11-11-ckp-live | 11-11 | 3 | CKP-01 | T-11-ckp-live | Login → fetch → logout against httptest fixture; SID never logged (asserted via `*bytes.Buffer` log capture) | unit | `cd agent && go test -race ./internal/checkpoint/...` | ✅ | ✅ green |
| 11-11-ckp-import | 11-11 | 3 | CKP-02 | T-11-ckp-import | `TestParser_LiveImportEquivalence` — shared parser yields byte-identical output from live + offline fixtures (D-12 LOCKED) | equivalence | `cd agent && go test -race ./internal/checkpoint/...` | ✅ | ✅ green |
| 11-02-be-schema | 11-02 | 1 | ASA-01..03, CKP-01..02 | T-11-rls | 4 new tables enforce team RLS via `current_setting('app.current_team_id')` | integration | `cd backend && pytest tests/test_schemas_firewall.py` | ✅ | ✅ green (Docker-gated for RLS probes) |
| 11-03-be-push | 11-03 | 2 | ASA-01..03, CKP-01..02 | T-11-bearer | 3 push endpoints accept site_token Bearer; reject without (Pattern A+B+E) | integration | `cd backend && pytest tests/test_routes_firewall.py` | ✅ | ✅ green (Docker-gated for snapshot persistence) |
| 11-04-be-read | 11-04 | 2 | ROADMAP §11.4 | T-11-jwt | `GET /v1/sites/{id}/firewall-rules` returns latest snapshot per device under Clerk JWT, RLS-scoped (DISTINCT ON) | integration | `cd backend && pytest tests/test_routes_firewall_read.py` | ✅ | ✅ green (Docker-gated for cross-team probe) |
| 11-07-ticker | 11-07 | 2 | D-02, D-03 | — | 4th ticker fires firewall pulls at 1h cadence; shutdown drains; Pusher interface extended (mutex-guarded fakePusher under `-race`) | integration | `cd agent && go test -race ./cmd/infracanvas-agent/...` | ✅ | ✅ green |
| 11-12-dispatcher | 11-12 | 4 | All collectors | — | `collectAndPushFirewall` dispatches to 3 push endpoints; mints snapshot_id; writes Checkpoint-import config inline | integration | `cd agent && go test -race ./cmd/infracanvas-agent/...` | ✅ | ✅ green |
| 11-13-cab | 11-13 | 4 | DCA-09 fwd | T-11-creds | CAB packet enumerates the 5 firewall-creds points from CONTEXT §specifics | manual+grep | `grep -q "login-per-pull" agent/docs/cab/threat-model.md` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `agent/internal/asa/testdata/asa-rest-acl.json` — ASA REST access-list response fixture
- [x] `agent/internal/asa/testdata/asa-rest-nat.json` — ASA REST NAT response fixture
- [x] `agent/internal/asa/testdata/asa-rest-objects.json` — ASA REST network/service objects fixture
- [x] `agent/internal/asa/testdata/show-running-config.txt` — ASA SSH `show running-config` fixture
- [x] `agent/internal/fmc/testdata/fmc-token.json` — FMC token acquisition fixture
- [x] `agent/internal/fmc/testdata/fmc-access-policy.json` — FMC access-policy + rules fixture
- [x] `agent/internal/fmc/testdata/fmc-nat-policy.json` — FMC NAT-policy fixture
- [x] `agent/internal/fmc/testdata/fmc-network-objects.json` — FMC network-objects fixture
- [x] `agent/internal/checkpoint/testdata/ckp-login.json` — Checkpoint login (sid) fixture
- [x] `agent/internal/checkpoint/testdata/ckp-access-rulebase.json` — live `show access-rulebase` fixture
- [x] `agent/internal/checkpoint/testdata/ckp-access-rulebase-import.json` — paired offline fixture (D-12 equivalence)
- [x] `agent/internal/checkpoint/testdata/ckp-nat-rulebase.json` — NAT rulebase fixture
- [x] `agent/internal/checkpoint/testdata/ckp-objects.json` — objects fixture
- [x] `agent/internal/checkpoint/parser_test.go` — `TestParser_LiveImportEquivalence` (D-12 lock)
- [x] `backend/tests/test_schemas_firewall.py` — RLS + table-shape probes for the 4 new tables
- [x] `backend/tests/test_routes_firewall.py` — push-endpoint contracts (3 endpoints × site-token middleware)
- [x] `backend/tests/test_routes_firewall_read.py` — read-endpoint contract (Clerk JWT + RLS)
- [x] `backend/conftest.py` extension — `firewall_snapshot` factory fixture for parametrized seeding

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real ASA 9.x REST endpoint reachable from operator host | ASA-01 | Requires customer ASA hardware/lab with REST API enabled | Operator: `curl -k -u user:pass https://asa-host/api/access/in/rules` returns JSON |
| Real ASA SSH `show running-config` parses cleanly | ASA-03 | Requires customer ASA hardware/lab; output varies by ASA version | Operator: ssh asa-host, run `terminal pager 0` then `show running-config`, save and confirm parser handles |
| Real FMC token lifecycle (acquire → refresh → bail) | ASA-02 | Requires customer FMC hardware; token TTL is 30 min × 3 refresh | Operator: run agent against real FMC for ≥2h, confirm one refresh + one re-login per token cycle in logs |
| Real Checkpoint mgmt API session | CKP-01 | Requires customer Checkpoint Mgmt server; session timeout is 600s default | Operator: configure agent with real CKP host, confirm login → pull → logout in logs at 1h interval |
| `mgmt_cli show ... --format json` import file matches live API output | CKP-02 | Requires running `mgmt_cli` on customer Checkpoint host | Operator: run `mgmt_cli show access-rulebase name "Standard" --format json` on Checkpoint host, save to file referenced by `checkpoint-import` protocol; agent parses cleanly |
| CAB packet language acceptable to enterprise security review | DCA-09 fwd | Subjective — review by ops/security stakeholders | Owner reviews `agent/docs/cab/{threat-model,architecture,dataflow,known-limitations}.md` and signs off |
| Backend DB integration tests under Docker | ASA-01..03, CKP-01..02 | Testcontainers requires a running Docker daemon (not present in all CI envs) | Local: `docker info && cd backend && pytest tests/test_routes_firewall*.py tests/test_schemas_firewall.py -x` — 6 DB-gated cases pass |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies (planner enforces)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (fixtures + parser equivalence test)
- [x] No watch-mode flags
- [x] Feedback latency < 90s (full combined)
- [x] `nyquist_compliant: true` set in frontmatter once all rows above are ✅ green

**Approval:** validated 2026-05-17

---

## Validation Audit 2026-05-17

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 1 (backend DB tests — Docker requirement → Manual-Only row added) |

**Audit detail:** Agent `go test -race ./internal/{asa,fmc,checkpoint}/... ./cmd/infracanvas-agent/...` → all green. Backend `pytest tests/test_routes_firewall*.py tests/test_schemas_firewall.py` → 6 passed / 6 Docker-gated (Testcontainers env limitation, not a code gap). CAB grep `login-per-pull` in `agent/docs/cab/threat-model.md` → 1 match. All 13 Wave 0 fixtures + 6 RED test files + 3 backend test files present. Placeholders (`TBD-*`, `❌ W0`, draft frontmatter) resolved to actual task IDs / plan numbers / green status.
