---
phase: 1
slug: canvas-mvp
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-16
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (Python CLI) + vitest (TypeScript viewer) |
| **Config file** | `pyproject.toml` (pytest), `viewer/vite.config.ts` (vitest) |
| **Quick run command** | `cd cli && python -m pytest tests/ -x -q` |
| **Full suite command** | `cd cli && python -m pytest tests/ && cd ../viewer && npm test` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd cli && python -m pytest tests/ -x -q`
- **After every plan wave:** Run `cd cli && python -m pytest tests/ && cd ../viewer && npm test`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 1-01-00 | 01 | 1 | CLI-02 | — | N/A | unit | `python -m pytest tests/test_graph.py::TestNetworkFinding -x -q` | ✅ W0 | ⬜ pending |
| 1-01-01 | 01 | 1 | CLI-01 | — | N/A | unit | `python -m pytest tests/test_cli.py -x -q` | ❌ W0 | ⬜ pending |
| 1-01-02 | 01 | 1 | CLI-02 | — | N/A | unit | `python -m pytest tests/test_cli.py -x -q` | ❌ W0 | ⬜ pending |
| 1-01-03 | 01 | 1 | PRS-01 | — | N/A | unit | `python -m pytest tests/test_parser.py -x -q` | ✅ | ⬜ pending |
| 1-01-04 | 01 | 1 | PRS-02 | — | N/A | unit | `python -m pytest tests/test_parser.py -x -q` | ✅ | ⬜ pending |
| 1-01-05 | 01 | 1 | PRS-03 | — | N/A | unit | `python -m pytest tests/test_parser.py -x -q` | ✅ | ⬜ pending |
| 1-01-06 | 01 | 1 | PRS-04 | — | N/A | unit | `python -m pytest tests/test_parser.py -x -q` | ✅ | ⬜ pending |
| 1-01-07 | 01 | 1 | PRS-05 | — | N/A | unit | `python -m pytest tests/test_parser.py -x -q` | ❌ W0 | ⬜ pending |
| 1-02-01 | 02 | 1 | GRF-01 | — | N/A | unit | `python -m pytest tests/test_builder.py -x -q` | ✅ | ⬜ pending |
| 1-02-02 | 02 | 1 | GRF-02 | — | N/A | unit | `python -m pytest tests/test_builder.py -x -q` | ✅ | ⬜ pending |
| 1-02-03 | 02 | 1 | GRF-03 | — | N/A | unit | `python -m pytest tests/test_builder.py -x -q` | ✅ | ⬜ pending |
| 1-03-01 | 03 | 2 | SEC-01 | T-1-01 | Security rules produce findings for known-bad configs | unit | `python -m pytest tests/test_security.py -x -q` | ✅ | ⬜ pending |
| 1-03-02 | 03 | 2 | SEC-02 | T-1-01 | Rules don't produce false positives on secure configs | unit | `python -m pytest tests/test_security.py -x -q` | ✅ | ⬜ pending |
| 1-03-03 | 03 | 2 | SEC-03 | T-1-01 | All 10+ rules have test coverage | unit | `python -m pytest tests/test_security.py -x -q` | ✅ | ⬜ pending |
| 1-03-04 | 03 | 2 | SEC-04 | T-1-01 | N/A | unit | `python -m pytest tests/test_security.py -x -q` | ✅ | ⬜ pending |
| 1-04-01 | 04 | 2 | SCR-01 | — | N/A | unit | `python -m pytest tests/test_scorer.py -x -q` | ❌ W0 | ⬜ pending |
| 1-04-02 | 04 | 2 | SCR-02 | — | N/A | unit | `python -m pytest tests/test_scorer.py -x -q` | ❌ W0 | ⬜ pending |
| 1-04-03 | 04 | 2 | SCR-03 | — | N/A | unit | `python -m pytest tests/test_scorer.py -x -q` | ❌ W0 | ⬜ pending |
| 1-05-01 | 05 | 3 | VWR-01 | — | N/A | unit | `cd viewer && npm test` | ✅ | ⬜ pending |
| 1-05-02 | 05 | 3 | VWR-02 | — | N/A | unit | `cd viewer && npm test` | ✅ | ⬜ pending |
| 1-05-03 | 05 | 3 | VWR-03 | — | N/A | unit | `cd viewer && npm test` | ✅ | ⬜ pending |
| 1-05-04 | 05 | 3 | VWR-04 | — | N/A | unit | `cd viewer && npm test` | ✅ | ⬜ pending |
| 1-05-05 | 05 | 3 | VWR-05 | — | N/A | unit | `cd viewer && npm test` | ✅ | ⬜ pending |
| 1-05-06 | 05 | 3 | VWR-06 | T-1-02 | Blurred findings don't leak content to DOM | unit | `cd viewer && npm test` | ❌ W0 | ⬜ pending |
| 1-06-01 | 06 | 3 | EXP-01 | — | N/A | unit | `python -m pytest tests/test_export.py -x -q` | ✅ | ⬜ pending |
| 1-06-02 | 06 | 3 | EXP-02 | — | N/A | unit | `python -m pytest tests/test_export.py -x -q` | ✅ | ⬜ pending |
| 1-07-01 | 07 | 4 | REL-01 | — | N/A | integration | `pip install -e . && infracanvas --version` | ✅ | ⬜ pending |
| 1-07-02 | 07 | 4 | REL-02 | — | N/A | integration | `pip install infracanvas` (CI) | ❌ W0 | ⬜ pending |
| 1-07-03 | 07 | 4 | REL-03 | — | N/A | manual | GitHub Actions publish workflow | ❌ W0 | ⬜ pending |
| 1-07-04 | 07 | 4 | REL-04 | — | N/A | manual | Show HN draft review + submission | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `cli/tests/test_graph.py::TestNetworkFinding` — stubs for CLI-02 (NetworkFinding model, ResourceGraph v2.0) — **covered by Plan 01-01 Task 0**
- [ ] `cli/tests/test_cli.py` — stubs for CLI-01, CLI-02 (browser open, CI detection, serve command)
- [ ] `cli/tests/test_scorer.py` — stubs for SCR-01, SCR-02, SCR-03 (score card dimensions, HTML output)
- [ ] `viewer/src/__tests__/FreeGate.test.tsx` — stubs for VWR-06 (blur/gate rendering)
- [ ] `.github/workflows/publish.yml` — PyPI Trusted Publisher workflow skeleton
- [ ] `Formula/infracanvas.rb` — Homebrew formula stub

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Browser opens automatically on `scan` | EXP-02 | OS-level browser open cannot be unit tested | Run `infracanvas scan ./test_tf` on local machine, verify browser opens |
| CI auto-detection skips browser open | CLI-02 | Requires setting env vars in a real terminal | Run `CI=true infracanvas scan ./test_tf`, verify no browser open and path is printed |
| `infracanvas score` opens browser with score HTML | SCR-03 | Browser open is OS-level | Run `infracanvas score ./test_tf`, verify score HTML opens in browser |
| Homebrew install works | REL-04 | Requires real Homebrew environment | `brew tap infracanvas/tap && brew install infracanvas` |
| Single-file HTML opens offline in all browsers | EXP-01 | Cross-browser testing | Open report HTML in Safari/Firefox/Chrome with network disabled |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
