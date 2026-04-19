---
phase: 3
slug: flowmap-v1-0
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-18
audited: 2026-04-19
---

# Phase 3 — Validation Strategy

> Per-phase validation contract. Audited 2026-04-19 — all Phase 3a requirements
> have automated test coverage. NET-010 (path-dependent firewall rule) is
> scope-excluded and deferred to Phase 3b.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework (CLI)** | pytest (Python 3.12+, via pyproject.toml) |
| **Framework (viewer)** | Vitest 4.1.4 + @testing-library/react 16.3.2 |
| **Config file (CLI)** | `cli/pyproject.toml` |
| **Config file (viewer)** | `viewer/vite.config.ts` |
| **Quick run command (CLI)** | `cd cli && pytest -x tests/test_flowmap_*.py tests/test_viewer_template_bundle.py` |
| **Quick run command (viewer)** | `cd viewer && npx vitest run src/__tests__/flowmap/ src/__tests__/store.test.ts src/__tests__/types.test.ts` |
| **Full suite command** | `cd cli && pytest && cd ../viewer && npx vitest run` |
| **Estimated runtime** | ~60 seconds (CLI ~30s, viewer ~30s) |

---

## Sampling Rate

- **After every task commit:** Run the relevant quick command (CLI or viewer)
- **After every plan wave:** Run the full suite
- **Before `/gsd-verify-work`:** Full suite green + bundle size check (<5MB HTML)
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

*All 3a requirements map to hermetic automated tests (no live cloud calls).*

| Task | Plan | Wave | Requirement | Test Type | Automated Command | Test File | Status |
|------|------|------|-------------|-----------|-------------------|-----------|--------|
| 03-01 T1 | Schema foundation | 1 | FDM-01, FDM-02 | unit | `pytest -x tests/test_flowmap_models.py` | `cli/tests/test_flowmap_models.py` | ✅ green |
| 03-01 T2 | TS type mirror | 1 | FDM-01, FDM-02 | unit | `npx vitest run src/__tests__/types.test.ts` | `viewer/src/__tests__/types.test.ts` | ✅ green |
| 03-01 T3 | Optional deps | 1 | FDM-02 | smoke | `grep -c "^flowmap = \[" cli/pyproject.toml && grep -c '"elkjs"' viewer/package.json` | pyproject.toml, package.json | ✅ green |
| 03-02 T1 | Orchestrator scaffold | 2 | FDM-02 | unit | `pytest -x tests/test_flowmap_cli.py` | `cli/tests/test_flowmap_cli.py` | ✅ green |
| 03-02 T2 | `--flowmap` flag | 2 | FDM-02 | unit | `pytest -x tests/test_flowmap_cli.py` | `cli/tests/test_flowmap_cli.py` | ✅ green |
| 03-02 T3 | Credential warnings | 2 | FDM-02 | unit | `pytest -x tests/test_flowmap_cli.py` | `cli/tests/test_flowmap_cli.py` | ✅ green |
| 03-03 T1 | AWS placebo fixtures | 3 | AWS-01..03 | fixture | (consumed by T3) | `cli/tests/fixtures/flowmap/aws/` | ✅ green |
| 03-03 T2 | `aws.py` collector | 3 | AWS-01..03 | unit | `pytest -x tests/test_flowmap_aws.py` | `cli/tests/test_flowmap_aws.py` | ✅ green |
| 03-03 T3 | AWS test suite | 3 | AWS-01..03 | unit | `pytest -x tests/test_flowmap_aws.py` | `cli/tests/test_flowmap_aws.py` | ✅ green |
| 03-04 T1 | Azure fixtures | 3 | AZN-01..03 | fixture | (consumed by T3) | `cli/tests/fixtures/flowmap/azure/` | ✅ green |
| 03-04 T2 | `azure.py` collector | 3 | AZN-01..03 | unit | `pytest -x tests/test_flowmap_azure.py` | `cli/tests/test_flowmap_azure.py` | ✅ green |
| 03-04 T3 | Azure test suite | 3 | AZN-01..03 | unit | `pytest -x tests/test_flowmap_azure.py` | `cli/tests/test_flowmap_azure.py` | ✅ green |
| 03-05 T1 | NET-001..012 rules | 2 | FDM-03, NFN-01 | rule YAML | (consumed by T2) | `cli/infracanvas/security/rules/network/` | ✅ green |
| 03-05 T2 | Rule engine tests | 2 | FDM-03, NFN-01 | unit | `pytest -x tests/test_flowmap_network_rules.py` | `cli/tests/test_flowmap_network_rules.py` | ✅ green |
| 03-06 T1 | Zustand tab slice | 2 | FMV-01, FMV-05 | unit | `npx vitest run src/__tests__/store.test.ts` | `viewer/src/__tests__/store.test.ts` | ✅ green |
| 03-06 T2 | TabBar component | 2 | FMV-01 | unit | `npx vitest run src/__tests__/flowmap/TabBar.test.tsx` | `viewer/src/__tests__/flowmap/TabBar.test.tsx` | ✅ green |
| 03-06 T3 | App shell swap | 2 | FMV-01 | unit | (covered by TabBar + store tests) | same as above | ✅ green |
| 03-07 T1 | FlowMapCanvas | 2 | FMV-01..04 | unit | `npx vitest run src/__tests__/flowmap/FlowMapCanvas.test.tsx` | `viewer/src/__tests__/flowmap/FlowMapCanvas.test.tsx` | ✅ green |
| 03-07 T2 | Custom nodes | 2 | FMV-01, FMV-03 | unit | `npx vitest run src/__tests__/flowmap/nodes.test.tsx` | `viewer/src/__tests__/flowmap/nodes.test.tsx` | ✅ green |
| 03-07 T3 | PathEdge (dual-color) | 2 | FMV-02 | unit | `npx vitest run src/__tests__/flowmap/PathEdge.test.tsx` | `viewer/src/__tests__/flowmap/PathEdge.test.tsx` | ✅ green |
| 03-07 T4 | elkjs layout engine | 2 | FMV-04 | unit | `npx vitest run src/__tests__/flowmap/elkLayout.test.ts` | `viewer/src/__tests__/flowmap/elkLayout.test.ts` | ✅ green |
| 03-08 T1 | FlowMapFilterPanel | 2 | FMV-05 | unit | `npx vitest run src/__tests__/flowmap/FlowMapFilterPanel.test.tsx` | `viewer/src/__tests__/flowmap/FlowMapFilterPanel.test.tsx` | ✅ green |
| 03-08 T2 | PathDetailPanel | 2 | FMV-05 | unit | `npx vitest run src/__tests__/flowmap/PathDetailPanel.test.tsx` | `viewer/src/__tests__/flowmap/PathDetailPanel.test.tsx` | ✅ green |
| 03-08 T3 | FlowMapEmptyState | 2 | FMV-05 | unit | `npx vitest run src/__tests__/flowmap/FlowMapEmptyState.test.tsx` | `viewer/src/__tests__/flowmap/FlowMapEmptyState.test.tsx` | ✅ green |
| 03-08 T4 | colors.ts + index.css | 2 | FMV-05 | visual constants | (verified via panel tests) | `viewer/src/colors.ts`, `viewer/src/index.css` | ✅ green |
| 03-09 T1 | Rebuild viewer bundle | 1 | FMV-* | artifact | `npm run build` (viewer) | `cli/infracanvas/export/viewer_template.html` | ✅ green |
| 03-09 T2 | npm postbuild sync | 1 | FMV-* | smoke | `npm run build && ls cli/infracanvas/export/viewer_template.html` | `viewer/package.json` | ✅ green |
| 03-09 T3 | Bundle regression guard | 1 | FMV-* | unit | `pytest -x tests/test_viewer_template_bundle.py` | `cli/tests/test_viewer_template_bundle.py` | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Requirements Coverage Matrix

| Requirement | Status | Evidence |
|-------------|--------|----------|
| FDM-01 | ✅ COVERED | `test_flowmap_models.py`, `types.test.ts` |
| FDM-02 | ✅ COVERED | `test_flowmap_models.py`, `test_flowmap_cli.py` |
| FDM-03 | ✅ COVERED | `test_flowmap_network_rules.py` |
| AWS-01 | ✅ COVERED | `test_flowmap_aws.py` (TGW fixtures) |
| AWS-02 | ✅ COVERED | `test_flowmap_aws.py` (VPC/NACL paths) |
| AWS-03 | ✅ COVERED | `test_flowmap_aws.py` (DX + flow-log metadata) |
| AZN-01 | ✅ COVERED | `test_flowmap_azure.py` (vWAN + vNet + NSG) |
| AZN-02 | ✅ COVERED | `test_flowmap_azure.py` (peerings + ExpressRoute) |
| AZN-03 | ✅ COVERED | `test_flowmap_azure.py` (NSG flow-log metadata) |
| NFN-01 | ✅ COVERED (11/12) | `test_flowmap_network_rules.py`. NET-010 scope-excluded (path-dependent, ships Phase 3b) |
| FMV-01 | ✅ COVERED | `FlowMapCanvas.test.tsx`, `TabBar.test.tsx`, `store.test.ts` |
| FMV-02 | ✅ COVERED | `PathEdge.test.tsx` |
| FMV-03 | ✅ COVERED | `nodes.test.tsx` (FirewallNode capacity gauge) |
| FMV-04 | ✅ COVERED | `elkLayout.test.ts` |
| FMV-05 | ✅ COVERED | `FlowMapFilterPanel.test.tsx`, `PathDetailPanel.test.tsx`, `FlowMapEmptyState.test.tsx` |

---

## Wave 0 Requirements

✅ Satisfied during Wave 1 (schema foundation) and Wave 2 (viewer + rules) execution:

- [x] `cli/infracanvas/flowmap/__init__.py` — module scaffold
- [x] `cli/tests/` — test package with flowmap fixtures under `cli/tests/fixtures/flowmap/{aws,azure}/`
- [x] Pydantic model stubs (NetworkPath, PathHop, DCCollectorReading, DCSite, extended NetworkFinding)
- [x] Schema version bump test: `ResourceGraph.version == "2.1"` round-trips with empty `network_paths` + `dc_sites`
- [x] Fixture tripwire test: Python ↔ TypeScript field parity (`test_flowmap_models.py` + `types.test.ts`)
- [x] Install deps: `boto3`, `azure-identity`, `azure-mgmt-network`, `azure-mgmt-resource` (Python optional-deps group `flowmap`); `elkjs` (viewer)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| FlowMap tab visual parity with Canvas (zoom, pan, minimap, selection) | FMV-01..05 | Visual regressions not reliably caught by unit tests | Open exported HTML, toggle `[Canvas \| FlowMap]`, verify zoom/pan/minimap/selection work identically; no console errors |
| Dual-color edge rendering (blue forward + orange return) readable at all zoom levels | FMV-02 | Color perception + anti-aliasing | Open a fixture HTML with 2+ paths, zoom 25%–400%, verify edges remain distinguishable; screenshot for release notes |
| Empty-state CTA copy + Copy-to-clipboard behavior | FMV-05 / D-08 | Copy review + clipboard API | Open HTML exported without `--flowmap`; verify empty state shows, Copy button transitions to "Copied ✓" for 2s |
| Live-scan smoke test against real AWS + Azure accounts | AWS-01..03, AZN-01..03 | Credential availability + real SDK behavior | Run `infracanvas scan ./fixtures/live-smoke --flowmap` against personal AWS/Azure accounts; confirm FlowMap tab populates; record as design-partner demo asset |

*All other behaviors have automated verification above.*

---

## Scope Exclusions (deferred to Phase 3b)

| Item | Reason |
|------|--------|
| **NET-010** (stateful firewall on only one path) | Path-dependent rule — requires forward/return path comparison. Phase 3a ships cloud topology only; `network_paths` is empty. Rule ships when path inference lands in 3b. |
| **Asymmetric routing detection** | Same root cause — requires populated `network_paths`. |
| **PathEdge divergence marker visual** | Renders only when paths are populated; code path is tested cold against synthetic fixtures in `PathEdge.test.tsx`. |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covered all foundation dependencies (schema, fixtures, TS tripwire)
- [x] No watch-mode flags (`--watch`, bare `vitest`, `pytest-watch`)
- [x] Feedback latency < 60s
- [x] Bundle size check wired into CI via `test_viewer_template_bundle.py` (exported HTML < 5MB)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** ✅ 2026-04-19 — Phase 3a is Nyquist-compliant.

---

## Validation Audit 2026-04-19

| Metric | Count |
|--------|-------|
| Requirements in scope | 15 (3 FDM + 3 AWS + 3 AZN + 1 NFN + 5 FMV) |
| Tasks audited | 28 across 9 plans |
| Test files mapped | 14 (6 CLI + 8 viewer) |
| Gaps found | 0 |
| Gaps resolved | 0 |
| Gaps escalated (scope-excluded) | 1 (NET-010 → Phase 3b) |
| Visual/live-scan items moved to manual-only | 4 (already documented) |

Auditor: main agent (no `gsd-nyquist-auditor` subagent needed — no gaps to fill).
