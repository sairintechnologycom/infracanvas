---
phase: 10
plan: "01"
subsystem: dc-agent-core
completed: "2026-05-07"
duration: "8m"
tasks_completed: 3
tasks_total: 3
commits:
  - "466f63a"
  - "7954f8a"
  - "67198ab"
tags:
  - go-module
  - nyquist-scaffold
  - wave-0
  - tdd-stubs
  - dc-agent
dependency_graph:
  requires: []
  provides:
    - agent/go.mod (Go module github.com/infracanvas/infracanvas/agent)
    - agent/go.sum (all 7 pinned dependency checksums)
    - agent/cmd/infracanvas-agent/main_test.go (TestDaemonStartStop + TestTickerIntervals)
    - agent/internal/config/config_test.go (TestConfigLoad + TestConfigImport)
    - agent/internal/netconf/collector_test.go (TestNetconfCollector)
    - agent/internal/ssh/collector_test.go (TestSSHCollector)
    - agent/internal/netflow/listener_test.go (TestNetFlowListener)
    - agent/internal/netflow/buffer_test.go (TestRingBuffer)
    - agent/internal/push/client_test.go (TestPushClient)
    - backend/tests/test_agent.py (8 pytest stubs for DCA-05 backend)
  affects:
    - Plans 10-02 through 10-09 (all depend on Wave 0 stubs existing)
    - 10-VALIDATION.md (wave_0_complete flipped to true)
tech_stack:
  added:
    - Go 1.25.0 agent module (agent/)
    - nemith.io/netconf v0.0.4
    - golang.org/x/crypto v0.50.0
    - github.com/netsampler/goflow2/v2 v2.2.6
    - github.com/spf13/cobra v1.10.2
    - gopkg.in/yaml.v3 v3.0.1
    - go.uber.org/zap v1.28.0
    - github.com/stretchr/testify v1.11.1
  patterns:
    - Go standard testing + t.Skip("RED ...") stub pattern for Wave 0 Nyquist compliance
    - Separate self-contained go.mod per Go module in mixed-language monorepo (no go.work)
    - Pytest @pytest.mark.skip(reason="RED ...") stub pattern matching Go Wave 0 convention
key_files:
  created:
    - agent/go.mod
    - agent/go.sum
    - agent/.gitignore
    - agent/cmd/infracanvas-agent/main.go
    - agent/cmd/infracanvas-agent/main_test.go
    - agent/internal/config/config.go
    - agent/internal/config/config_test.go
    - agent/internal/netconf/collector.go
    - agent/internal/netconf/collector_test.go
    - agent/internal/ssh/collector.go
    - agent/internal/ssh/collector_test.go
    - agent/internal/netflow/listener.go
    - agent/internal/netflow/listener_test.go
    - agent/internal/netflow/buffer.go
    - agent/internal/netflow/buffer_test.go
    - agent/internal/push/client.go
    - agent/internal/push/client_test.go
    - backend/tests/test_agent.py
  modified:
    - .planning/phases/10-dc-agent-core/10-VALIDATION.md (wave_0_complete: true, per-task rows updated)
decisions:
  - "go 1.25.0 canonical form used (Go toolchain expands 1.25 → 1.25.0 in go.mod; grep -q 'go 1.25' still passes per plan acceptance criteria)"
  - "go mod tidy strips explicit requires when no Go source imports them; go.mod maintained with explicit require block written by hand + go mod download to populate go.sum"
  - "backend pytest coverage gate (D-15) fires at 0% when only test_agent.py runs (all skip); this is pre-existing infrastructure behavior — out of scope per SCOPE BOUNDARY rule; the plan's actual verify command (--collect-only) returns 8 correctly"
  - "wave_0_complete: true + nyquist_compliant: true flipped in 10-VALIDATION.md frontmatter on plan close per plan output spec"
---

# Phase 10 Plan 01: Wave 0 Nyquist Scaffold Summary

Go module skeleton + 8 Go test stubs (t.Skip RED) + 8 pytest stubs (@pytest.mark.skip RED) satisfying the Nyquist Wave 0 gate so all subsequent plans (10-02 through 10-09) land in strict RED→GREEN cadence.

## What Was Built

### Task 1: Go Module Initialization (commit 466f63a)

Created `agent/go.mod` with module path `github.com/infracanvas/infracanvas/agent` and 7 pinned dependencies verified against proxy.golang.org on 2026-05-07:

| Dependency | Version | Purpose |
|------------|---------|---------|
| `nemith.io/netconf` | v0.0.4 | NETCONF RFC 6241/6242 client (IOS-XE) |
| `golang.org/x/crypto` | v0.50.0 | SSH CLI transport |
| `github.com/netsampler/goflow2/v2` | v2.2.6 | NetFlow v9/IPFIX decoder |
| `github.com/spf13/cobra` | v1.10.2 | CLI framework |
| `gopkg.in/yaml.v3` | v3.0.1 | agent.yaml config parsing |
| `go.uber.org/zap` | v1.28.0 | Structured logging |
| `github.com/stretchr/testify` | v1.11.1 | Test assertions |

`agent/go.sum` populated via `go mod download`. `agent/.gitignore` excludes binaries (`/infracanvas-agent*`), local config (`/agent.yaml`, per D-05 chmod 600), and test artifacts (`/coverage.out`). No `go.work` at repo root (RESEARCH Pitfall 5).

### Task 2: Seven Go Test Stub Files (commit 7954f8a)

Created 14 files (7 source stubs + 7 test stubs) following exact test function names from 10-VALIDATION.md:

**Go test functions locked:**
- `TestDaemonStartStop` — `agent/cmd/infracanvas-agent/main_test.go` (DCA-01)
- `TestTickerIntervals` — `agent/cmd/infracanvas-agent/main_test.go` (DCA-06)
- `TestConfigLoad` — `agent/internal/config/config_test.go` (DCA-07 config reader, Plan 10-03)
- `TestConfigImport` — `agent/internal/config/config_test.go` (DCA-07 config-import fallback, Plan 10-05)
- `TestNetconfCollector` — `agent/internal/netconf/collector_test.go` (DCA-02, Plan 10-04)
- `TestSSHCollector` — `agent/internal/ssh/collector_test.go` (DCA-03, Plan 10-05)
- `TestNetFlowListener` — `agent/internal/netflow/listener_test.go` (DCA-04, Plan 10-06)
- `TestRingBuffer` — `agent/internal/netflow/buffer_test.go` (DCA-04 ring buffer, Plan 10-06)
- `TestPushClient` — `agent/internal/push/client_test.go` (DCA-05 push, Plan 10-07)

`buffer.go` and `listener.go` share `package netflow` (same package, per plan spec). All 6 packages pass `go test ./... -count=1 -timeout 30s` — all 8 tests SKIP, 0 FAIL.

### Task 3: Backend Pytest Stubs (commit 67198ab)

Created `backend/tests/test_agent.py` with 8 `@pytest.mark.skip` stubs matching DCA-05 backend verify rows in 10-VALIDATION.md:

**Pytest test names locked:**
- `test_create_site_returns_one_time_token` (POST /v1/sites, Plan 10-02)
- `test_create_site_requires_owner_role` (RBAC, Plan 10-02)
- `test_push_routes_rejects_missing_bearer` (401 missing_bearer, Plan 10-02)
- `test_push_routes_rejects_invalid_site_token` (401 invalid_site_token, Plan 10-02)
- `test_push_routes_accepts_valid_site_token` (202 happy path, Plan 10-02)
- `test_push_flows_rejects_missing_bearer` (401 missing_bearer, Plan 10-02)
- `test_push_flows_accepts_valid_site_token` (202 happy path, Plan 10-02)
- `test_dc_sites_rls_isolates_teams` (TMM-01 RLS, Plan 10-02)

`pytest tests/test_agent.py -q --co` returns 8 collected items.

## Wave 0 Nyquist Sign-Off

`wave_0_complete: true` and `nyquist_compliant: true` flipped in `.planning/phases/10-dc-agent-core/10-VALIDATION.md` frontmatter. All per-task verify commands from the verification map (rows 10-01-01 through 10-01-06) point at test files that now exist and compile. Plans 10-02 through 10-09 can begin immediately in RED→GREEN cadence.

## Pinned-Version Drift from go mod tidy

No transitive version bumps observed. `go mod tidy` with empty source packages strips ALL explicit requires (since no imports to satisfy). Resolution: go.mod explicit require block maintained with `go mod download` for go.sum population. This is the correct pattern for a binary-only module in a mixed-language monorepo.

The `go 1.25.0` canonical form (vs plan spec `go 1.25`) is a Go toolchain normalization — the acceptance criteria grep `-q "go 1.25"` passes since `go 1.25.0` contains `go 1.25`.

## Deviations from Plan

None — plan executed exactly as written. Minor notes:
1. **Go toolchain normalized `go 1.25` to `go 1.25.0`** — expected behavior; acceptance criteria still passes.
2. **`go mod tidy` strips explicit requires** when no source imports them — maintained go.mod manually + `go mod download` for go.sum; not a deviation but a known Go behavior with binary-only modules.
3. **Backend pytest D-15 coverage gate fires at 0% in isolation** — pre-existing infrastructure behavior; the plan's verify command uses `--collect-only` which returns 8 correctly; running the full test suite maintains coverage. Out of scope per SCOPE BOUNDARY rule.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced in this plan. Wave 0 only authors source/test stub files with no runtime behavior. T-10-01-01 (go.sum tampering) mitigation in place: go.sum committed; `go mod verify` guard planned for Plan 10-08 CI job.

## Known Stubs

All stubs are intentional Wave 0 scaffolding with explicit RED markers pointing to implementation plans:
- Go stubs: `t.Skip("RED — implementation lands in plan 10-0X (...)")` — Plans 10-03 through 10-07
- Python stubs: `@pytest.mark.skip(reason="RED — implementation lands in plan 10-02 (...)")` — Plan 10-02

These are not data stubs affecting UI — they are test scaffold for future RED→GREEN cycles.

## Self-Check: PASSED

**Files exist:**
- agent/go.mod: FOUND
- agent/go.sum: FOUND (non-empty)
- agent/.gitignore: FOUND
- agent/cmd/infracanvas-agent/main_test.go: FOUND
- agent/internal/config/config_test.go: FOUND
- agent/internal/netconf/collector_test.go: FOUND
- agent/internal/ssh/collector_test.go: FOUND
- agent/internal/netflow/listener_test.go: FOUND
- agent/internal/netflow/buffer_test.go: FOUND
- agent/internal/push/client_test.go: FOUND
- backend/tests/test_agent.py: FOUND

**Commits exist:**
- 466f63a (chore: Go module init): FOUND
- 7954f8a (test: Go stub files): FOUND
- 67198ab (test: pytest stubs): FOUND
