---
phase: 11
slug: firewall-integration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-10
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

> Populated by the planner. Each task in `*-PLAN.md` declares an `<automated>` verify command. The list below seeds the contract; the planner fills in `Task ID`, `Plan`, `Wave` columns when emitting the plan files.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD-W0  | 11-00 | 0 | — | — | Wave 0 fixtures land before any vendor work | fixture | `cd agent && go test ./internal/checkpoint/parser/...` | ❌ W0 | ⬜ pending |
| TBD-asa-rest-1 | 11-?? | 2 | ASA-01 | T-11-asa-rest | REST client returns access-lists + NAT + objects against httptest fixture | unit | `cd agent && go test -race ./internal/asa/...` | ❌ W0 | ⬜ pending |
| TBD-asa-ssh-1 | 11-?? | 2 | ASA-03 | T-11-asa-ssh | SSH parser normalizes `show running-config` to D-08 hybrid schema | unit | `cd agent && go test -race ./internal/asa/...` | ❌ W0 | ⬜ pending |
| TBD-fmc-1 | 11-?? | 2 | ASA-02 | T-11-fmc | FMC token refresh on 401 succeeds before bailing | unit | `cd agent && go test -race ./internal/fmc/...` | ❌ W0 | ⬜ pending |
| TBD-ckp-live-1 | 11-?? | 2 | CKP-01 | T-11-ckp-live | Login → fetch → logout against httptest fixture; SID never logged | unit | `cd agent && go test -race ./internal/checkpoint/...` | ❌ W0 | ⬜ pending |
| TBD-ckp-import-1 | 11-?? | 2 | CKP-02 | T-11-ckp-import | Shared parser yields equivalent rules from live + offline fixtures | equivalence | `cd agent && go test -race ./internal/checkpoint/parser/...` | ❌ W0 | ⬜ pending |
| TBD-be-schema | 11-02 | 1 | ASA-01..03,CKP-01..02 | T-11-rls | New tables enforce team RLS; `current_setting('app.current_team_id')` required | integration | `cd backend && pytest tests/test_schemas_firewall.py` | ❌ W0 | ⬜ pending |
| TBD-be-push | 11-03 | 2 | ASA-01..03,CKP-01..02 | T-11-bearer | 3 push endpoints accept site_token Bearer; reject without | integration | `cd backend && pytest tests/test_routes_firewall.py` | ❌ W0 | ⬜ pending |
| TBD-be-read | 11-04 | 2 | ROADMAP §11.4 | T-11-jwt | `GET /v1/sites/{id}/firewall-rules` returns latest snapshot per device under Clerk JWT, RLS-scoped | integration | `cd backend && pytest tests/test_routes_firewall_read.py` | ❌ W0 | ⬜ pending |
| TBD-ticker | 11-?? | 3 | D-02, D-03 | — | 4th ticker fires firewall pulls at 1h cadence; shutdown drains | integration | `cd agent && go test -race ./cmd/infracanvas-agent/...` | ❌ W0 | ⬜ pending |
| TBD-cab | 11-?? | 4 | DCA-09 fwd | T-11-creds | CAB packet enumerates the 5 firewall-creds points from CONTEXT §specifics | manual+grep | `grep -q "login-per-pull" agent/docs/cab/threat-model.md` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `agent/internal/asa/testdata/asa-rest-acl.json` — fixture for ASA REST access-list response
- [ ] `agent/internal/asa/testdata/asa-rest-nat.json` — fixture for ASA REST NAT response
- [ ] `agent/internal/asa/testdata/asa-rest-objects.json` — fixture for ASA REST network/service objects
- [ ] `agent/internal/asa/testdata/show-running-config.txt` — fixture for ASA SSH `show running-config` output (with access-lists + nat lines)
- [ ] `agent/internal/fmc/testdata/fmc-token.json` — fixture for FMC token acquisition response (X-auth-access-token, X-auth-refresh-token headers)
- [ ] `agent/internal/fmc/testdata/fmc-access-policy.json` — fixture for FMC access-policy + rules response
- [ ] `agent/internal/fmc/testdata/fmc-nat-policy.json` — fixture for FMC NAT-policy response
- [ ] `agent/internal/fmc/testdata/fmc-network-objects.json` — fixture for FMC network-objects response
- [ ] `agent/internal/checkpoint/testdata/ckp-login.json` — fixture for Checkpoint login response (sid)
- [ ] `agent/internal/checkpoint/testdata/ckp-access-rulebase.json` — fixture for live `show access-rulebase` response
- [ ] `agent/internal/checkpoint/testdata/ckp-access-rulebase-import.json` — paired offline fixture (must produce same parser output as live; equivalence test)
- [ ] `agent/internal/checkpoint/testdata/ckp-nat-rulebase.json` — NAT rulebase fixture
- [ ] `agent/internal/checkpoint/testdata/ckp-objects.json` — objects fixture
- [ ] `agent/internal/checkpoint/parser_test.go` — equivalence test that locks the shared-parser premise (D-12)
- [ ] `backend/tests/test_schemas_firewall.py` — RLS + table-shape stubs for the 4 new tables
- [ ] `backend/tests/test_routes_firewall.py` — push-endpoint stubs (3 endpoints × site-token middleware)
- [ ] `backend/tests/test_routes_firewall_read.py` — read-endpoint stub (Clerk JWT + RLS)
- [ ] `backend/tests/conftest.py` extension — fixtures for a populated firewall snapshot (rules + nat + objects) under a known site_id

*If none: "Existing infrastructure covers all phase requirements."* — Not applicable; all fixtures above are new.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real ASA 9.x rest endpoint reachable from operator host | ASA-01 | Requires customer ASA hardware/lab with REST API enabled | Operator: `curl -k -u user:pass https://asa-host/api/access/in/rules` returns JSON |
| Real ASA SSH `show running-config` parses cleanly | ASA-03 | Requires customer ASA hardware/lab; output varies by ASA version | Operator: ssh asa-host, run `terminal pager 0` then `show running-config`, save and confirm parser handles |
| Real FMC token lifecycle (acquire → refresh → bail) | ASA-02 | Requires customer FMC hardware; token TTL is 30 min × 3 refresh | Operator: run agent against real FMC for ≥2h, confirm one refresh + one re-login per token cycle in logs |
| Real Checkpoint mgmt API session | CKP-01 | Requires customer Checkpoint Mgmt server; session timeout is 600s default | Operator: configure agent with real CKP host, confirm login → pull → logout in logs at 1h interval |
| `mgmt_cli show ... --format json` import file matches live API output | CKP-02 | Requires running `mgmt_cli` on customer Checkpoint host | Operator: run `mgmt_cli show access-rulebase name "Standard" --format json` on Checkpoint host, save to file referenced by `checkpoint-import` protocol; agent parses cleanly |
| CAB packet language is acceptable to enterprise security review | DCA-09 fwd | Subjective — review by ops/security stakeholders | Owner reviews extended `agent/docs/cab/{threat-model,architecture,dataflow,known-limitations}.md` and signs off |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies (planner enforces)
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (fixtures + parser equivalence test)
- [ ] No watch-mode flags
- [ ] Feedback latency < 90s (full combined)
- [ ] `nyquist_compliant: true` set in frontmatter once all rows above are ✅ green

**Approval:** pending
