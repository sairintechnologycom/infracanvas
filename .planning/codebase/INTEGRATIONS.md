# External Integrations

**Analysis Date:** 2026-04-15

## APIs & External Services

**Terraform API:**
- Terraform CLI integration (not direct API)
  - Parses `.tf` files from filesystem
  - Reads `terraform plan` output (`terraform show -json plan.bin`)
  - No credentials required; filesystem-based

**Google Fonts:**
- Used in scorecard export CSS
  - `@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=JetBrains+Mono:wght@400;500&display=swap')`
  - Located in: `cli/infracanvas/export/scorecard.py`
  - Purpose: Typography for generated security score card reports
  - No auth required

## Data Storage

**Databases:**
- None - This is a static analysis tool
- No persistent data layer
- All computation happens in-memory during scan execution

**File Storage:**
- Local filesystem only
  - Terraform files: read from user's project directory
  - Plans: read from `terraform show -json` output
  - Configuration: `.infracanvas.yml` config file loaded from project root or parent directories
  - Outputs: HTML reports, JSON graphs, score cards written to disk
- No cloud storage integration

**Caching:**
- None - Tool is designed for single-scan execution
- File system watching available via Watchdog (4.0.1) but not actively used in core flow

## Authentication & Identity

**Auth Provider:**
- None required
- Tool operates entirely on local Terraform files
- No API authentication, no cloud credentials needed (except for user's own Terraform state if scanning live infra)

## Monitoring & Observability

**Error Tracking:**
- None - No external error tracking service
- Errors logged to stdout/stderr via Rich formatting

**Logs:**
- Rich terminal output
  - Uses `rich.console.Console` for colored, formatted terminal output
  - Separate stderr stream for CI mode diagnostics (`_ci_console`)
  - Located in: `cli/infracanvas/main.py` (lines 38-39)
- No log aggregation service

**Diagnostics:**
- Verbose flag: `--verbose` option for detailed parse/security evaluation output
- Manual inspection of `.ruff_cache/` and test reports

## CI/CD & Deployment

**Hosting:**
- PyPI package distribution (infracanvas)
- GitHub repository: https://github.com/infracanvas/infracanvas
- Docker image: `python:3.12-slim` (Dockerfile)
- Website: https://infracanvas.dev

**CI Pipeline:**
- GitHub Actions (recommended in README, line 75-81)
- No explicit GitHub Actions workflow files detected in `.github/workflows/`
- Tool designed for CI integration: `--ci` flag with exit codes (0: pass, 1: findings, 2: error)

**Package Distribution:**
- PyPI: `pip install infracanvas`
- Version: 0.1.0 (defined in `cli/pyproject.toml` and `viewer/package.json`)
- Build system: Hatchling (Python) + Vite (JavaScript)

## Environment Configuration

**Required env vars:**
- None explicitly required
- Config file: `.infracanvas.yml` (optional, located in project root or parent directories)

**Secrets location:**
- No secrets management integration
- User handles Terraform credentials separately (via Terraform AWS provider configuration)
- No API keys, tokens, or passwords required for InfraCanvas itself

**Configuration file:**
- `.infracanvas.yml` (YAML format)
- Optional; if missing, defaults applied
- Supported fields:
  - `severity_threshold`: minimum severity level to report (default: "high")
  - `ignore_rules`: list of rule IDs to skip
  - `output_dir`: directory for output files (default: ".")
  - `open_browser`: auto-open browser on scan (default: true)
  - `provider`: cloud provider (default: "aws")
- Located in: `cli/infracanvas/config.py` (lines 11-16)

## Webhooks & Callbacks

**Incoming:**
- None - Tool is stateless and event-driven only by user commands

**Outgoing:**
- None - No external callbacks or webhooks triggered
- Browser auto-open: Uses `webbrowser` module (Python stdlib) to launch local HTML file
  - Controlled by `open_browser` config flag
  - Located in: `cli/infracanvas/main.py`

## Report Export Formats

**HTML:**
- Single-file HTML export (embedded React app + data)
- Uses vite-plugin-singlefile for bundling
- Template: `cli/infracanvas/export/viewer_template.html` (478KB compiled)
- Contains entire viewer application + inline graph data

**JSON:**
- Graph export as JSON structure
- Schema matches TypeScript types in `viewer/src/types.ts`
- Contains: nodes, edges, metadata, summary, findings

**Scorecard (PDF-friendly HTML):**
- Security score card as formatted HTML
- CSS includes Google Fonts import
- Letter-graded score across categories: encryption, networking, IAM, logging
- Location: `cli/infracanvas/export/scorecard.py`

## AWS Integration

**AWS Resource Support:**
- Static resource type mapping (no API calls)
- Supported resource types: EC2, RDS, S3, Lambda, IAM, KMS, VPC, Security Groups, Load Balancers, ECS, DynamoDB, SQS, SNS, CloudFront, NAT Gateway, EKS
- Icon mapping to AWS service icons (aws-react-icons package)
- Located in: `viewer/src/components/icons/AwsIcon.tsx`

**Cost Estimation:**
- Hardcoded AWS pricing (us-east-1, on-demand rates)
- EC2 prices: lines 15-20 in `cli/infracanvas/cost/estimator.py`
- RDS prices: lines 22-25
- Flat monthly rates: lines 27-33
- Usage-based services: lines 35-40
- No API integration for real-time pricing
- Cost delta calculated from Terraform plan changes

**Provider Assumption:**
- Designed for AWS infrastructure
- Config field `provider: "aws"` (default)
- Could be extended to other providers (GCP, Azure) but not currently integrated

---

*Integration audit: 2026-04-15*
