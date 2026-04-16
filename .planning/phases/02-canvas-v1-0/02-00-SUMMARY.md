---
phase: 02-canvas-v1-0
plan: "00"
subsystem: test-infrastructure
tags: [wave-0, test-stubs, python, typescript, tdd]
dependency_graph:
  requires: []
  provides: [test-stubs-wave0]
  affects: [02-01, 02-02, 02-03, 02-04, 02-05, 02-06, 02-07, 02-08]
tech_stack:
  added: []
  patterns: [pytest.mark.skip, vitest test.skip]
key_files:
  created:
    - cli/tests/test_azure_parser.py
    - cli/tests/test_shadow.py
    - cli/tests/test_staleness.py
    - cli/tests/test_policy.py
    - viewer/src/__tests__/ResourceNode.test.tsx
    - viewer/src/__tests__/DetailPanel.test.tsx
  modified:
    - cli/tests/test_cost.py
decisions: []
metrics:
  duration: "~4 minutes"
  completed: "2026-04-16T10:54:31Z"
  tasks_completed: 2
  files_modified: 7
---

# Phase 02 Plan 00: Wave 0 Test Stubs Summary

Wave 0 test stubs created for all new Python and TypeScript test modules required by the Nyquist validation strategy — all stubs are skipped so the suite stays green before implementation begins.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create Python test stub files | 037ae23 | test_azure_parser.py, test_shadow.py, test_staleness.py, test_policy.py, test_cost.py |
| 2 | Create viewer test stub files | 2bc651a | ResourceNode.test.tsx, DetailPanel.test.tsx |

## Verification Results

- Python: `162 passed, 27 skipped` — all new stubs collected and skipped, no failures
- Viewer: `30 passed, 9 skipped` — all new stubs collected and skipped, no failures

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical functionality] Added `import pytest` to test_cost.py**
- **Found during:** Task 1
- **Issue:** The existing test_cost.py had no `import pytest` statement, but the new stub classes use `@pytest.mark.skip` decorator
- **Fix:** Added `import pytest` at the top of test_cost.py before the new stubs
- **Files modified:** cli/tests/test_cost.py
- **Commit:** 037ae23

## Known Stubs

All files in this plan ARE stubs by design. They are intentional Wave 0 placeholders. Implementation plans 02-08 will replace stub bodies with real test logic.

| File | Purpose | Resolved By |
|------|---------|-------------|
| cli/tests/test_azure_parser.py | Azure parser tests | Plan 02 |
| cli/tests/test_shadow.py | Shadow detector tests | Plan 04 |
| cli/tests/test_staleness.py | Staleness check tests | Plan 03 |
| cli/tests/test_policy.py | Policy engine tests | Plan 06 |
| cli/tests/test_cost.py (new classes) | Region multiplier + group cost tests | Plan 05 |
| viewer/src/__tests__/ResourceNode.test.tsx | Azure icon rendering tests | Plan 07 |
| viewer/src/__tests__/DetailPanel.test.tsx | ChangesTab and FindingCard tests | Plan 07 |

## Threat Flags

None — test-only files with skip markers, no runtime logic.

## Self-Check: PASSED

- [x] cli/tests/test_azure_parser.py exists
- [x] cli/tests/test_shadow.py exists
- [x] cli/tests/test_staleness.py exists
- [x] cli/tests/test_policy.py exists
- [x] cli/tests/test_cost.py modified (stubs appended)
- [x] viewer/src/__tests__/ResourceNode.test.tsx exists
- [x] viewer/src/__tests__/DetailPanel.test.tsx exists
- [x] Commit 037ae23 exists (Python stubs)
- [x] Commit 2bc651a exists (Viewer stubs)
