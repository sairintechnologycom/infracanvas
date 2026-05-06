---
phase: 02-canvas-v1-0
plan: "03"
subsystem: security-rules-staleness
tags: [wave-2, security-rules, compliance, staleness, python, yaml]
dependency_graph:
  requires: [02-01, 02-02]
  provides: [30-aws-security-rules, framework-ids-all-rules, staleness-engine]
  affects: [02-06, 02-07, 02-08]
tech_stack:
  added: []
  patterns: [yaml-rule-files, pydantic-finding-append, eol-date-comparison]
key_files:
  created:
    - cli/infracanvas/security/staleness.py
    - cli/infracanvas/security/rules/aws/s3_advanced.yaml
    - cli/infracanvas/security/rules/aws/networking_advanced.yaml
    - cli/infracanvas/security/rules/aws/iam_advanced.yaml
    - cli/infracanvas/security/rules/aws/lambda.yaml
    - cli/infracanvas/security/rules/aws/rds_advanced.yaml
    - cli/infracanvas/security/rules/aws/eks.yaml
    - cli/infracanvas/security/rules/aws/alb.yaml
    - cli/infracanvas/security/rules/aws/cloudfront.yaml
    - cli/infracanvas/security/rules/aws/messaging.yaml
    - cli/infracanvas/security/rules/aws/dynamodb.yaml
    - cli/infracanvas/security/rules/aws/kms_advanced.yaml
  modified:
    - cli/infracanvas/security/rules/aws/s3.yaml
    - cli/infracanvas/security/rules/aws/networking.yaml
    - cli/infracanvas/security/rules/aws/iam.yaml
    - cli/infracanvas/security/rules/aws/database.yaml
    - cli/infracanvas/security/rules/aws/compute.yaml
    - cli/tests/test_staleness.py
    - cli/tests/test_security.py
decisions:
  - "SEC-030 placed in s3_advanced.yaml (not s3.yaml) to keep existing files minimal and new rules in dedicated files"
  - "test_security.py rule count updated from 20 to 40 — auto-fix (Rule 1) for hardcoded assertion no longer matching post-expansion rule count"
  - "staleness.py uses date.today().isoformat() string comparison (lexicographic) for EOL — avoids datetime parsing overhead and is correct for ISO-8601 dates"
metrics:
  duration: "~15 minutes"
  completed: "2026-04-16T11:15:00Z"
  tasks_completed: 3
  files_modified: 18
---

# Phase 02 Plan 03: AWS Security Rules Expansion and Staleness Checks Summary

Expanded AWS security rules from 10 to 30 (SEC-001 through SEC-030), retrofitted CIS/NIST/SOC2/PCI-DSS compliance framework tags onto all 40 rules (30 AWS + 10 Azure), and implemented the runtime staleness engine that detects EOL Lambda runtimes, outdated EKS/AKS versions, and missing Azure management locks.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1A | Retrofit framework_ids on 10 existing AWS rules | d9dd90b | s3.yaml, networking.yaml, iam.yaml, database.yaml, compute.yaml |
| 1B | Create 20 new AWS rules (SEC-011 through SEC-030) in 11 YAML files | 722b81e | 11 new yaml files, test_security.py |
| 2 | Runtime staleness checks (RST-01, RST-02) | 9743b6e | staleness.py, test_staleness.py |

## Verification Results

- `load_rules()` returns 40 rules (30 AWS + 10 Azure)
- All 40 rules have `framework_ids` arrays with 2+ entries each
- `35 passed` — all security + staleness tests green
- `7 staleness tests` cover RST-001 (Lambda EOL), RST-002 (EKS version), RST-003 (AKS version), RST-004 (missing management lock)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated hardcoded rule count assertion in test_security.py**
- **Found during:** Task 1B
- **Issue:** `test_loads_all_rules` asserted `len(rules) == 20` which failed after expanding to 30 AWS rules
- **Fix:** Updated assertion to `len(rules) == 40` with updated comment reflecting 30 AWS + 10 Azure
- **Files modified:** cli/tests/test_security.py
- **Commit:** 722b81e

## Known Stubs

None — all framework_ids are populated with real compliance tag values, staleness engine performs real EOL date comparisons against `date.today()`.

## Threat Flags

None. The staleness EOL tables (T-02-06) are accepted in the threat register — static dates will drift over time, which is documented as acceptable for Phase 2 CLI. YAML rule files (T-02-07) remain package-internal, loaded via `yaml.safe_load()`.

## Self-Check: PASSED

- [x] cli/infracanvas/security/staleness.py contains `def check_staleness(graph: ResourceGraph)`
- [x] cli/infracanvas/security/staleness.py contains `LAMBDA_EOL` dict with 8 entries
- [x] cli/infracanvas/security/staleness.py contains `_check_resource_locks` function
- [x] cli/infracanvas/security/rules/aws/lambda.yaml contains `SEC-017`
- [x] All 40 rules have framework_ids (verified via load_rules() assertion)
- [x] 30 AWS rules load (SEC-001 through SEC-030)
- [x] 7 staleness tests pass
- [x] Commit d9dd90b exists (Task 1A)
- [x] Commit 722b81e exists (Task 1B)
- [x] Commit 9743b6e exists (Task 2)
