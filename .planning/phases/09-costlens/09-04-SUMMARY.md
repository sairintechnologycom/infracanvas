---
phase: 09-costlens
plan: "04"
subsystem: cli-costlens
tags: [costlens, egress-estimator, cross-cloud, python, tdd, cpc-01]
dependency_graph:
  requires:
    - 09-01  # test stubs + shadcn badge/tooltip
    - 09-02  # CostLensData models + SharedCostAllocator + PathCost/NetworkPath.path_cost
    - 09-03  # IdleDetector + main.py CostLens pipeline wiring
  provides:
    - EgressEstimator class with static AWS + Azure + cross-cloud egress pricing tables
    - NetworkPath.path_cost populated for paths with identifiable region data
    - PathCost.basis always contains "estimated at 100 GB/mo (no flow data)" disclaimer
    - EgressEstimator wired into main.py CostLens pipeline at both score() and plan() callsites
    - CPC-C-1..3 GREEN (were xfail RED stubs from Plan 01)
  affects:
    - cli/infracanvas/cost/egress.py
    - cli/infracanvas/main.py
    - cli/tests/test_costlens.py
tech_stack:
  added:
    - "EgressEstimator (cli/infracanvas/cost/egress.py) — topology-based cross-cloud egress cost estimation"
  patterns:
    - "Static pricing tables: AWS_EGRESS_RATES (12 region pairs), AZURE_EGRESS_RATES (4 pairs), CROSS_CLOUD_EGRESS=0.09"
    - "_normalize_region() strips/lowercases for T-09-04-01 (adversarial region strings from HCL)"
    - "_is_cross_cloud() detects AWS<->Azure boundary via provider field AND type prefix (covers both)"
    - "node_by_id.get(id) returns None for missing nodes — path_cost=None graceful skip (T-09-04-04)"
    - "BASIS_NOTE hardcoded disclaimer: 'estimated at 100 GB/mo (no flow data — enable flow logs for actuals)'"
    - "inline import inside try block in main.py with noqa: PLC0415 — matches Plan 03 pattern"
key_files:
  created:
    - cli/infracanvas/cost/egress.py  # was stub — fully implemented
  modified:
    - cli/infracanvas/main.py
    - cli/tests/test_costlens.py
decisions:
  - "CPC-02 (flow-log-driven attribution) remains deferred to Phase 12 per D-09 — EgressEstimator uses static 100 GB/mo assumed volume only"
  - "_is_cross_cloud() checks BOTH provider field AND resource type prefix — handles cases where provider='aws' but type starts 'azurerm_' (edge case from Terraform aliasing)"
  - "DEFAULT_EGRESS_RATE=0.09 used for all unknown region pairs — conservative fallback matches AWS internet egress rate; safe estimate for the disclaimer"
  - "Bidirectional table lookup: tries 'src:dst' then 'dst:src' so table keys only need one direction per pair"
  - "EgressEstimator placed AFTER IdleDetector in main.py pipeline — both run inside the same non-fatal try/except; order: allocator → detector → egress"
metrics:
  duration: "420 seconds"
  completed_date: "2026-05-06"
  tasks_completed: 2
  files_changed: 3
  tests_added: 3
  tests_status: "365 passed (was 362 passed + 3 xfailed — CPC-C-1..3 now GREEN)"
---

# Phase 9 Plan 04: EgressEstimator + CPC-01 Summary

**One-liner:** Topology-based cross-cloud egress cost estimator with static AWS/Azure pricing tables annotating NetworkPath.path_cost at 100 GB/mo assumed volume, wired into main.py CostLens pipeline.

## What Was Built

### Task 1 — EgressEstimator + CPC-C-1..3 GREEN (commits b4c19c1 RED, 7b2d9b4 GREEN)

**cli/tests/test_costlens.py** — Replaced 3 xfail stubs with real test bodies (CPC-C-1..3):

- Added `from infracanvas.graph.models import NetworkPath` and changed `EgressEstimator` import from `noqa: F401` stub to real import
- `test_inter_region_aws_rate` (CPC-C-1): us-east-1 → eu-west-1 path → `rate_per_gb == 0.02`, `estimated_monthly_usd == 2.0`
- `test_cross_cloud_rate` (CPC-C-2): AWS TGW → Azure ExpressRoute path → `rate_per_gb == 0.09`, `"100 GB/mo" in basis`
- `test_no_region_data_graceful` (CPC-C-3): nodes with empty attributes → `path_cost is None` (no exception)

**cli/infracanvas/cost/egress.py** — Full `EgressEstimator` replacing the `NotImplementedError` stub:

Pricing tables:
- `AWS_EGRESS_RATES` — 12 region pairs covering US, EU, AP inter-region traffic (0.01–0.09 $/GB)
- `AZURE_EGRESS_RATES` — 4 zone-1 region pairs (eastus, westeurope, southeastasia, 0.05–0.08 $/GB)
- `CROSS_CLOUD_EGRESS = 0.09` — AWS ↔ Azure via Internet
- `DEFAULT_EGRESS_RATE = 0.09` — fallback for all unknown region pairs
- `ASSUMED_MONTHLY_GB = 100.0` — assumed volume (CPC-02 deferred)
- `BASIS_NOTE = "estimated at 100 GB/mo (no flow data — enable flow logs for actuals)"`

Helper functions:
- `_normalize_region(region)` — strips whitespace + lowercases (T-09-04-01: adversarial HCL attribute mitigation)
- `_get_node_region(node)` — checks `node.attributes["region"]` (AWS) then `node.attributes["location"]` (Azure)
- `_is_cross_cloud(src, dst)` — checks `provider` field AND `type` prefix for AWS/azurerm boundary
- `_lookup_rate(src, dst, cross_cloud)` — bidirectional lookup in AWS then Azure tables; fallback to default

`EgressEstimator.estimate(graph)`:
- Returns graph immediately when `graph.network_paths` is empty
- Builds `node_by_id` dict once before the loop
- For each path: resolves nodes, extracts regions, sets `path_cost = None` for missing nodes/regions
- For resolved paths: calls `_is_cross_cloud` + `_lookup_rate` + creates `PathCost(estimated_monthly_usd, rate_per_gb, assumed_gb, basis)`

### Task 2 — Wire EgressEstimator into main.py (commit b0cf9a6)

**cli/infracanvas/main.py** — EgressEstimator added to both CostLens wiring blocks:

1. `score()` function (~line 698): after `graph = _detector.detect(graph)`
2. `plan()` function (~line 820): after `graph = _detector.detect(graph)`

Both blocks now follow the pipeline:
```python
from infracanvas.cost.egress import EgressEstimator  # noqa: PLC0415
...
_egress = EgressEstimator()
graph = _egress.estimate(graph)
```

Inside the existing non-fatal `try/except Exception as exc` — scan continues on CostLens error.

## Test Results

```
365 passed in 21.02s
Coverage: 91.85% (above 80% gate)
```

CPC-C-1..3 all GREEN. Previous 362 passed + 3 xfailed = now 365 passed (3 xfails became real passes).

## TDD Gate Compliance

| Gate | Commit | Status |
|------|--------|--------|
| Task 1 RED | b4c19c1 | `test(09-04): add failing tests CPC-C-1..3 EgressEstimator RED` — 3 FAIL (NotImplementedError) |
| Task 1 GREEN | 7b2d9b4 | `feat(09-04): implement EgressEstimator CPC-01 GREEN` — 3 PASS |

## Deviations from Plan

None — plan executed exactly as written.

**Note on test_cli.py:** Pre-existing collection error (`CliRunner.__init__() got an unexpected keyword argument 'mix_stderr'`) was present before Plan 04. Full suite run uses `--ignore=tests/test_cli.py` consistent with Plan 03's 362-test run. Scope boundary applies — not fixed here.

## Known Stubs

None. `EgressEstimator` is fully implemented. CPC-02 (flow-log attribution) is intentionally deferred to Phase 12 per D-09 — the `BASIS_NOTE` disclaimer makes this explicit to users.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries. All changes are Python in-process (EgressEstimator static table lookup + main.py pipeline wiring). T-09-04-01..04 mitigations all applied:

- T-09-04-01 (region string tampering): `_normalize_region()` strips/lowercases; table miss → DEFAULT_EGRESS_RATE
- T-09-04-02 (PathCost.basis disclosure): hardcoded disclaimer constant — no sensitive data
- T-09-04-03 (outdated rates): BASIS_NOTE explicitly labels as estimate
- T-09-04-04 (missing node IDs): `node_by_id.get(id)` → None → `path_cost = None`

## Self-Check: PASSED

| Check | Result |
|-------|--------|
| cli/infracanvas/cost/egress.py exists with EgressEstimator | FOUND |
| `grep -c "class EgressEstimator" egress.py` == 1 | PASS (1) |
| `grep -c "CROSS_CLOUD_EGRESS" egress.py` >= 1 | PASS (2) |
| `grep -c "path_cost = None" egress.py` >= 1 | PASS (2) |
| `grep -c "EgressEstimator" main.py` >= 2 | PASS (4) |
| commit b4c19c1 exists (Task 1 RED) | FOUND |
| commit 7b2d9b4 exists (Task 1 GREEN) | FOUND |
| commit b0cf9a6 exists (Task 2) | FOUND |
| CPC-C-1..3 all GREEN | 3/3 passed |
| Full test suite (ex. pre-existing test_cli.py error) | 365 passed |
