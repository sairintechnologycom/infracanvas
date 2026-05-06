---
phase: 09-costlens
plan: "02"
subsystem: cli-costlens
tags: [costlens, pydantic, allocator, cost, python]
dependency_graph:
  requires:
    - 09-01  # test stubs + shadcn badge/tooltip
  provides:
    - CostLensData family of Pydantic models in models.py
    - CostLensConfig in config.py
    - SharedCostAllocator with equal-split allocation
    - 4 new FLAT_MONTHLY entries in estimator.py
    - idle.py + egress.py importable stubs for Plans 03/04
  affects:
    - cli/infracanvas/graph/models.py
    - cli/infracanvas/config.py
    - cli/infracanvas/cost/estimator.py
    - cli/infracanvas/cost/allocator.py
    - cli/tests/test_costlens.py
tech_stack:
  added:
    - "SharedCostAllocator (cli/infracanvas/cost/allocator.py)"
    - "CostLensConfig nested Pydantic model in config.py"
  patterns:
    - "_split_percentages() rounding guarantee: base=round(100/n,4), remainder distributed to first"
    - "node_by_id dict pre-built before O(n) edge traversal (T-09-02-03 mitigation)"
    - "CostLensData | None = None forward reference in ResourceGraph (Pydantic v2 lazy annotations)"
key_files:
  created:
    - cli/infracanvas/cost/allocator.py
    - cli/infracanvas/cost/idle.py
    - cli/infracanvas/cost/egress.py
  modified:
    - cli/infracanvas/graph/models.py
    - cli/infracanvas/config.py
    - cli/infracanvas/cost/estimator.py
    - cli/tests/test_costlens.py
decisions:
  - "CostLensData and PathCost defined after ResourceGraph/NetworkPath in models.py — Pydantic v2 with `from __future__ import annotations` resolves forward references lazily; no model_rebuild() call needed"
  - "idle.py and egress.py created as importable stubs in Plan 02 so test_costlens.py can be collected; Plans 03/04 will implement the real classes replacing the NotImplementedError stubs"
  - "_split_percentages() uses round(100/n, 4) base + distributes float remainder to first element — guarantees sum within 0.001 of 100.0 for any n"
  - "Dedicated (non-shared) untagged resources are excluded from workload totals (wl_name == 'untagged' → skip); only tagged dedicated resources are attributed"
metrics:
  duration: "243 seconds"
  completed_date: "2026-05-06"
  tasks_completed: 2
  files_changed: 7
  tests_added: 9
  tests_status: "356 passed, 9 xfailed (Plans 03/04 RED stubs)"
---

# Phase 9 Plan 02: CostLens Data Models + SharedCostAllocator Summary

**One-liner:** Pydantic CostLensData family + SharedCostAllocator with equal-split rounding guarantee, turning 9 RED test stubs into GREEN for CLA-01..04.

## What Was Built

### Task 1 — Data Models + Config Extension (commit 22e4600)

**cli/infracanvas/graph/models.py** — Added 6 new Pydantic models after `ResourceGraph`:

- `CostLineItem` — single cost line with resource_id, resource_type, label, monthly_usd, share_pct
- `WorkloadCost` — workload with name, total_monthly_usd, list[CostLineItem]
- `SharedResourceSummary` — shared resource summary with workload_count
- `IdleRecommendation` — idle resource with description and monthly_waste_usd
- `CostLensData` — root allocation result: workloads + shared_resources + recommendations
- `PathCost` — egress cost with rate_per_gb, assumed_gb, basis (for Plan 04/CPC-01)

Also added:
- `costlens: CostLensData | None = None` field to `ResourceGraph`
- `path_cost: PathCost | None = None` field to `NetworkPath`

**cli/infracanvas/config.py** — Added `CostLensConfig(workload_tag_key='Service')` and `costlens: CostLensConfig = Field(default_factory=CostLensConfig)` to `InfraCanvasConfig`. Backward compatible — existing configs without `costlens:` key get default values via Pydantic v2 `model_validate`.

### Task 2 — FLAT_MONTHLY + Allocator + Tests GREEN (commit 741774a)

**cli/infracanvas/cost/estimator.py** — Added 4 new FLAT_MONTHLY entries:
- `aws_ec2_transit_gateway`: $36.50/mo (0.05 * 730)
- `aws_vpc_endpoint`: $7.30/mo (0.01 * 730)
- `azurerm_express_route_circuit`: $55.00/mo flat
- `azurerm_firewall`: $912.50/mo (1.25 * 730)

**cli/infracanvas/cost/allocator.py** — `SharedCostAllocator` class:
- `SHARED_TYPES` frozenset with 5 shared resource types
- `_workload_name()` — reads tag by key, defaults to `'untagged'`
- `_split_percentages(n)` — equal split with float remainder on first element (rounding guarantee)
- `allocate(graph)` — O(n) node_by_id dict + edge traversal; produces `CostLensData`

**cli/infracanvas/cost/idle.py** + **egress.py** — Importable stubs with `NotImplementedError` so `test_costlens.py` can be collected by pytest. Plans 03/04 will replace these.

**cli/tests/test_costlens.py** — All 9 `TestSharedAllocator` xfail stubs replaced with full implementations (CLA-C-1..9).

## Test Results

```
356 passed, 9 xfailed in 21.87s
Coverage: 92.32% (above 80% gate)
```

CLA-C-1..9 all GREEN. The 9 xfailed are `TestIdleDetector` (CLA-C-10..15) and `TestEgressEstimator` (CPC-C-1..3) — Plans 03/04 RED stubs.

## Deviations from Plan

None — plan executed exactly as written.

The pre-existing `test_cli.py` failure (`CliRunner.__init__() got an unexpected keyword argument 'mix_stderr'`) was confirmed pre-existing before this plan and is out of scope per SCOPE BOUNDARY rule. Tests were run with `--ignore=tests/test_cli.py` for the full-suite pass verification.

## Known Stubs

- `cli/infracanvas/cost/idle.py` — `IdleDetector.detect()` raises `NotImplementedError`. Intentional stub; Plan 03 will implement.
- `cli/infracanvas/cost/egress.py` — `EgressEstimator.estimate()` raises `NotImplementedError`. Intentional stub; Plan 04 will implement.
- `CostLensData.recommendations` is always `[]` after `SharedCostAllocator.allocate()` — `IdleDetector` in Plan 03 populates this.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries introduced. All changes are purely Python in-process Pydantic models and allocation logic.

## Self-Check: PASSED

| Check | Result |
|-------|--------|
| cli/infracanvas/cost/allocator.py exists | FOUND |
| cli/infracanvas/cost/idle.py exists | FOUND |
| cli/infracanvas/cost/egress.py exists | FOUND |
| .planning/phases/09-costlens/09-02-SUMMARY.md exists | FOUND |
| commit 22e4600 exists | FOUND |
| commit 741774a exists | FOUND |
| CLA-C-1..9 all GREEN | 9/9 passed |
| Full test suite | 356 passed, 9 xfailed |
