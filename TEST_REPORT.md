# Test Report — InfraCanvas Phase 1+2

**Date:** 2026-04-14
**Test Runner:** pytest 9.0.3 (Python), vitest 4.1.4 (TypeScript)
**Python:** 3.12.11
**Node:** v22.x

---

## Summary

| Suite | Tests | Passed | Failed | Status |
|---|---|---|---|---|
| A — Parser | 16 | 16 | 0 | PASS |
| B — Graph | 14 | 14 | 0 | PASS |
| C — Security | 15 | 15 | 0 | PASS |
| CLI — Commands | 15 | 15 | 0 | PASS |
| D — Integration (BLOCKER) | 9 | 9 | 0 | PASS |
| E — Viewer (TypeScript) | 25 | 25 | 0 | PASS |
| **TOTAL** | **94** | **94** | **0** | **ALL PASS** |

---

## Suite A — Parser Unit Tests (16 tests)

| ID | Test | Status |
|---|---|---|
| A-001 | Parse single resource block — type, name, attributes | PASS |
| A-002 | Parse multiple resource types in one directory | PASS |
| A-003 | Detect implicit dependency from resource reference | PASS |
| A-004 | Detect explicit depends_on declaration | PASS |
| A-005 | Handle empty .tf file without crashing | PASS |
| A-006 | Handle directory with no .tf files | PASS |
| A-007 | Handle malformed HCL — skips gracefully | PASS |
| A-008 | Parse .tfstate file — resource count and attributes | PASS |
| A-009 | State reader maps to correct type.name addresses | PASS |
| A-010 | Parse variable blocks without crashing | PASS |
| — | Simple VPC attributes preserved | PASS |
| — | Multi-module parses multiple files | PASS |
| — | Multi-module outputs parsed | PASS |
| — | Insecure setup resources parsed | PASS |
| — | Large fixture (50 resources) parsed | PASS |
| — | State provider extraction | PASS |

## Suite B — Graph Builder Tests (14 tests)

| ID | Test | Status |
|---|---|---|
| B-001 | Correct node count (6 for simple_vpc) | PASS |
| B-002 | Edge exists between subnet and VPC | PASS |
| B-003 | Node attributes: provider, type, name | PASS |
| B-004 | Graph exports to valid JSON | PASS |
| B-005 | JSON round-trip (model → JSON → model) | PASS |
| B-006 | Same VPC reference → same group value | PASS |
| B-007 | Summary counts resources correctly | PASS |
| B-008 | Empty directory → 0 nodes, no error | PASS |
| — | Provider detection | PASS |
| — | Node attributes preserved | PASS |
| — | Multi-module explicit deps | PASS |
| — | Multi-module implicit deps | PASS |
| — | Dependencies list populated | PASS |
| — | Edge types (depends_on vs implicit) | PASS |

## Suite C — Security Rules Tests (15 tests)

| ID | Test | Status |
|---|---|---|
| C-001+ | S3 acl="public-read" → SEC-001 critical | PASS |
| C-001- | S3 no ACL → no SEC-001 | PASS |
| C-002+ | S3 no encryption → SEC-002 high | PASS |
| C-003+ | SG 0.0.0.0/0 port 22 → SEC-003 critical | PASS |
| C-004+ | RDS publicly_accessible=true → SEC-005 critical | PASS |
| C-005+ | IAM Action=* → SEC-007 critical | PASS |
| C-006 | Score: 1 critical = 80 | PASS |
| C-007 | Score clamped to 0 for 5+ criticals | PASS |
| C-008 | Finding summary counts match | PASS |
| C-009 | Unmatched resource type → no error | PASS |
| C-010 | YAML loader discovers all 10 rules | PASS |
| — | Missing tags detected (SEC-010) | PASS |
| — | KMS no rotation detected (SEC-009) | PASS |
| — | Finding has evidence dict | PASS |
| — | Clean infra → no critical findings | PASS |

## Suite D — Integration Tests (BLOCKER) — 9 tests

| ID | Test | Status |
|---|---|---|
| D-001 | E2E scan → valid JSON, ≥4 nodes, ≥1 finding | PASS |
| D-002 | --severity critical filters correctly | PASS |
| D-003 | JSON output file created at specified path | PASS |
| D-004 | CLI exits 0 on clean scan | PASS |
| D-005 | --ci exits non-zero on criticals | PASS |
| D-005b | --ci exits 0 when clean | PASS |
| — | Invalid directory exits non-zero | PASS |
| — | Score command JSON output | PASS |
| — | Schema fields complete (all required fields present) | PASS |

**Suite D: ALL PASS — no blockers.**

## Suite E — Viewer Tests (TypeScript) — 25 tests

| ID | Test | Status |
|---|---|---|
| E-002/003 | Severity colors (critical=red, clean=green) | PASS |
| E-004 | Drift colors (changed=amber, deleted=red) | PASS |
| E-007 | toggleSeverityFilter fires callback | PASS |
| E-009 | Store filter state updates | PASS |
| E-010 | TypeScript types match sample-data shape | PASS |
| — | Resource color mapping (known types) | PASS |
| — | Resource color default (unknown types) | PASS |
| — | getHighestSeverity (all priority levels) | PASS |
| — | Store: setGraph, setSelectedNode, toggleFilterPanel | PASS |
| — | Store: clearFilters resets all | PASS |
| — | Store: multiple severity filters accumulate | PASS |
| — | Types: nodes have all required fields | PASS |
| — | Types: findings have all required fields | PASS |
| — | Types: summary has all required fields | PASS |
| — | Types: edges have correct type values | PASS |
| — | Types: valid severity values | PASS |
| — | Types: valid drift values | PASS |
| — | TypeScript strict compile: 0 errors | PASS |

## Coverage

### Python (target: ≥80%)

```
Name                               Stmts   Miss  Cover
----------------------------------------------------------------
infracanvas/__init__.py                1      0   100%
infracanvas/export/html.py            12      1    92%
infracanvas/export/json.py             5      0   100%
infracanvas/graph/builder.py          40      0   100%
infracanvas/graph/models.py           50      0   100%
infracanvas/main.py                  167     19    89%
infracanvas/parser/hcl.py            116     18    84%
infracanvas/parser/references.py      20      0   100%
infracanvas/parser/state.py           44      2    95%
infracanvas/security/engine.py       111     34    69%
infracanvas/security/loader.py        27      2    93%
infracanvas/security/models.py        19      0   100%
----------------------------------------------------------------
TOTAL                                615     79    87%
```

**Result: 87% — PASS (target: ≥80%)**

### TypeScript

TypeScript strict mode compilation: **0 errors**
Vitest: 25/25 tests passing

## Performance

| Metric | Target | Actual | Status |
|---|---|---|---|
| PC-001: 50-node scan time | <5s | 0.44s | PASS |
| PC-002: HTML output size | <3MB | ~478KB | PASS |

## Verdict

**ALL SUITES PASS. Suite D (blocker) is GREEN. Ready for Phase 3.**
