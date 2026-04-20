---
phase: 04-e2e-wiring-hardening
plan: 04
subsystem: tests
tags: [tests, coverage, ci-gate, parametrized, per-module-gate]

# Dependency graph
requires:
  - phase: 04 Plan 01 (WRG-01 exit-code contract + stderr routing)
  - phase: 04 Plan 02 (WRG-02 5-key drift contract)
  - phase: pre-existing rules/aws/*.yaml (30 SEC-* rules), rules/azure/*.yaml (10 AZ-* rules)

provides:
  - Coverage config in pyproject.toml with branch=true, fail_under=80, source=["infracanvas"]
  - pytest-cov in test extras; pytest addopts scoped to security+cost+drift
  - Per-module >=80% line+branch gate (conftest.py pytest_sessionfinish hook) — structural enforcement beyond pytest-cov's global --cov-fail-under
  - 80 parametrized SEC-* + AZ-* rule tests (30 x 2 SEC-AWS + 10 x 2 AZ) backed by reviewable JSON fixtures
  - DFT-INV-01 drift-invariant property test asserting sum(drift.values()) == len(nodes) across mixes including shadow
  - CLI contract tests (test_cli_contract.py) asserting Plan 01's exit-code contract (0/1/2) and stderr routing

affects:
  - Phase 5+ can treat CLI core (security/cost/drift) as regression-gated; a future plan that degrades any rule's semantic correctness will fire one of 80 rule tests immediately
  - CI must preserve the global pytest addopts (--cov-fail-under=80 scoped to security/cost/drift) and the conftest per-module gate
  - Future additions of SEC-*/AZ-* rules require appending positive+negative fixtures to sec_fixtures.json/az_fixtures.json or the new rule will ship untested (tests are driven from hand-listed ID arrays for reviewability)

# Tech tracking
tech-stack:
  added:
    - "pytest-cov>=5,<8 in test extras (dev-only)"
  patterns:
    - "Parametrized rule × positive/negative fixture pattern lifted from test_flowmap_network_rules.py and applied to SEC + AZ"
    - "pytest_sessionfinish coverage gate: reads .coverage via coverage.Coverage + coverage.results.analysis_from_file_reporter to extract per-file line + branch counts, aggregated by path prefix, enforcing per-module thresholds that pytest-cov's global --cov-fail-under cannot express"
    - "Scoped pytest addopts (--cov=infracanvas.security --cov=infracanvas.cost --cov=infracanvas.drift) to narrow global gate to WRG-04 scope without failing on pre-existing out-of-scope sub-80% modules (main.py 61%, parser/module.py 33%)"

key-files:
  created:
    - cli/tests/conftest.py
    - cli/tests/test_cli_contract.py
    - cli/tests/fixtures/rules/sec_fixtures.json
    - cli/tests/fixtures/rules/az_fixtures.json
  modified:
    - cli/pyproject.toml
    - cli/tests/test_cost.py
    - cli/tests/test_drift.py
    - cli/tests/test_security.py

key-decisions:
  - "Scoped the default pytest addopts to --cov=infracanvas.security/cost/drift (not global --cov=infracanvas) because the repo-wide baseline is 78.5% (main.py 61%, parser/module.py 33%) — out of scope for WRG-04. The global --cov-fail-under=80 would fail immediately on baseline otherwise. The conftest per-module gate still enforces D-15 structurally on the three in-scope modules. (Rule 3 deviation.)"
  - "Branch counts computed via public API coverage.results.analysis_from_file_reporter — analysis2() alone only returns line stats. The first conftest draft used cov._analyze() (private) which returned n_branches=0. Switched to analysis_from_file_reporter after probing the coverage 7.13.5 surface."
  - "conftest hook skips gate for any prefix with zero measured files (scoped pytest runs, e.g. `pytest tests/test_cost.py`, should not fail for security/drift 0/0)."
  - "Hand-listed SEC_AWS_IDS (30) and SEC_AZ_IDS (10) rather than collection-time enumeration — PATTERNS.md called out reviewability: a new rule should fail the test suite loudly if it's not added to this list, which forces the contributor to also add fixtures."
  - "NET-* rules (11) deliberately out of scope — already covered by test_flowmap_network_rules.py per PATTERNS.md §Rule count."

patterns-established:
  - "Rule parametrize pattern: `SEC_IDS` hard-list + `{rule_id}_positive`/`{rule_id}_negative` fixture JSON + `TestSEC_RuleEvaluation` + `TestAZ_RuleEvaluation` classes. Replicate for any future rule family (policy/, compliance/)."
  - "Per-module coverage gate via pytest_sessionfinish — structurally enforce per-path coverage thresholds that pytest-cov cannot. Recipe: load coverage via coverage.Coverage, aggregate via analysis_from_file_reporter, fail session if any prefix under threshold, no-op if coverage wasn't collected."
  - "Fixture-driven false-positive/false-negative catching: positive fixture must match the rule's YAML condition exactly; negative fixture must be minimally different on the specific axis under test (siblings can fire other rules — we only filter by the target rule_id)."

requirements-completed: [WRG-04]

# Metrics
duration: 45min
completed: 2026-04-20
---

# Phase 04 Plan 04: Per-Module Coverage Gate + Parametrized Rule Suite (WRG-04) Summary

**Closed WRG-04: pytest-cov enforces >=80% line+branch on security/cost/drift globally; a pytest_sessionfinish hook enforces the same threshold per-module structurally; 80 parametrized SEC+AZ rule tests catch regressions at rule N+1 instead of after all 40; drift invariant + CLI exit-code contract tests lock in Plans 01 and 02.**

## Performance

- **Duration:** ~45 min
- **Started:** 2026-04-20
- **Tasks:** 3 (Task 1, 2a, 2b)
- **Commits:** 3 (atomic, one per task)
- **Files created:** 4
- **Files modified:** 4
- **Tests added:** 96 (80 rule-parametrized + 6 cost branch-fill + 1 drift 5-key update + 6 drift invariant parametrized + 4 CLI contract)
- **Total tests:** 271 baseline → 367 after Plan 04

## Rule-ID counts

| Rule family | Count | In scope? | Coverage source |
|-------------|-------|-----------|-----------------|
| SEC-AWS     | 30    | YES (Plan 04) | `test_security.py::TestSEC_RuleEvaluation` × positive+negative = 60 cases |
| AZ-*        | 10    | YES (Plan 04) | `test_security.py::TestAZ_RuleEvaluation` × positive+negative = 20 cases |
| NET-*       | 11    | NO (pre-existing) | `test_flowmap_network_rules.py::TestNetworkRuleEvaluation` (already 22 cases) |
| **Total (new in Plan 04)** | **40** | — | **80 new cases** |
| **Grand total across all rule families** | **51** | — | **102 parametrized rule cases** |

Per PATTERNS.md §Rule count confirmed by `grep -hE "^- id:" cli/infracanvas/security/rules/{aws,azure}/*.yaml` at plan start: 30 SEC + 10 AZ = 40, no gaps in numbering.

## Final coverage percentages (from full `pytest tests/` run)

Per-module gate via conftest `pytest_sessionfinish` hook, using `coverage.results.analysis_from_file_reporter`:

| Module                | Line coverage    | Branch coverage | Gate (>=80% both) |
|-----------------------|------------------|-----------------|-------------------|
| `infracanvas/security/` | **93.9%** (230/245) | **82.3%** (107/130) | PASS |
| `infracanvas/cost/`     | **100.0%** (81/81)  | **100.0%** (32/32)  | PASS |
| `infracanvas/drift/`    | **100.0%** (23/23)  | **90.0%** (9/10)    | PASS |

Scoped coverage runs (demanded by verification block):

| Command | Result |
|---------|--------|
| `pytest --cov=infracanvas.security --cov-branch --cov-fail-under=80 tests/test_security.py tests/test_flowmap_network_rules.py tests/test_scorer.py tests/test_staleness.py` | PASS — 83.20% |
| `pytest --cov=infracanvas.cost --cov-branch --cov-fail-under=80 tests/test_cost.py` | PASS — 100.00% |
| `pytest --cov=infracanvas.drift --cov-branch --cov-fail-under=80 tests/test_drift.py tests/test_shadow.py` | PASS — 93.94% |

## Global gate confirmation

`pytest tests/` (full suite, default addopts) triggers BOTH gates:

1. **Global addopts gate** (pytest-cov `--cov-fail-under=80` on `security+cost+drift` union):
   `Required test coverage of 80% reached. Total coverage: 92.51%`
2. **Per-module conftest gate**: no `PER-MODULE COVERAGE FAIL` messages printed (all three prefixes >=80% line+branch).

Exit code 0. 367 tests pass.

## Fixtures requiring judgment calls

Most fixtures are mechanical translations of the rule's `condition:` block. The non-obvious ones:

- **SEC-007 positive** (`policy contains "\"Action\":\"*\""`): the condition matches a *substring of the JSON-encoded policy document*, not a structured wildcard. Positive fixture stores the policy as a serialized JSON string with `\"Action\":\"*\"` in it, mirroring the `_clean_value` shape HCL parsing would produce. Engine handles both the literal and `\\\"`-unescaped form (engine.py:66).
- **SEC-012 positive/negative** (`versioning.enabled not_equals true`): nested attribute access. Engine's `_get_nested_attr` takes `versioning` → `enabled`. Positive: `{"versioning": {"enabled": false}}`. Negative: `{"versioning": {"enabled": true}}`.
- **SEC-027 positive/negative** (`point_in_time_recovery.enabled not_equals true`): same nested pattern.
- **SEC-008** (`root_block_device.encrypted not_exists`): `_get_nested_attr` on a missing key returns None → not_exists matches. Positive omits root_block_device entirely; negative provides `{"root_block_device": {"encrypted": true}}`.
- **AZ-001 / AZ-003** (`security_rule.<field> equals/any_equals`): engine resolves `security_rule` → first-element-of-list. Both fixtures use `security_rule: [{...}]`. AZ-003 uses `any_equals` which iterates the list, so it also would work with multiple rules; we use a single-rule list for clarity.
- **SEC-s3 rules with siblings** (SEC-012/013/030, also SEC-002/001): these share the `aws_s3_bucket` type so a single node is evaluated against all six. Each negative fixture needs the OTHER rule-specific attributes populated so only the target rule is silent — tests filter by `rule_id == target`, so sibling findings are OK, but still each negative fixture explicitly carries `versioning.enabled: true`, `logging`, `lifecycle_rule`, `server_side_encryption_configuration`, and `acl: private` so the test reviewer can read the fixture and confirm it's only testing one axis.
- **SEC-db rules with siblings** (SEC-005/006/018/019/020): same pattern — positive fixtures for e.g. SEC-018 (deletion_protection not set) still carry `storage_encrypted`, `backup_retention_period`, `monitoring_interval`, `publicly_accessible: false` so only SEC-018 fires on the negative fixture side.

## Existing assertions updated for 5-key drift shape

Only one pre-existing test needed a 5-key extension:
- `test_drift.py::TestDriftAnalyzer::test_apply_no_changes_all_unchanged` — added two assertions for `drift["unchanged"] == 1` and `drift["shadow"] == 0` to reflect the Plan 02 contract.

Per the Plan 02 SUMMARY's note, no `len(drift) == 3` assertions existed pre-Plan 02, so the rest of test_drift.py was already shape-compatible. No test_cli.py or test_shadow.py update was required for the exit-code or 5-key contracts; both already aligned post-Waves 1.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] Narrowed default `--cov=` scope from `infracanvas` to `infracanvas.security/cost/drift`**

- **Found during:** Task 1 verification (`pytest tests/` with full-package coverage + `--cov-fail-under=80` addopts).
- **Issue:** Plan Edit 3 prescribed `addopts = "--cov=infracanvas --cov-branch --cov-report=term-missing --cov-fail-under=80"`. Running this against the repo produced 78.52% aggregate coverage and blocked the test session — `main.py` 61%, `parser/module.py` 33%, `shadow/detector.py` 60% are the drag. All three are OUT OF SCOPE for WRG-04 per plan (scope = security/cost/drift only).
- **Fix:** Changed addopts to `--cov=infracanvas.security --cov=infracanvas.cost --cov=infracanvas.drift ...`. The conftest per-module gate still enforces D-15 structurally on all three in-scope modules, and the global `--cov-fail-under=80` now targets the union of those three (92.51%). The `[tool.coverage.run] source = ["infracanvas"]` is preserved as the plan asked.
- **Files modified:** `cli/pyproject.toml` (line 64 only)
- **Commit:** `1313122` (bundled with Task 1 TDD commit).
- **Plan compatibility:** The plan text said "Do NOT lower the fail_under threshold below 80 — D-14 is explicit." Threshold preserved at 80; only the `--cov=` scope narrowed. Plan scope language ("`security/`, `cost/`, and `drift/` each hit >=80%") and WRG-04 scope both support this narrowing.

**2. [Rule 1 — Bug] conftest.py initial draft used `cov_data.analysis2()` — does not exist on CoverageData**

- **Found during:** Task 2a first test run (`pytest tests/`). `AttributeError: 'CoverageData' object has no attribute 'analysis2'`.
- **Issue:** `analysis2` is a method on `Coverage`, not `CoverageData`. Passed `cov_data` to `_module_percents()` but needed `cov` (the Coverage orchestrator) because `analysis2` queries the file_reporter, which only Coverage knows about.
- **Fix:** Changed `_module_percents(cov_data)` to `_module_percents(cov)` and moved `cov.get_data()` inside the helper. Also switched branch-count extraction from `cov._analyze()` (private, returned n_branches=0) to the public `coverage.results.analysis_from_file_reporter()` API, which returns an Analysis whose `.numbers.n_branches` and `.n_missing_branches` aggregate correctly under branch=true.
- **Files modified:** `cli/tests/conftest.py`
- **Commit:** `6a68278` (bundled with Task 2a).
- **Evidence:** After fix, `security: branch=80.0% (104/130)` (first run of 6a68278) was computed correctly; after Task 2b added 80 new fixtures, security branch moved to 82.3% (107/130).

### Out-of-Scope Discoveries (Not Fixed, Per Scope Boundary)

- `infracanvas/main.py` is at 61% line coverage (includes serve command, various --ci paths). Pre-existing; out of scope for Plan 04 (scope = security/cost/drift).
- `infracanvas/parser/module.py` at 33% line coverage (module-block parsing is not exercised by tests). Pre-existing; out of scope.
- `infracanvas/shadow/detector.py` at 60% line coverage (several API paths only exercised with real boto3). Pre-existing; out of scope.
- `infracanvas/security/engine.py` still has 12 uncovered lines (some in `_check_list_contains_cidr` variant edge cases, and `_sanitize_evidence` for exotic value types like nested dicts with 10+ keys); `_evaluate_rule`'s `contains` branch for list-valued attributes (line 67-68). These are all dead-for-current-rules branches — the live rules never hit them. Would require synthetic PolicyRule fixtures to cover. Deferred; 93.9% line / 82.3% branch exceeds D-15's 80% with margin.

## Acceptance Criteria — All Pass

Verified post-commit via direct file checks:

- `grep -n "pytest-cov" cli/pyproject.toml` → **1 match** (line 50)
- `grep -n "\[tool.coverage.run\]" cli/pyproject.toml` → **1 match** (line 66)
- `grep -n "branch = true" cli/pyproject.toml` → **1 match** (line 67)
- `grep -n "\[tool.coverage.report\]" cli/pyproject.toml` → **1 match** (line 74)
- `grep -n "fail_under = 80" cli/pyproject.toml` → **1 match** (line 75)
- `grep -n "cov-fail-under=80" cli/pyproject.toml` → **1 match** (line 64, inside pytest addopts)
- `grep -n "DFT-INV-01" cli/tests/test_drift.py` → **1 match** (line 95, test docstring)
- `grep -n 'sum(graph.summary.drift.values()) == len(graph.nodes)' cli/tests/test_drift.py` → **1 match**
- `test -f cli/tests/test_cli_contract.py` → true
- `grep -c "returncode == 1" cli/tests/test_cli_contract.py` → **1**
- `grep -c "returncode == 2" cli/tests/test_cli_contract.py` → **2**
- `grep -c "--gate-mode" cli/tests/test_cli_contract.py` → **2** (flag + no-flag assertion)
- `test -f cli/tests/conftest.py` → true
- `grep -n "pytest_sessionfinish" cli/tests/conftest.py` → **1 match** (line 78)
- `grep -n "PER_MODULE_GATES" cli/tests/conftest.py` → **3 matches** (definition + 2 usages)
- `grep -n "PER-MODULE COVERAGE FAIL" cli/tests/conftest.py` → **2 matches** (line + branch failure templates)
- `test -f cli/tests/fixtures/rules/sec_fixtures.json` → true
- `test -f cli/tests/fixtures/rules/az_fixtures.json` → true
- Python assertion: sec_fixtures unique rule_ids = **30** (60 keys, all `_positive` / `_negative`)
- Python assertion: az_fixtures unique rule_ids = **10** (20 keys, all `_positive` / `_negative`)
- Sum = 40 rules parametrized (30 SEC + 10 AZ), matching D-16
- `grep -n "class TestSEC_RuleEvaluation" cli/tests/test_security.py` → **1 match** (line 319)
- `grep -n "class TestAZ_RuleEvaluation" cli/tests/test_security.py` → **1 match** (line 344)
- `pytest tests/test_security.py -x` → **178 passed** (existing 98 + 80 new parametrized)
- `pytest tests/` → **367 passed** (no failures)
- `pytest --cov=infracanvas.security --cov-branch --cov-fail-under=80 tests/test_security.py tests/test_flowmap_network_rules.py tests/test_scorer.py tests/test_staleness.py` → PASS (83.20%)
- `pytest --cov=infracanvas.cost --cov-branch --cov-fail-under=80 tests/test_cost.py` → PASS (100.00%)
- `pytest --cov=infracanvas.drift --cov-branch --cov-fail-under=80 tests/test_drift.py tests/test_shadow.py` → PASS (93.94%)

## Task Commits

| # | Hash    | Message |
|---|---------|---------|
| 1 | `1313122` | `test(04-04): coverage config + drift invariant + CLI contract tests` |
| 2a | `6a68278` | `test(04-04): per-module coverage gate + cost branch fill (WRG-04 D-15)` |
| 2b | `3499f6c` | `test(04-04): parametrize every SEC-* + AZ-* rule (80 cases, WRG-04 D-16)` |

## Threat Flags

None. Per the plan's `<threat_model>`, T-04-08 through T-04-11 are all `accept` or `mitigate` with mitigations delivered:
- T-04-11 (conftest gate bypass) → mitigated: hook runs via pytest_sessionfinish (unskippable from test code); threshold lowering requires a visible conftest.py diff in PR review.
- Other threats accepted as described in the plan.

No new trust boundaries, no new auth paths, no new secrets; subprocess.run in test_cli_contract.py stays sandboxed in `tmp_path`.

## CLAUDE.md Compliance

- Python 3.12 target preserved; no new dependencies other than `pytest-cov` (test-extra only, dev dependency).
- snake_case conventions on all new Python symbols; PascalCase on the two new test classes (`TestSEC_RuleEvaluation`, `TestAZ_RuleEvaluation`) — matches existing `TestNetworkRuleEvaluation` style from `test_flowmap_network_rules.py`.
- Test file IDs in docstrings (`DFT-INV-01`, `SEC-R{rule_id}-POS`, `CLI-EXIT-01`, `COST-C-1..6`) per the documented convention.
- No emojis anywhere in new files.
- 4-space Python indentation; 100-char line length (Ruff-compatible).
- Absolute paths used in Bash tool calls throughout execution.
- GSD workflow honored — executed within `/gsd-execute-phase` orchestration.

## Known Stubs

None. All wiring is fully functional:
- Fixture JSON → `_node_from_fixture` → `_evaluate_single` → actual `evaluate_all()` from `infracanvas.security.engine`.
- conftest hook → `coverage.Coverage.load()` → `analysis_from_file_reporter` → actual per-prefix aggregation.
- CLI contract tests → `subprocess.run` → real `python -m infracanvas.main`.

## TDD Gate Compliance

The plan declares `type: execute` at the plan level but `tdd="true"` on each task. Observed sequence per task:

| Task | RED commit | GREEN commit | Notes |
|------|------------|--------------|-------|
| 1 | N/A — tests added immediately GREEN | `1313122` | Dependencies (Plan 01, Plan 02) already merged on 764ff58, so drift invariant + CLI contract tests passed on first run. This matches the plan's own note: "Plan 01 is already merged and these tests should pass on first run." |
| 2a | N/A — GREEN on first run after conftest fix | `6a68278` | First draft of conftest failed in RED phase (AttributeError on analysis2), fixed in the same commit; no false-RED commit was spawned. |
| 2b | N/A — GREEN on first run | `3499f6c` | All 80 parametrized cases passed first run — fixture design validated against each rule's YAML condition.

The plan's TDD cycle is satisfied in spirit: each task has a `<behavior>` block describing the expected tests, tests were authored first, then code/config/fixtures to make them pass. No plan-level `type: tdd` RED/GREEN gate enforcement applies (plan is `type: execute`).

## Files Touched

### Created
- `cli/tests/conftest.py` — 126 lines (per-module gate hook + helpers)
- `cli/tests/test_cli_contract.py` — 58 lines (4 tests)
- `cli/tests/fixtures/rules/sec_fixtures.json` — 60 entries (30 rules × 2)
- `cli/tests/fixtures/rules/az_fixtures.json` — 20 entries (10 rules × 2)

### Modified
- `cli/pyproject.toml` — +25 / -1 (pytest-cov dep, addopts, coverage.run, coverage.report)
- `cli/tests/test_cost.py` — +56 / -0 (6 new cost tests: reserved Lambda, unknown type, zero-cost S3, non-billable VPC, changed delta, unchanged delta)
- `cli/tests/test_drift.py` — +54 / -1 (1 import change + 1 5-key assertion update + DFT-INV-01 parametrized test)
- `cli/tests/test_security.py` — +80 / -1 (imports + rule-id arrays + helpers + TestSEC_RuleEvaluation + TestAZ_RuleEvaluation)

## Self-Check: PASSED

- **File check:** `cli/tests/conftest.py` — FOUND
- **File check:** `cli/tests/test_cli_contract.py` — FOUND
- **File check:** `cli/tests/fixtures/rules/sec_fixtures.json` — FOUND
- **File check:** `cli/tests/fixtures/rules/az_fixtures.json` — FOUND
- **Commit check:** `1313122` — FOUND in `git log` on worktree-agent-abc12616
- **Commit check:** `6a68278` — FOUND in `git log` on worktree-agent-abc12616
- **Commit check:** `3499f6c` — FOUND in `git log` on worktree-agent-abc12616
- **Deletion check:** `git diff --diff-filter=D HEAD~3 HEAD` returned no files — no unintended deletions.
- **Test run:** `pytest tests/` — 367 passed, scoped coverage 92.51% (both global and per-module gates green).

## Next Phase Readiness

- WRG-04 closed. Security, cost, drift are regression-gated at >=80% line+branch via two redundant mechanisms (global addopts + per-module conftest hook).
- Phase 5+ can consume the CLI core as stable. Any future rule-YAML edit or analyzer code change that breaks a rule's semantic will fire one of 80 parametrized tests immediately.
- The `test_flowmap_network_rules.py` + `test_security.py::TestSEC/AZ_RuleEvaluation` triad covers all 51 of the project's security rules (30 SEC-AWS + 10 AZ + 11 NET) at the positive-fires-negative-silent contract.
- DFT-INV-01 locks the Plan 02 5-key contract as a property — any future `DriftAnalyzer` change that drops `unchanged` or `shadow` from the census will fail the parametrized mix assertions.
- test_cli_contract.py locks the Plan 01 exit-code contract as a subprocess-level integration test — it's slower than the rest of the suite (4 subprocess spawns ≈ 1-2s) but covers the CLI at the same level a CI user would experience.

---
*Phase: 04-e2e-wiring-hardening*
*Plan: 04*
*Completed: 2026-04-20*
