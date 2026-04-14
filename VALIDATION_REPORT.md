# Validation Report — InfraCanvas Phase 1+2

**Date:** 2026-04-14
**Validator:** Automated + manual code review

---

## Severity Summary

| Severity | Count |
|---|---|
| Critical | 0 |
| High | 0 |
| Medium | 3 |
| Low | 5 |

---

## Code Quality Findings

| ID | Check | Status | Notes |
|---|---|---|---|
| CQ-001 | No dead/commented-out code | PASS | Clean after ruff --fix |
| CQ-002 | No unresolved TODO/FIXME | PASS | Only "Phase 2" stub in plan command (intentional) |
| CQ-003 | All functions <50 lines | MEDIUM | 5 functions over limit (see below) |
| CQ-004 | Consistent error handling | PASS | Python uses specific exceptions, no bare `except:` (hcl.py:91 uses `except Exception:` for parse errors — acceptable for file parsing) |
| CQ-005 | No raw print() statements | PASS | All output via `rich.Console` or `typer.echo` |
| CQ-006 | Python type annotations | PASS | All functions annotated; ruff check clean |
| CQ-007 | TypeScript strict mode | PASS | `strict: true` in tsconfig.json, 0 errors on `tsc --noEmit` |
| CQ-008 | pyproject.toml deps pinned | LOW | Dependencies use minimum version ranges (e.g., `>=2.0`) instead of exact pins. Acceptable for a CLI tool distributed via pip. |
| CQ-009 | package.json deps pinned | LOW | Dependencies use `^` ranges. Standard npm convention for a bundled SPA. |

### CQ-003 Details — Functions over 50 lines

| File | Function | Lines | Recommendation |
|---|---|---|---|
| `graph/builder.py:11` | `build_graph()` | 55 | Acceptable — extract edge-building to helper |
| `main.py:90` | `_print_summary()` | 60 | Low risk — Rich table formatting |
| `main.py:153` | `scan()` | 69 | Inflated by typer argument declarations |
| `main.py:225` | `score()` | 69 | Inflated by typer argument declarations |
| `parser/hcl.py:86` | `_parse_file()` | 84 | Refactor candidate — split by block type |

**Verdict:** No refactoring required for Phase 3. Can address in Phase 4 polish.

---

## Security Audit

| ID | Check | Status | Notes |
|---|---|---|---|
| SC-001 | No hardcoded paths/secrets/keys | PASS | Zero matches for AKIA, password, secret, api_key, token |
| SC-002 | Parser does not execute Terraform | PASS | Only `hcl2.load()` for file parsing, no subprocess calls |
| SC-003 | Path inputs validated | PASS | `directory.is_dir()` check in scan/score commands; typer handles path validation |
| SC-004 | JSON via Pydantic model_dump_json | PASS | All JSON output through Pydantic serialization |
| SC-005 | HTML export uses safe injection | PASS | `model_dump_json()` → JSON.parse in browser. No raw string interpolation. |
| SC-006 | No secrets in help/error text | PASS | Only generic error messages |
| SC-007 | pip-audit | PASS | 0 vulnerabilities in project deps (pip itself has CVEs, not project deps) |
| SC-008 | npm audit | PASS | 0 vulnerabilities |

---

## Architecture Conformance

| ID | Check | Status | Notes |
|---|---|---|---|
| AC-001 | ResourceGraph JSON matches schema | PASS | All 33 fields verified present (see automated check) |
| AC-002 | TypeScript interfaces match JSON | PASS | types.ts defines all fields: ResourceNode, Finding, GraphSummary, GraphEdge |
| AC-003 | YAML rule format matches spec | PASS | All 10 rules have required fields (id, title, severity, resource_types, condition, remediation, description). Operators used: equals, in, not_exists, contains, list_contains_cidr |
| AC-004 | CLI commands match spec | PASS | `scan` (with --format, --output, --ci, --severity), `score` (with --format json), `export`, `plan` (stub) all present |
| AC-005 | HTML injection key correct | PASS | `window.__INFRACANVAS_DATA__ = null;` placeholder, replaced with `model_dump_json()` output |

---

## Performance Results

| ID | Check | Target | Actual | Status |
|---|---|---|---|---|
| PC-001 | Parse 50 resources | <5s | 0.44s | PASS |
| PC-002 | HTML output size | <3MB | 478KB | PASS |
| PC-003 | Viewer renders 50 nodes | No visible lag | N/A (requires browser) | DEFERRED |

---

## Dependency Audit

### pip-audit (Python)
```
Project dependencies: 0 known vulnerabilities
pip itself: 4 CVEs (not project deps, upgrade recommended)
```

### npm audit (TypeScript viewer)
```
found 0 vulnerabilities
```

---

## Medium Findings

1. **CQ-003: `_parse_file()` is 84 lines** — `parser/hcl.py:86`. Handles 5 block types in one function. Recommend splitting into `_parse_resources()`, `_parse_variables()`, etc. in Phase 4.

2. **CQ-003: `build_graph()` is 55 lines** — `graph/builder.py:11`. Edge construction loop could be extracted.

3. **Engine coverage at 69%** — `security/engine.py`. Uncovered code paths: `equals`, `not_equals`, `not_in`, `any_equals`, `matches_cidr` operators. Not a blocker but should add targeted tests.

## Low Findings

1. **pyproject.toml uses version ranges** — Not pinned to exact versions. Acceptable for CLI distribution but could cause reproducibility issues.
2. **package.json uses `^` ranges** — Standard npm convention for bundled apps.
3. **`layout.py` placeholder** — 3 lines, 0% coverage. Phase 2 placeholder, intentional.
4. **Missing `--format json` on scan for CLI usage** — scan defaults to json output format but `--format` only affects file format, not stdout.
5. **`except Exception:` in hcl.py:91** — Broad catch for HCL parse errors. Acceptable for file parsing resilience.

---

## Verdict

**PASS — Ready for Phase 3.**

- Zero Critical findings
- Zero High findings
- 3 Medium findings — all documented, none blocking
- 5 Low findings — cosmetic/style
- All architecture conformance checks pass
- All dependency audits clean
- Performance within targets
