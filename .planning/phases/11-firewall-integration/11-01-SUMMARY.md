---
phase: 11
plan: 01
subsystem: firewall-integration
tags: [wave-0, tdd, test-scaffold, fixtures, red]
requires:
  - phase-10-summary  # Pusher interface, require_site_token, dc_sites, mock_clerk
provides:
  - agent-firewall-fixtures  # 13 vendor-shape JSON/text fixtures
  - agent-firewall-red-tests  # 6 _test.go files locking collector contracts
  - backend-firewall-red-tests  # 3 pytest files locking schema + route contracts
  - firewall_snapshot-fixture  # conftest factory for downstream read-API tests
  - d12-equivalence-lock  # TestParser_LiveImportEquivalence — shared parser premise
affects:
  - agent/cmd/infracanvas-agent/main_test.go  # TestDefaultIntervals extended for 4th interval
tech-stack:
  added: []   # No new dependencies; reuses Phase 10's testify + httptest + pytest stack
  patterns:
    - "httptest.Server-driven REST collector tests (mirrors netconf/collector_test.go)"
    - "Mock Session/Dialer interfaces for SSH collector tests (mirrors ssh/collector_test.go)"
    - "Paired live + import fixtures locking shared-parser equivalence (D-12)"
    - "Pattern B (set_config app.current_team_id) on all backend DB probes"
    - "Factory fixture pattern for parametrized snapshot seeding"
key-files:
  created:
    - agent/internal/asa/testdata/asa-rest-acl.json
    - agent/internal/asa/testdata/asa-rest-nat.json
    - agent/internal/asa/testdata/asa-rest-objects.json
    - agent/internal/asa/testdata/show-running-config.txt
    - agent/internal/asa/rest_test.go
    - agent/internal/asa/ssh_test.go
    - agent/internal/fmc/testdata/fmc-token.json
    - agent/internal/fmc/testdata/fmc-access-policy.json
    - agent/internal/fmc/testdata/fmc-nat-policy.json
    - agent/internal/fmc/testdata/fmc-network-objects.json
    - agent/internal/fmc/client_test.go
    - agent/internal/checkpoint/testdata/ckp-login.json
    - agent/internal/checkpoint/testdata/ckp-access-rulebase.json
    - agent/internal/checkpoint/testdata/ckp-access-rulebase-import.json
    - agent/internal/checkpoint/testdata/ckp-nat-rulebase.json
    - agent/internal/checkpoint/testdata/ckp-objects.json
    - agent/internal/checkpoint/parser_test.go
    - agent/internal/checkpoint/live_test.go
    - agent/internal/checkpoint/import_test.go
    - backend/tests/test_routes_firewall.py
    - backend/tests/test_routes_firewall_read.py
    - backend/tests/test_schemas_firewall.py
  modified:
    - agent/cmd/infracanvas-agent/main_test.go
    - backend/tests/conftest.py
decisions:
  - "TestDefaultIntervals extended in place (not duplicated, not replaced) — keeps the DCA-06 timing contract test as a single function with all 4 interval assertions"
  - "TestRunDaemon_FirewallTick stubbed with t.Skip rather than left as a TODO comment — keeps the suite RED-but-runnable; Plan 11-07 removes the skip"
  - "rest_test.go uses inline sscanInt helper rather than importing strconv to keep the imports list aligned with the netconf analog (cosmetic, but flagged for downstream consistency reviewers)"
  - "ckp-access-rulebase.json and ckp-access-rulebase-import.json are byte-identical in this scaffold — the test asserts reflect.DeepEqual on parser output, so a future planner can diverge the envelope shapes provided parser output stays equivalent"
  - "firewall_snapshot is a factory fixture (returns a callable) rather than a parameter fixture — lets a single test seed multiple parent rows with different snapshot_ts values for D-11 latest-per-device coverage"
metrics:
  duration_minutes: 7
  tasks_completed: 2
  files_created: 22
  files_modified: 2
  total_files: 24
  completed_date: "2026-05-12"
---

# Phase 11 Plan 01: Wave 0 Test Scaffold Summary

Lands every RED test stub and vendor-shape fixture file the downstream Phase 11 plans will GREEN. No production code is written; every test references symbols that do not exist yet (`asa.NewRESTCollector`, `fmc.NewClient`, `checkpoint.Parse`, `iv.Firewall`, `app.schemas.firewall.*`, `firewall_ruleset_snapshots` table) so the compile-RED / runtime-ModuleNotFoundError state is the intended hand-off to Wave 1+.

## What Was Built

### Agent-side (Task 1, commit `05ee050`)

**13 vendor fixtures** structured to match real Cisco ASA REST, Cisco FMC, and Checkpoint Management API response shapes (planner-researched URLs in 11-RESEARCH.md §Sources):

- `agent/internal/asa/testdata/` — 3 ASA REST JSON fixtures (`asa-rest-acl.json` with 3 access rules including a deny-all final; `asa-rest-nat.json` with one static + one dynamic NAT; `asa-rest-objects.json` with 3 network objects including a group) plus `show-running-config.txt` carrying 14 directive-bearing lines: `access-list ×6`, `nat (...) ×3`, `object network ×3`, `object-group network ×2`.
- `agent/internal/fmc/testdata/` — `fmc-token.json` with both `X-auth-access-token` and `X-auth-refresh-token` so the test stub can serve them as headers; `fmc-access-policy.json` with rule envelopes and `paging` metadata; `fmc-nat-policy.json` and `fmc-network-objects.json` rounding out the 4-pull set.
- `agent/internal/checkpoint/testdata/` — `ckp-login.json` (sid + session-timeout), paired `ckp-access-rulebase.json` + `ckp-access-rulebase-import.json` for the D-12 equivalence lock, `ckp-nat-rulebase.json` with static + hide NAT, `ckp-objects.json` with 8 mixed-kind objects (hosts, networks, groups, services).

**6 new Go `_test.go` files** each living in the same `package asa | fmc | checkpoint` (not `_test` external) so they directly reference unexported production symbols when those eventually land. Key contracts encoded:

| File                                 | Tests                                                | Locks                                                |
| ------------------------------------ | ---------------------------------------------------- | ---------------------------------------------------- |
| `agent/internal/asa/rest_test.go`    | `TestRESTCollector_Pull`, `TestRESTCollector_DisabledAPI` | httptest fixture wiring + 401 non-retryable surface  |
| `agent/internal/asa/ssh_test.go`     | `TestSSHCollector_DisablesPager`, `TestSSHParser_RealConfig` | First command must be `terminal pager 0`; parser counts on the realistic fixture |
| `agent/internal/fmc/client_test.go`  | `TestClient_TokenRefresh`, `TestClient_PaginatedAccessRules` | Exactly one refresh attempt before bail; pagination walks all pages |
| `agent/internal/checkpoint/parser_test.go` | `TestParser_LiveImportEquivalence`, `TestParser_RulebaseCounts` | **D-12 LOCK**: live and import fixtures yield `reflect.DeepEqual` parser output |
| `agent/internal/checkpoint/live_test.go`   | `TestLiveCollector_LoginPullLogout`, `TestLiveCollector_Paginates` | D-14 login → fetch → logout lifecycle; SID never appears in logs |
| `agent/internal/checkpoint/import_test.go` | `TestImport_MatchesLiveShape`, `TestImport_MissingFile` | LoadImport is parser-equivalent to live path; error prefix matches `config-import:` precedent |

**1 main_test.go extension** — renamed `TestTickerIntervals` → `TestDefaultIntervals` (the planner's nomenclature) and appended the 4th assertion `require.Equal(t, 1*time.Hour, iv.Firewall, ...)`. Added `TestRunDaemon_FirewallTick` as a `t.Skip` stub that Plan 11-07 will fill in.

### Backend-side (Task 2, commit `6a8a9d4`)

**3 new pytest files** plus a conftest factory fixture:

| File                                          | Tests | Patterns Applied                                            |
| --------------------------------------------- | ----- | ----------------------------------------------------------- |
| `backend/tests/test_schemas_firewall.py`      | 4     | T-11-04-01 `max_length=50000`, D-08 hybrid, D-15 NAT cols, D-09 kind enum |
| `backend/tests/test_routes_firewall.py`       | 5     | Pattern A site-token, Pattern E idempotent snapshot_id, three-way share, missing-bearer 401 |
| `backend/tests/test_routes_firewall_read.py`  | 3     | Pattern B Clerk JWT, Pattern C cross-team RLS, D-11 latest-per-device |
| `backend/tests/conftest.py` (extended)        | n/a   | `firewall_snapshot` factory: seeds N parent + child rows under a fresh team + dc_site |

Every DB probe wraps a `set_config('app.current_team_id', :t, true)` inside the same transaction as the SELECT — Pattern B from PATTERNS.md, the most common-source-of-empty-list-bug guard.

## RED Verification (Wave 0 contract)

**Agent — `go vet` output is exactly the planned RED signature** (commit `05ee050`):

```
vet: internal/asa/ssh_test.go:36:7: undefined: SSHSession
vet: internal/checkpoint/import_test.go:30:40: undefined: Parse
vet: internal/fmc/client_test.go:75:7: undefined: NewClient
vet: cmd/infracanvas-agent/main_test.go:70:35: iv.Firewall undefined (type Intervals has no field or method Firewall)
```

Each undefined symbol corresponds to a specific downstream plan that will GREEN it:

| Symbol            | Will be defined by   |
| ----------------- | -------------------- |
| `NewRESTCollector`| Plan 11-05 (ASA REST)|
| `NewSSHCollector`, `SSHSession`, `SSHDialer`, `ParseRunningConfig` | Plan 11-06 (ASA SSH) |
| `NewClient` (fmc) | Plan 11-08 (FMC)     |
| `Parse` (checkpoint), `NewLiveCollector`, `NewLiveCollectorWithLogger` | Plans 11-09/10 |
| `LoadImport`      | Plan 11-11           |
| `iv.Firewall`     | Plan 11-07           |

**Backend — pytest collects 12 tests but each fails at runtime with `ModuleNotFoundError: No module named 'app.schemas.firewall'`** when run individually (confirmed by sample run on `test_firewall_rule_hybrid_shape`). This is the intended state: collection-clean is required so downstream `pytest -x` works once one plan flips GREEN; runtime-RED ensures the gate is real until Plan 11-04 ships the schemas module.

## Decisions Made

(Also captured in frontmatter `decisions:` for state-recording.)

1. **TestDefaultIntervals extended, not duplicated.** Acceptance criterion required `grep -c 'func TestDefaultIntervals' == 1`. The existing test was named `TestTickerIntervals`; renaming + extending is preferable to adding a new function that duplicates the 3 existing assertions.
2. **TestRunDaemon_FirewallTick uses t.Skip** rather than a `// TODO` block, keeping the test runner output clean. Plan 11-07 removes the skip and writes the real assertion.
3. **Paired Checkpoint fixtures are byte-identical at scaffold time.** The D-12 lock is enforced via `reflect.DeepEqual` on parser output, not on raw JSON. A future planner can diverge envelope shapes (e.g., if `mgmt_cli` emits a different wrapper) as long as the parser normalizes both to the same `Rules`/`NATs`/`Objects` slices.
4. **firewall_snapshot is a factory fixture** (returns a callable) — lets `test_returns_latest_per_device` seed two snapshots in a single test invocation for the D-11 newest-per-device assertion. A parameter fixture would force per-test parametrization gymnastics.
5. **Inline sscanInt helper in rest_test.go.** Cosmetic — keeps the import list aligned with the netconf analog. Downstream reviewers should not view this as load-bearing; refactor to `strconv.Atoi` if it ever becomes a lint annoyance.

## Deviations from Plan

None — plan executed exactly as written. Two minor naming-alignment choices (documented under Decisions) were within the planner's explicit Discretion bullet.

## Authentication Gates

None encountered.

## Known Stubs

This is a Wave 0 scaffold plan — **the entire plan IS stubs by design**. Every test fails because it references symbols that do not exist; that is the contract this plan delivers. The Wave 0 stubs are tracked here for completeness, but they are NOT regressions — they are the explicit deliverable:

| File / Symbol                                     | Reason                                                  | Resolved by |
| ------------------------------------------------- | ------------------------------------------------------- | ----------- |
| Every `_test.go` reference to a production symbol | Wave 0 RED scaffold per 11-CONTEXT.md plan decomposition | Plans 11-02 through 11-11 |
| `app.schemas.firewall.*` imports in pytest files  | Wave 0 RED — schemas module does not exist yet           | Plan 11-04 |
| `firewall_*` table references in conftest fixture | Wave 0 RED — migration does not exist yet                | Plan 11-02 |

## TDD Gate Compliance

This plan is `type=execute` with `tdd="true"` on both tasks. RED gate satisfied (commits `05ee050` and `6a8a9d4` are both `test(...)` commits). GREEN and REFACTOR gates apply at the plan level only when production code lands — those gates belong to Plans 11-02 through 11-11.

| Gate    | Commit       | Status |
| ------- | ------------ | ------ |
| RED-1   | `05ee050`    | ✅ Agent fixtures + tests committed; `go vet` reports the planned undefined symbols |
| RED-2   | `6a8a9d4`    | ✅ Backend pytest + conftest committed; runtime `ModuleNotFoundError` confirms RED |
| GREEN   | n/a in 11-01 | Deferred to Wave 1+ |
| REFACTOR| n/a in 11-01 | Deferred to Wave 1+ |

## Verification

### Automated checks performed

```bash
# Agent vet — RED expected
cd agent && go vet ./internal/asa/... ./internal/fmc/... ./internal/checkpoint/... ./cmd/infracanvas-agent/...
# Output: 4 undefined-symbol errors (one per planned Wave 1+ plan)

# Fixture inventory
find agent/internal/{asa,fmc,checkpoint}/testdata -type f | wc -l  # → 13

# Acceptance grep checks
grep -c 'func TestDefaultIntervals' agent/cmd/infracanvas-agent/main_test.go  # → 1
grep -c 'func TestRunDaemon_FirewallTick' agent/cmd/infracanvas-agent/main_test.go  # → 1
grep -c 'iv.Firewall' agent/cmd/infracanvas-agent/main_test.go  # → 1

# Backend test counts
grep -c 'def test_' backend/tests/test_routes_firewall.py        # → 5
grep -c 'def test_' backend/tests/test_routes_firewall_read.py   # → 3
grep -c 'def test_' backend/tests/test_schemas_firewall.py       # → 4

# Pattern B / T-11-04-01 grep
grep -c 'set_config.*app.current_team_id' backend/tests/test_routes_firewall.py  # → 5
grep -c '50001' backend/tests/test_schemas_firewall.py  # → 1

# Runtime RED confirmation
pytest backend/tests/test_schemas_firewall.py::test_firewall_rule_hybrid_shape
# → FAILED: ModuleNotFoundError: No module named 'app.schemas.firewall'
```

All checks pass / produce the planned RED signature.

## Commits

| Commit    | Type | Summary                                                          | Files |
| --------- | ---- | ---------------------------------------------------------------- | ----- |
| `05ee050` | test | land agent fixtures + RED test stubs                             | 20    |
| `6a8a9d4` | test | land backend pytest stubs + conftest firewall_snapshot fixture   |  4    |

## Self-Check: PASSED

- All 22 created files verified on disk ✓
- Both commits verified in `git log` ✓
- Agent `go vet` produces the planned RED signature ✓
- Backend pytest collects 12 tests and runtime-fails with `ModuleNotFoundError` (Wave 0 RED) ✓
- main_test.go has exactly 1 `TestDefaultIntervals` and exactly 1 `TestRunDaemon_FirewallTick` ✓
- Paired Checkpoint fixtures exist and the `TestParser_LiveImportEquivalence` test references both ✓

## Next Plan

`11-02-PLAN.md` — Alembic migration `20260512_011_firewall_tables.py` creating the four RLS-scoped tables (`firewall_ruleset_snapshots` parent + 3 children with ON DELETE CASCADE). Will flip the conftest `firewall_snapshot` fixture from collection-RED to runnable for downstream read-API tests.
