# SECURITY.md — Phase 02 (canvas-v1-0)

**Audit Date:** 2026-04-18
**ASVS Level:** 1 (local CLI tool, no network services)
**Block Policy:** `block_on = open`
**Threats Closed:** 18/18
**Threats Open:** 0

Local CLI tool that parses user-provided Terraform files, applies security rules, and
produces HTML/JSON reports. No persistent service, no credentials stored, no external
network surface beyond user-invoked read-only AWS describe calls under `--shadow`.

---

## Threat Register Verification

### Mitigated Threats (Evidence in Code)

| ID | Category | Component | Evidence |
|----|----------|-----------|----------|
| T-02-01 | Tampering | `security/loader.py` `load_policy_rules` | `yaml.safe_load()` at `cli/infracanvas/security/loader.py:33`; `policy_dir.is_dir()` guard at `cli/infracanvas/security/loader.py:72` before `rglob("*.yaml")` |
| T-02-02 | Info Disclosure | `main.py` parse error output | Uses `path.name` only in warning: `cli/infracanvas/main.py:92` — `f"Could not parse {path.name}: {err}"`. No file contents, no full/outside paths printed |
| T-02-08 | Info Disclosure | `shadow/detector.py` boto3 creds | Lazy `import boto3` at `cli/infracanvas/shadow/detector.py:46`; generic `RuntimeError` messages lines 48-50, 55-57 never embed credential values; `except Exception: pass` at lines 134, 154, 181, 208, 228, 251 suppresses API errors without logging |
| T-02-09 | Tampering | `shadow/detector.py` region inference | Region set from `.tf` provider block: `cli/infracanvas/main.py:120-127` (loops nodes, takes first `node.region`), defaults to `us-east-1`. Passed once to `ShadowDetector(region=...)` at `cli/infracanvas/main.py:126`; single region used for all boto3 clients at `cli/infracanvas/shadow/detector.py:66, 75` |
| T-02-12 | Tampering | `--policy` path traversal | Same loader, same guard: `policy_dir.is_dir()` at `cli/infracanvas/security/loader.py:72`; `yaml.safe_load()` at line 33 — blocks arbitrary-object YAML construction |
| T-02-14 | Tampering | `--fail-on` invalid severity | `sev_order.index(threshold)` at `cli/infracanvas/main.py:344` raises `ValueError` on unknown string; Typer surfaces error and exits non-zero |
| T-02-16 | Tampering | `release.yml` PyPI publish | Official `pypa/gh-action-pypi-publish@release/v1` at `.github/workflows/release.yml:129`; `id-token: write` permission set at `.github/workflows/release.yml:104` — OIDC Trusted Publisher, no PyPI API-token secret stored |
| T-02-17 | EoP | Dockerfile | Non-root user: `useradd -m -s /bin/bash infracanvas` at `Dockerfile:19`, switched via `USER infracanvas` at `Dockerfile:20`. No `chmod u+s` / SUID bits set in any layer |

### Accepted Risks (Sustaining Conditions Verified)

| ID | Category | Component | Sustaining Condition | Verified |
|----|----------|-----------|---------------------|----------|
| T-02-03 | DoS | `parser/hcl.py` | Local CLI; per-file `try/except` bounds blast radius to a single bad file. `parse_errors` list collects errors at `cli/infracanvas/parser/hcl.py:88-95`, allowing other files to still be parsed | Yes |
| T-02-04 | Tampering | `parser/azure.py` `normalize_azure_attrs` | Function reads and copies dict only — no file I/O, no exec, no subprocess. `cli/infracanvas/parser/azure.py:11-21` contains only `dict(attrs)` + key lookup | Yes |
| T-02-05 | Info Disclosure | Azure attrs in graph | Attributes sourced from user's own `.tf` files; identical trust boundary to AWS path. No external fetch. Graph serialized to user's own disk via `export_graph`/`export_html` | Yes |
| T-02-06 | Repudiation | `staleness.py` EOL dates | Static tables (`LAMBDA_EOL`, `EKS_EOL`, `AKS_EOL`) at `cli/infracanvas/security/staleness.py:10-36`. Users can suppress via `--ignore RST-001` (wired in `main.py:153-156`) | Yes |
| T-02-07 | Tampering | AWS rule YAML | Rule files are package-internal (`cli/infracanvas/security/rules/`), distribution integrity provided by PyPI/pip supply chain | Yes |
| T-02-10 | EoP | AWS IAM scope | Only read-only APIs invoked: `describe_instances`, `describe_security_groups`, `describe_vpcs`, `describe_subnets`, `list_buckets`, `describe_db_instances`. Grep of `cli/infracanvas/shadow/detector.py` shows no `create_*`, `delete_*`, `put_*`, `modify_*`, or `terminate_*` calls | Yes |
| T-02-11 | Tampering | `cost/estimator.py` region | Region read from `node.region` (from user's `.tf`) at `cli/infracanvas/cost/estimator.py:120`. Incorrect region → incorrect cost only; no security impact, no remote call | Yes |
| T-02-13 | DoS | `--policy` many YAML | Local CLI, user-invoked; blast radius is the user's own terminal session | Yes |
| T-02-15 | Info Disclosure | `FindingCard` framework_ids | Framework IDs (CIS/NIST/SOC2/PCI-DSS) are non-sensitive public control identifiers. In gate mode (`gateMode=true`), `viewer/src/components/FindingCard.tsx:55-61` renders blurred placeholder divs — finding title, description, evidence, remediation, and framework tags are all inside the non-gated else-branch at lines 62-112, and therefore omitted from the DOM when `gateMode=true`. `export_html(..., gate_mode=True)` is used by default in `scan`/`serve` flows (`cli/infracanvas/main.py:357, 468`) | Yes |
| T-02-18 | Info Disclosure | Docker image layers | Source code is open-source (MIT). No credentials, `.env` files, or tokens are copied into the image (verified in `Dockerfile`). Viewer `dist/` and Python site-packages only | Yes |

---

## Unregistered Threat Flags from SUMMARY.md

All 8 phase summaries (`02-00-SUMMARY.md` through `02-08-SUMMARY.md`) report **no new
threats / no unregistered flags**. Each summary explicitly cross-references the registered
threat IDs and reconfirms the accepted-risk reasoning:

- `02-00-SUMMARY.md`: "None — test-only files with skip markers, no runtime logic."
- `02-01-SUMMARY.md`: `load_policy_rules` within T-02-01 scope; mitigation present.
- `02-02-SUMMARY.md`: T-02-04 accepted — dict read/copy only.
- `02-03-SUMMARY.md`: T-02-06 static EOL accepted; T-02-07 package-internal accepted.
- `02-04-SUMMARY.md`: T-02-08 mitigated — generic RuntimeError, no credential exposure.
- `02-05-SUMMARY.md`: T-02-11 accepted — region from user's `.tf`, cost-only impact.
- `02-06-SUMMARY.md`: T-02-12 mitigated by existing `is_dir` + `safe_load`; T-02-14 via `sev_order.index`.
- `02-07-SUMMARY.md`: T-02-15 accepted — framework IDs non-sensitive, gate mode blurs details.
- `02-08-SUMMARY.md`: "No new threats. T-02-16, T-02-17 mitigated as planned."

No unregistered flags logged.

---

## Scope Notes

- Audit verified mitigation evidence exists in cited files at cited behaviours. Audit did
  not re-derive threat scope or scan for new threat classes.
- `block_on = open` policy: 0 open threats → non-blocking.
- ASVS Level 1 scope is appropriate: no authentication surface, no session management,
  no remote services exposed by this phase.
