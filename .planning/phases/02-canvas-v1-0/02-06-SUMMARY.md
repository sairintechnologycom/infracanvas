---
phase: 02-canvas-v1-0
plan: "06"
subsystem: cli-integration
tags: [wave-3, integration, policy-engine, shadow-detection, staleness, cli-flags, python]
dependency_graph:
  requires: [02-01, 02-03, 02-04, 02-05]
  provides: [scan-pipeline-integration, policy-flag, shadow-flag, fail-on-flag]
  affects: [02-07, 02-08]
tech_stack:
  added: []
  patterns: [lazy-import-inside-condition, policy-rules-injected-to-evaluate-all, fail-on-threshold-logic]
key_files:
  created:
    - cli/tests/fixtures/policies/required_tags.yaml
    - cli/tests/test_policy.py
  modified:
    - cli/infracanvas/main.py
    - cli/tests/test_cli.py
decisions:
  - "shadow RuntimeError caught in _run_scan() with yellow Warning — keeps scan non-fatal per D-02"
  - "check_staleness() called unconditionally after evaluate_all() — staleness is always part of the pipeline, not opt-in"
  - "plan() default output renamed to infracanvas-plan.html/json per D-16 (was infracanvas-report.*)"
  - "watchdog __version__ accessed via importlib.metadata.version() — watchdog 4.x does not set module-level __version__"
metrics:
  duration: "~6 minutes"
  completed: "2026-04-16T12:04:51Z"
  tasks_completed: 3
  files_modified: 4
---

# Phase 02 Plan 06: CLI Integration — Shadow, Policy, Staleness, and New Flags Summary

Wired all Phase 2 analysis modules (shadow detection, policy engine, staleness checks) into the main scan pipeline with `--shadow`, `--policy`, and `--fail-on` CLI flags; policy findings carry `source='policy'`; CI exit code respects `--fail-on` threshold.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add --shadow, --policy, --fail-on flags and wire scan pipeline | 1454cca | cli/infracanvas/main.py |
| 2 | Policy test fixtures and integration tests | f1b3c16 | tests/fixtures/policies/required_tags.yaml, tests/test_policy.py, tests/test_cli.py |
| 3 | Verify watch mode compatible with updated pipeline (CLX-02) | b3a8709 | tests/test_cli.py |

## Verification Results

- `python -m pytest tests/test_policy.py -v`: 5 passed (all policy loader + evaluation tests)
- `python -m pytest tests/test_cli.py -v`: 25 passed (all CLI tests including new fail-on + watch mode tests)
- `python -m pytest tests/ -x -q`: 193 passed, 0 failed — full suite green after integration

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] watchdog `__version__` not available on module**
- **Found during:** Task 3
- **Issue:** `assert hasattr(watchdog, '__version__')` failed — watchdog 4.x does not expose a `__version__` attribute on the package module object
- **Fix:** Replaced with `importlib.metadata.version("watchdog")` which correctly retrieves the installed package version
- **Files modified:** cli/tests/test_cli.py
- **Commit:** b3a8709

## Known Stubs

None — all three integration paths are fully wired:
- `--shadow` creates a `ShadowDetector` per call and runs `detect(graph)`
- `--policy` calls `load_policy_rules(policy)` and passes results to `evaluate_all(policy_rules=...)`
- `check_staleness(graph)` runs unconditionally after `evaluate_all()` in every scan

## Threat Flags

None. Threat mitigations per T-02-12 and T-02-14 are both handled by existing code:
- T-02-12 (path traversal): `load_policy_rules()` already checks `policy_dir.is_dir()` before rglob, and uses `yaml.safe_load()`
- T-02-14 (invalid --fail-on): `sev_order.index(threshold)` raises `ValueError` on invalid input, which Typer surfaces as a CLI error

## Self-Check: PASSED

- [x] cli/infracanvas/main.py `scan()` has `--shadow`, `--policy`, `--fail-on` parameters
- [x] cli/infracanvas/main.py `_run_scan()` calls `ShadowDetector` when `shadow=True`
- [x] cli/infracanvas/main.py `_run_scan()` calls `load_policy_rules()` when `policy` is not None
- [x] cli/infracanvas/main.py `_run_scan()` calls `check_staleness(graph)` after `evaluate_all`
- [x] cli/infracanvas/main.py `scan()` CI exit logic uses `fail_on` parameter
- [x] cli/infracanvas/main.py `plan()` default output is `infracanvas-plan.html`
- [x] Shadow `RuntimeError` caught with yellow warning
- [x] cli/tests/fixtures/policies/required_tags.yaml has POL-001 and POL-002
- [x] cli/tests/test_policy.py has 5 tests across 2 classes
- [x] cli/tests/test_cli.py has TestFailOnFlag (2 tests) and TestWatchMode (2 tests)
- [x] All 193 tests pass
- [x] Commit 1454cca exists (Task 1)
- [x] Commit f1b3c16 exists (Task 2)
- [x] Commit b3a8709 exists (Task 3)
