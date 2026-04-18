---
phase: 2
slug: canvas-v1-0
status: verified
threats_open: 0
asvs_level: 1
created: 2026-04-18
---

# Phase 2 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| User `.tf` files -> parser | Terraform HCL parsed by python-hcl2 | Untrusted input (user-owned) |
| User policy YAML -> engine | `--policy <dir>` loads YAML via safe_load | Untrusted input (user-owned) |
| Package YAML rules -> engine | Built-in rule definitions shipped in wheel | Trusted (PyPI integrity) |
| CLI flags -> scan pipeline | `--fail-on`, `--ignore`, `--shadow`, `--policy` | Untrusted input |
| CLI -> AWS API | boto3 read-only `describe_*` / `list_*` | User credentials (never logged) |
| AWS API responses -> graph | Shadow resource attributes | Trusted (AWS-signed) |
| Static EOL tables -> staleness | Hardcoded dates in Python | Trusted (may drift over time) |
| Graph JSON -> viewer | `window.__INFRACANVAS_DATA__` injection | Trusted (CLI-generated) |
| GitHub Actions -> PyPI | Release workflow publishes wheel | OIDC Trusted Publisher |
| GitHub Actions -> GHCR | Release workflow pushes Docker image | OIDC |
| Dockerfile -> runtime | Container executes user-provided scans | Non-root, read-only |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-02-01 | Tampering | `security/loader.py::load_policy_rules` | mitigate | `yaml.safe_load()` (loader.py:33) + `policy_dir.is_dir()` guard (loader.py:72) | closed |
| T-02-02 | Info Disclosure | `main.py` parse error output | mitigate | Prints only `path.name` (main.py:92) — no file contents or absolute paths | closed |
| T-02-03 | DoS | `parser/hcl.py` | accept | See Accepted Risks R-02-01 | closed |
| T-02-04 | Tampering | `parser/azure.py::normalize_azure_attrs` | accept | See Accepted Risks R-02-02 | closed |
| T-02-05 | Info Disclosure | Azure attributes in graph | accept | See Accepted Risks R-02-03 | closed |
| T-02-06 | Repudiation | `security/staleness.py` EOL tables | accept | See Accepted Risks R-02-04 | closed |
| T-02-07 | Tampering | AWS rule YAML files | accept | See Accepted Risks R-02-05 | closed |
| T-02-08 | Info Disclosure | `shadow/detector.py` boto3 credentials | mitigate | Lazy boto3 import (detector.py:46-57); generic `RuntimeError`; `except Exception: pass` suppresses API errors (detector.py:134,154,181,208,228,251) — credentials never logged | closed |
| T-02-09 | Tampering | `shadow/detector.py` region inference | mitigate | Region resolved from user `.tf` (main.py:120-127); single region per `--shadow` invocation; default `us-east-1` | closed |
| T-02-10 | Elevation of Privilege | AWS IAM scope | accept | See Accepted Risks R-02-06 | closed |
| T-02-11 | Tampering | `cost/estimator.py` region from attributes | accept | See Accepted Risks R-02-07 | closed |
| T-02-12 | Tampering | `--policy` path traversal | mitigate | `policy_dir.is_dir()` check (loader.py:72) + `yaml.safe_load()` (loader.py:33) | closed |
| T-02-13 | DoS | `--policy` with many YAML files | accept | See Accepted Risks R-02-08 | closed |
| T-02-14 | Tampering | `--fail-on` invalid severity | mitigate | `sev_order.index(threshold)` raises `ValueError` (main.py:344); Typer handles gracefully | closed |
| T-02-15 | Info Disclosure | `FindingCard` framework_ids display | accept | See Accepted Risks R-02-09 | closed |
| T-02-16 | Tampering | `release.yml` PyPI publish | mitigate | `pypa/gh-action-pypi-publish@release/v1` (release.yml:129) with `id-token: write` OIDC Trusted Publisher (release.yml:104) — no long-lived API token | closed |
| T-02-17 | Elevation of Privilege | Dockerfile | mitigate | Non-root `infracanvas` user (Dockerfile:19-20); no SUID binaries; read-only scan operations | closed |
| T-02-18 | Info Disclosure | Docker image layers | accept | See Accepted Risks R-02-10 | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| R-02-01 | T-02-03 | Malformed HCL could slow python-hcl2 Lark parser. Acceptable: CLI is a local tool, not a network service. Per-file try/except in `parser/hcl.py:88-95` limits blast radius to the offending file. | Bhushan | 2026-04-18 |
| R-02-02 | T-02-04 | `normalize_azure_attrs` (parser/azure.py:11-21) only reads and copies dict values — no file I/O, no exec, no dynamic imports. Tampering surface is equivalent to upstream python-hcl2 parsing. | Bhushan | 2026-04-18 |
| R-02-03 | T-02-05 | Azure resource attributes come from the user's own `.tf` files and travel the same trust boundary as existing AWS parsing. No secrets are fetched from Azure APIs in Phase 2. | Bhushan | 2026-04-18 |
| R-02-04 | T-02-06 | Lambda runtime / EKS / AKS EOL dates are hardcoded (`security/staleness.py:10-36`) and will drift as vendors update schedules. Users can suppress stale findings with `--ignore RST-001`. Acceptable for Phase 2 (local CLI); revisit when EOL feed becomes available. | Bhushan | 2026-04-18 |
| R-02-05 | T-02-07 | Built-in AWS/Azure rule YAML files ship inside the wheel. Distribution integrity is delegated to PyPI + pip signature model; no separate signing is justified for Phase 2. | Bhushan | 2026-04-18 |
| R-02-06 | T-02-10 | `ShadowDetector` exclusively calls read-only `describe_*` / `list_*` AWS APIs. No write/delete operations. IAM scoping is delegated to the user (least-privilege read-only policy documented in README). | Bhushan | 2026-04-18 |
| R-02-07 | T-02-11 | Region value in `cost/estimator.py:120` originates from the user's own `.tf`. An incorrect region yields an incorrect cost estimate only — no security consequence, no privilege boundary crossed. | Bhushan | 2026-04-18 |
| R-02-08 | T-02-13 | A user pointing `--policy` at a very large directory triggers slow YAML loading but no security impact. Local CLI invocation; user controls their own machine. | Bhushan | 2026-04-18 |
| R-02-09 | T-02-15 | Framework IDs rendered by `viewer/src/components/FindingCard.tsx:55-61` are non-sensitive public control identifiers (CIS, NIST, PCI, etc.). In gate mode (default, main.py:357,468) finding details including framework tags are blurred behind the free-tier placeholder. | Bhushan | 2026-04-18 |
| R-02-10 | T-02-18 | The Docker image contains open-source MIT-licensed code plus PyPI-resolved dependencies. No secrets, tokens, or customer data are copied into any layer. | Bhushan | 2026-04-18 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-04-18 | 18 | 18 | 0 | gsd-security-auditor (Opus) |

### Audit 2026-04-18 — Initial verification (State B)

- Auditor: `gsd-security-auditor` (model: Opus)
- Input state: B (SECURITY.md absent; PLAN + SUMMARY artifacts present for sub-phases 02-00 through 02-09)
- All 18 registered threats verified against implementation with file:line evidence.
- All 8 SUMMARY.md files report "No new threat flags" — no unregistered drift.
- Sub-phase 02-00 (test stubs) and 02-09 (offline font inlining — reduces threat surface by removing CDN fetch) introduced no new trust boundaries.

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-04-18
