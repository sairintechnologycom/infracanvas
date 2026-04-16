---
phase: 02-canvas-v1-0
plan: "05"
subsystem: cost-estimation
tags: [wave-2, cost, region-multipliers, group-aggregation, python]
dependency_graph:
  requires: [02-00, 02-01]
  provides: [region-aware-cost, group-cost-aggregation]
  affects: [02-06, 02-07, 02-08]
tech_stack:
  added: []
  patterns: [region-multiplier-dict, metadata-side-channel-for-group-costs]
key_files:
  created: []
  modified:
    - cli/infracanvas/cost/estimator.py
    - cli/tests/test_cost.py
decisions:
  - "REGION_MULTIPLIERS uses human-readable names for Azure ('East US') alongside AWS region codes ('us-east-1') — both must be present since provider determines the format"
  - "Group costs stored in graph.metadata['group_costs'] rather than a new GraphSummary field — avoids model change and stays backwards compatible with viewer"
  - "Infracost API deferred per CONTEXT.md — static pricing remains the primary source (CST-01)"
metrics:
  duration: "~6 minutes"
  completed: "2026-04-16T11:12:21Z"
  tasks_completed: 1
  files_modified: 2
---

# Phase 02 Plan 05: Multi-Region Cost Estimation and Group Aggregation Summary

Extended CostEstimator with a 15-entry REGION_MULTIPLIERS dict (AWS + Azure) and group-level cost aggregation into graph.metadata, satisfying CST-01/02/03 with static pricing as primary fallback.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add region multipliers and group-level cost aggregation | 26f486e | cost/estimator.py, tests/test_cost.py |

## Verification Results

- `python -m pytest tests/test_cost.py -x -q`: 12 passed (8 existing + 4 new)
- `REGION_MULTIPLIERS` has 15 entries — assertion passed
- Group costs appear in `graph.metadata["group_costs"]` — confirmed by TestGroupCostAggregation

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — REGION_MULTIPLIERS is wired into estimate(), group costs flow into metadata.

## Threat Flags

None. T-02-11 accepted per threat register: region comes from user's own .tf files, incorrect region produces incorrect cost only — no security impact.

## Self-Check: PASSED

- [x] cli/infracanvas/cost/estimator.py contains `REGION_MULTIPLIERS` dict with 15 entries (>= 10)
- [x] cli/infracanvas/cost/estimator.py `estimate()` applies `REGION_MULTIPLIERS.get(node.region, 1.0)`
- [x] cli/infracanvas/cost/estimator.py `estimate()` populates `graph.metadata["group_costs"]`
- [x] cli/tests/test_cost.py has TestRegionMultiplier class with 3 tests (no longer skipped)
- [x] cli/tests/test_cost.py has TestGroupCostAggregation class with 1 test (no longer skipped)
- [x] All 12 cost tests pass
- [x] Commit 26f486e exists (Task 1)
