---
phase: 10
slug: dc-agent-core
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-07
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

### Go Agent
| Property | Value |
|----------|-------|
| **Framework** | Go standard `testing` + `github.com/stretchr/testify` v1.11.1 |
| **Config file** | none — `go test ./...` from `agent/` |
| **Quick run command** | `cd agent && go test ./... -count=1 -timeout 30s` |
| **Full suite command** | `cd agent && go test ./... -race -count=1 -timeout 120s` |
| **Estimated runtime** | ~30 seconds (quick), ~120 seconds (full with race) |

### Backend (Python)
| Property | Value |
|----------|-------|
| **Framework** | pytest ~8.3.0 (existing) |
| **Config file** | `backend/pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `cd backend && pytest tests/test_agent.py -x -q` |
| **Full suite command** | `cd backend && pytest --cov=app --cov-report=term-missing -q` |
| **Estimated runtime** | ~15 seconds (quick), ~60 seconds (full) |

---

## Sampling Rate

- **After every task commit:** `cd agent && go test ./... -count=1 -timeout 30s`
- **After every plan wave:** `cd agent && go test ./... -race -count=1` + `cd backend && pytest tests/test_agent.py -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds (Go quick run)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 10-01-01 | 01 | 0 | DCA-01 | — | N/A | unit stub | `cd agent && go test ./cmd/... -run TestDaemonStartStop -timeout 10s` | ❌ W0 | ⬜ pending |
| 10-01-02 | 01 | 0 | DCA-02 | — | N/A | unit stub | `cd agent && go test ./internal/netconf/... -run TestNetconfCollector` | ❌ W0 | ⬜ pending |
| 10-01-03 | 01 | 0 | DCA-03 | — | N/A | unit stub | `cd agent && go test ./internal/ssh/... -run TestSSHCollector` | ❌ W0 | ⬜ pending |
| 10-01-04 | 01 | 0 | DCA-04 | — | N/A | unit stub | `cd agent && go test ./internal/netflow/... -run TestNetFlowListener` | ❌ W0 | ⬜ pending |
| 10-01-05 | 01 | 0 | DCA-05 | T-10-push | Bearer header enforced; 401 on bad token | unit stub | `cd agent && go test ./internal/push/... -run TestPushClient` | ❌ W0 | ⬜ pending |
| 10-01-06 | 01 | 0 | DCA-05 | T-10-backend | 401 on bad site token; 200 on valid | integration stub | `cd backend && pytest tests/test_agent.py -x -q` | ❌ W0 | ⬜ pending |
| 10-02-01 | 02 | 1 | DCA-01 | — | N/A | unit | `cd agent && go test ./cmd/... -run TestDaemonStartStop` | ❌ W0 | ⬜ pending |
| 10-02-02 | 02 | 1 | DCA-06 | — | N/A | unit | `cd agent && go test ./cmd/... -run TestTickerIntervals` | ❌ W0 | ⬜ pending |
| 10-02-03 | 02 | 1 | DCA-07 | — | N/A | unit | `cd agent && go test ./internal/config/... -run TestConfigImport` | ❌ W0 | ⬜ pending |
| 10-03-01 | 03 | 1 | DCA-02 | T-10-mitm | InsecureIgnoreHostKey documented in CAB | unit (mock) | `cd agent && go test ./internal/netconf/... -run TestNetconfCollector` | ❌ W0 | ⬜ pending |
| 10-04-01 | 04 | 1 | DCA-03 | T-10-mitm | terminal length 0 sent; PTY allocated | unit (mock) | `cd agent && go test ./internal/ssh/... -run TestSSHCollector` | ❌ W0 | ⬜ pending |
| 10-05-01 | 05 | 1 | DCA-04 | T-10-dos | decode error continues loop; no crash | unit | `cd agent && go test ./internal/netflow/... -run TestNetFlowListener` | ❌ W0 | ⬜ pending |
| 10-05-02 | 05 | 1 | DCA-04 | T-10-race | ring buffer concurrent-safe | unit + race | `cd agent && go test ./internal/netflow/... -race -run TestRingBuffer` | ❌ W0 | ⬜ pending |
| 10-06-01 | 06 | 1 | DCA-05 | T-10-push | retries twice on 5xx; drops after 3 failures | unit (httptest) | `cd agent && go test ./internal/push/... -run TestPushClient` | ❌ W0 | ⬜ pending |
| 10-07-01 | 07 | 2 | DCA-05 | T-10-backend | 401 on bad token; 200 on valid; RLS enforced | integration | `cd backend && pytest tests/test_agent.py -x -q` | ❌ W0 | ⬜ pending |
| 10-08-01 | 08 | 3 | DCA-08 | — | N/A | GHA check | Manual GHA run on test tag | N/A | ⬜ pending |
| 10-09-01 | 09 | 3 | DCA-09 | — | N/A | manual | `ls agent/docs/cab/` | ❌ W-last | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `agent/internal/netconf/collector_test.go` — mock NETCONF interface injection — covers DCA-02
- [ ] `agent/internal/ssh/collector_test.go` — mock SSH server (golang.org/x/crypto/ssh test server) — covers DCA-03
- [ ] `agent/internal/netflow/listener_test.go` — UDP test packet sender — covers DCA-04
- [ ] `agent/internal/netflow/buffer_test.go` — ring buffer race test — covers DCA-04
- [ ] `agent/internal/push/client_test.go` — `httptest.Server` 2xx/5xx stubs — covers DCA-05
- [ ] `backend/tests/test_agent.py` — pytest for `/v1/sites`, `/v1/agent/routes`, `/v1/agent/flows` — covers DCA-05 backend
- [ ] `agent/cmd/infracanvas-agent/main_test.go` — daemon start/stop + ticker interval — covers DCA-01, DCA-06
- [ ] `agent/internal/config/config_test.go` — YAML parse + config-import mode — covers DCA-07

*Note: Go agent test files are created empty (compile-only stubs) in Wave 0, then filled RED→GREEN in subsequent waves per TDD discipline.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `linux/amd64` binary attached to GitHub release | DCA-08 | GHA matrix jobs; no local cross-compile harness | Push a test tag `v0.0.0-test10` and verify release artifacts contain `infracanvas-agent-linux-amd64` + `infracanvas-agent-darwin-arm64` |
| CAB packet complete (arch diagram, data flow, threat model, SBOM) | DCA-09 | Document artifacts, not code | `ls agent/docs/cab/` returns: `architecture.md`, `dataflow.md`, `threat-model.md`, `sbom.cyclonedx.json` |
| NETCONF routes collected from live IOS-XE device | DCA-02 | Requires Cisco DevNet sandbox | Run agent against `sandboxiosxe.cisco.com` or equivalent; verify route records appear in agent log |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
