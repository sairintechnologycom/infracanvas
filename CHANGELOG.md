# Changelog

All notable changes to InfraCanvas are documented here.

## v0.1.1 — 2026-05-20

First post-launch release. Closes UAT gaps surfaced after v0.1.0 and adds 8 high-impact CIS rules.

### Fixed
- **Parser hang on malformed HCL.** `infracanvas scan` on a `.tf` file with a missing brace or unterminated string used to consume 96% CPU indefinitely. The HCL parser now runs under a 30 s `SIGALRM` deadline (override with `INFRACANVAS_PARSE_TIMEOUT_S`) and surfaces a clear error.
- **Score card math.** Per-dimension scores were stuck at 100/A even when the overall score showed Critical findings, because the category-to-rule map only covered the original Phase 1 rule set. Expanded mapping covers all AWS / Azure / NET rules.
- **`--fail-on` was a silent no-op outside `--ci`.** `infracanvas scan ./bad-infra --fail-on critical` returned exit 0 with criticals present. Now gates the exit code in all output modes (default, `--quiet`, `--json`).
- **S3-encryption false positive.** `SEC-002 "S3 Bucket Missing Encryption"` fired on buckets that *had* encryption via the modern `aws_s3_bucket_server_side_encryption_configuration` sibling resource. The engine now folds five S3 companion resources (encryption, ACL, public-access-block, versioning, logging) onto their parent bucket before rule evaluation. `SEC-001` now also fires when a separate `aws_s3_bucket_acl.X` is `public-read`.
- **PEP 604 union annotations** (`Path | None`) crashed Typer 0.12.3 under `CliRunner`. Bumped `typer >= 0.15`, relaxed `click >= 8.1, < 9`. The PyPI v0.1.0 binary was unaffected (subprocess path).
- **Per-module coverage gate** triggered false-red when `pytest cli/tests/` was run from the project root against a stale `.coverage` file. The gate now only runs when `pytest-cov` is active for the session.

### Added
Eight new high-impact CIS rules. Coverage of the high-impact CIS controls on the UAT fixture went from ~50% to ~85%:

| Rule | Severity | Description |
|---|---|---|
| `SEC-007` (extended) | critical | IAM wildcard `Action: "*"` now also fires on `aws_iam_role_policy` / `_user_policy` / `_group_policy` (previously only `aws_iam_policy`) |
| `SEC-031` | high | RDS instance has `storage_encrypted = false` |
| `SEC-032` | critical | RDS master `password` is a hardcoded literal in source |
| `AZ-011` | high | Linux VM `disable_password_authentication = false` |
| `AZ-012` | critical | Azure VM `admin_password` is a hardcoded literal in source |
| `AZ-013` | high | Storage `enable_https_traffic_only = false` (legacy attribute) |
| `AZ-014` | high | Storage `public_network_access_enabled = true` |
| `AZ-015` | medium | SQL Server `minimum_tls_version` below 1.2 |
| `AZ-016` | critical | SQL Server `administrator_login_password` is a hardcoded literal |

Plus engine enhancements:
- `contains` operator now normalises Python-dict-repr → JSON style, so rules can author needles in natural `"Action":"*"` form against `jsonencode()` HCL output.
- new `not_starts_with` operator powers literal-secret detection (matches attributes that don't begin with a `${...}` interpolation).

### Infrastructure
- GitHub Actions CI green (test-cli, test-viewer, test-agent, lint) on every push to `main`.
- Release workflow primed for PyPI Trusted Publishing on `git push origin v*`. No PyPI token in repo secrets.
- `backend-ci` parked behind `workflow_dispatch` until Phase 6 provisions the FastAPI service deps.

## v0.1.0 — 2026-05-19

Initial PyPI release. Canvas (Terraform → annotated interactive HTML diagram) MVP for AWS + Azure.

- 30 AWS + 10 Azure security rules with CIS / NIST / SOC2 / PCI-DSS framework tags
- Single-file HTML output with embedded React viewer (~3.5 MB)
- Letter-grade Report Card across 5 dimensions
- `terraform plan` overlay (added / changed / deleted nodes)
- Cost estimates per resource and per group
- 100 % local execution — no cloud credentials, no SaaS account
