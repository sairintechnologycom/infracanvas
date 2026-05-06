---
phase: 9
slug: costlens
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-06
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework (CLI)** | pytest |
| **Framework (Viewer/Dashboard)** | Vitest 4.1.4 |
| **CLI config file** | `cli/pyproject.toml` |
| **Viewer config file** | `viewer/vitest.config.ts` |
| **Quick run command** | `cd cli && python -m pytest tests/test_costlens.py -x` |
| **Full suite command** | `cd cli && python -m pytest tests/ && cd ../viewer && npm test -- --run` |
| **Estimated runtime** | ~45 seconds (CLI) + ~20 seconds (viewer) |

---

## Sampling Rate

- **After every task commit:** Run `cd cli && python -m pytest tests/test_costlens.py -x && cd ../viewer && npm test -- --run`
- **After every plan wave:** Run full suite (CLI + viewer)
- **Before `/gsd-verify-work`:** Full CLI + viewer suites must be green
- **Max feedback latency:** ~65 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 9-01-01 | 01 | 0 | CLA-01..06 | — | N/A | setup | `ls cli/tests/test_costlens.py` | ❌ W0 | ⬜ pending |
| 9-01-02 | 01 | 0 | CLA-06 | — | N/A | setup | `ls dashboard/components/scans/WorkloadTable.test.tsx` | ❌ W0 | ⬜ pending |
| 9-02-01 | 02 | 1 | CLA-01 | — | N/A | unit | `pytest tests/test_costlens.py::TestSharedAllocator::test_tgw_two_workload_split -x` | ❌ W0 | ⬜ pending |
| 9-02-02 | 02 | 1 | CLA-02 | — | N/A | unit | `pytest tests/test_costlens.py::TestSharedAllocator::test_express_route_split -x` | ❌ W0 | ⬜ pending |
| 9-02-03 | 02 | 1 | CLA-03 | — | N/A | unit | `pytest tests/test_costlens.py::TestSharedAllocator::test_azure_firewall_split -x` | ❌ W0 | ⬜ pending |
| 9-02-04 | 02 | 1 | CLA-04 | — | N/A | unit | `pytest tests/test_costlens.py::TestSharedAllocator::test_nat_gateway_split -x` | ❌ W0 | ⬜ pending |
| 9-03-01 | 03 | 1 | CLA-05 | — | N/A | unit | `pytest tests/test_costlens.py::TestIdleDetector -x` | ❌ W0 | ⬜ pending |
| 9-04-01 | 04 | 1 | CPC-01 | — | N/A | unit | `pytest tests/test_costlens.py::TestEgressEstimator -x` | ❌ W0 | ⬜ pending |
| 9-05-01 | 05 | 2 | CLA-06 | — | N/A | integration | `cd viewer && npm test -- --run CostLensPanel` | ❌ W0 | ⬜ pending |
| 9-06-01 | 06 | 2 | CLA-06 | — | N/A | component | `cd dashboard && npm test -- --run WorkloadTable` | ❌ W0 | ⬜ pending |
| 9-07-01 | 07 | 2 | CPC-03 | — | N/A | component | `cd viewer && npm test -- --run PathDetailPanel` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `cli/tests/test_costlens.py` — stubs for CLA-C-1..CLA-C-15, CPC-C-1..CPC-C-3 (pytest RED stubs)
- [ ] `viewer/src/__tests__/costlens/CostLensPanel.test.tsx` — stubs for viewer CostLens rendering
- [ ] `dashboard/components/scans/WorkloadTable.test.tsx` — stubs for dashboard WorkloadTable
- [ ] `cd dashboard && npx shadcn@latest add badge tooltip` — install missing shadcn components before Wave 1 UI work

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Allocation percentages sum to 100% per shared resource | CLA (SC-4) | Requires live CLI scan against real Terraform fixture | Run `infracanvas scan fixtures/costlens/` and inspect `costlens.shared_resources[*].allocations` — sum must equal 100.0 |
| CostLens tab visible in viewer HTML report | CLA-05, CLA-06 | Requires HTML bundle build + browser render | `npm run build` in viewer, open output HTML, confirm CostLens tab is not disabled and shows workload cards |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 65s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** 2026-05-06
