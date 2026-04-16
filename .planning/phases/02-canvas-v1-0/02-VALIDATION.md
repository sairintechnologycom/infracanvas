---
phase: 2
slug: canvas-v1-0
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-16
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `cli/pyproject.toml` |
| **Quick run command** | `cd cli && python -m pytest tests/ -x -q` |
| **Full suite command** | `cd cli && python -m pytest tests/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd cli && python -m pytest tests/ -x -q`
- **After every plan wave:** Run `cd cli && python -m pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 0 | PLN-01 | — | N/A | unit | `cd cli && python -m pytest tests/test_parser.py -x -q` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | PLN-01 | — | N/A | unit | `cd cli && python -m pytest tests/test_parser.py::test_parse_errors -x -q` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 1 | AZR-01 | — | N/A | unit | `cd cli && python -m pytest tests/test_azure_parser.py -x -q` | ❌ W0 | ⬜ pending |
| 02-02-02 | 02 | 1 | AZR-02 | — | N/A | unit | `cd cli && python -m pytest tests/test_azure_security.py -x -q` | ❌ W0 | ⬜ pending |
| 02-03-01 | 03 | 1 | SHD-01 | — | boto3 never imported at module level | unit | `cd cli && python -m pytest tests/test_shadow.py -x -q` | ❌ W0 | ⬜ pending |
| 02-04-01 | 04 | 2 | DST-01 | — | N/A | unit | `cd cli && python -m pytest tests/test_drift.py -x -q` | ❌ W0 | ⬜ pending |
| 02-05-01 | 05 | 2 | POL-01 | — | Policy exit code ≠ 0 on violation | unit | `cd cli && python -m pytest tests/test_policy.py -x -q` | ❌ W0 | ⬜ pending |
| 02-06-01 | 06 | 2 | CST-01 | — | N/A | unit | `cd cli && python -m pytest tests/test_cost.py -x -q` | ❌ W0 | ⬜ pending |
| 02-07-01 | 07 | 3 | SEC-05 | — | N/A | unit | `cd cli && python -m pytest tests/test_security_rules.py -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `cli/tests/test_parser.py` — stubs for PLN-01, PLN-02, PLN-03
- [ ] `cli/tests/test_azure_parser.py` — stubs for AZR-01, AZR-02, AZR-03
- [ ] `cli/tests/test_azure_security.py` — stubs for AZR-02, SEC-05, SEC-06
- [ ] `cli/tests/test_shadow.py` — stubs for SHD-01, SHD-02
- [ ] `cli/tests/test_drift.py` — stubs for DST-01, DST-02
- [ ] `cli/tests/test_policy.py` — stubs for POL-01, POL-02
- [ ] `cli/tests/test_cost.py` — stubs for CST-01, CST-02, CST-03
- [ ] `cli/tests/test_security_rules.py` — stubs for SEC-05, SEC-06

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `infracanvas scan` on real Azure Terraform produces diagram | AZR-01 | Requires real Azure Terraform files | Run `infracanvas scan ./fixtures/azure/` and verify 10+ resource types in output |
| Shadow infra detection against live AWS API | SHD-01 | Requires live AWS credentials | Run `infracanvas scan --shadow` with real credentials, verify dashed-border nodes |
| CI exit code non-zero on policy violation | POL-01 | Integration test | Run `infracanvas scan --policy ./policies` with a violating config, check `echo $?` |
| CIS/NIST/SOC2/PCI-DSS tags visible in findings | SEC-05 | Visual verification | Run `infracanvas scan` and check `compliance_frameworks` in JSON output |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
