---
phase: 3
slug: flowmap-v1-0
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-18
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Planner fills the Per-Task Verification Map once PLAN.md files are generated.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework (CLI)** | pytest (Python 3.12+, via pyproject.toml) |
| **Framework (viewer)** | Vitest 4.1.4 + @testing-library/react 16.3.2 |
| **Config file (CLI)** | `cli/pyproject.toml` |
| **Config file (viewer)** | `viewer/vite.config.ts` |
| **Quick run command (CLI)** | `cd cli && pytest -x tests/flowmap/` |
| **Quick run command (viewer)** | `cd viewer && npx vitest run src/components/flowmap/` |
| **Full suite command** | `cd cli && pytest && cd ../viewer && npx vitest run` |
| **Estimated runtime** | ~60 seconds (CLI ~30s, viewer ~30s) |

---

## Sampling Rate

- **After every task commit:** Run the relevant quick command (CLI or viewer)
- **After every plan wave:** Run the full suite
- **Before `/gsd-verify-work`:** Full suite must be green + bundle size check (<5MB HTML)
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

*Populated by planner during PLAN.md generation. Every task requires either an `<automated>` verify command or a Wave 0 dependency. No 3 consecutive tasks may lack automated verification.*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD — planner fills | | | | | | | | | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Per the research recommendation (Wave 0 — install deps, Pydantic models, schema bump, test scaffolding):

- [ ] `cli/infracanvas/flowmap/__init__.py` — module scaffold
- [ ] `cli/tests/flowmap/__init__.py` — test package scaffold
- [ ] `cli/tests/flowmap/conftest.py` — shared fixtures (sanitized moto + placebo JSON loaders)
- [ ] `cli/tests/flowmap/fixtures/aws/` — TGW, VPC, NACL, Direct Connect sanitized JSON
- [ ] `cli/tests/flowmap/fixtures/azure/` — vWAN, vNet peering, NSG, ExpressRoute sanitized JSON
- [ ] `viewer/src/components/flowmap/__init.test.tsx` or equivalent scaffold test ensuring the tab mounts
- [ ] Install deps: `boto3`, `azure-identity`, `azure-mgmt-network`, `azure-mgmt-resource`, `moto`, `placebo` (Python); `elkjs` (viewer)
- [ ] Pydantic model stubs: `NetworkPath`, `PathHop`, `DCCollectorReading`, `NetworkFinding` (empty-field placeholders for 3a per D-10)
- [ ] Schema version bump test: `ResourceGraph.version == "2.1"` round-trips with empty network_paths + dc_sites
- [ ] Fixture tripwire test: Pydantic field names ↔ TypeScript interface keys match (prevents the drift flagged as open question #4 in RESEARCH.md)

*Goal: when Wave 0 lands, every subsequent task has a test file it can assert into — no task is blocked on "there's nowhere to put the test."*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| FlowMap tab visual parity with Canvas (zoom, pan, minimap, selection) | FMV-01..05 | Visual regressions not reliably caught by unit tests | Open exported HTML, toggle `[Canvas \| FlowMap]`, verify zoom/pan/minimap/selection work identically; no console errors |
| Dual-color edge rendering (blue forward + orange return) readable at all zoom levels | FMV-03 | Color perception + anti-aliasing | Open a fixture HTML with 2+ paths, zoom 25%–400%, verify edges remain distinguishable; screenshot for release notes |
| Empty-state CTA ("Re-run with `--flowmap`") copy + link correctness | D-08 | Copy review | Open HTML exported without `--flowmap`; verify empty state shows and message matches CONTEXT.md D-08 |
| Live-scan smoke test against real AWS + Azure accounts | AWS-01..03, AZN-01..03 | Credential availability + real SDK behavior | Run `infracanvas scan ./fixtures/live-smoke --flowmap` against personal AWS/Azure accounts; confirm FlowMap tab populates; record as design-partner demo asset |

*All other behaviors must have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (AWS + Azure fixtures, model stubs, schema bump test, TS tripwire)
- [ ] No watch-mode flags (`--watch`, `vitest` without `run`, `pytest-watch`)
- [ ] Feedback latency < 60s
- [ ] Bundle size check wired into CI: exported HTML < 5MB (CLAUDE.md constraint)
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
