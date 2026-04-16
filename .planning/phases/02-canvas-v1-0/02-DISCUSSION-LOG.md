# Phase 2: Canvas v1.0 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-16
**Phase:** 02-canvas-v1-0
**Areas discussed:** Shadow infra opt-in, Azure scan entry point, Policy engine behavior, Drift diff UX

---

## Shadow Infra Opt-In

| Option | Description | Selected |
|--------|-------------|----------|
| `--shadow` flag | Opt-in flag; auto-detects AWS credentials (env → ~/.aws → instance profile) | ✓ |
| Auto-detect if creds present | Always attempt shadow scan when credentials are available | |
| `--shadow` + explicit region | Opt-in and require `--region` alongside the flag | |

**User's choice:** `--shadow` flag (recommended)

---

| Option | Description | Selected |
|--------|-------------|----------|
| Warn and continue | Yellow warning, rest of scan proceeds | ✓ |
| Error and exit | Hard fail with exit code 2 | |

**User's choice:** Warn and continue without shadow scan (recommended)

---

| Option | Description | Selected |
|--------|-------------|----------|
| EC2 + RDS + S3 only | Focused scope, minimal IAM permissions | |
| All 15 supported types | Comprehensive, more permissions needed | |
| Claude's discretion | Planner picks based on feasibility + signal | ✓ |

**User's choice:** Claude's discretion

---

| Option | Description | Selected |
|--------|-------------|----------|
| Dashed border + 'Shadow' badge | Grey badge, dashed border per SHD-02 spec | ✓ |
| Separate 'Shadow' group node | Visually isolated group in diagram | |

**User's choice:** Dashed border + 'Shadow' badge (recommended)

---

| Option | Description | Selected |
|--------|-------------|----------|
| Infer region from .tf files | Detect from provider block / resource attributes | ✓ |
| Always scan all regions | Full account sweep | |
| `--region` flag overrides | Infer by default, override with flag | |

**User's choice:** Infer region from .tf files (recommended)

---

## Azure Scan Entry Point

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-detect Azure .tf files | No flag needed; azurerm resources auto-detected | ✓ |
| `--provider azure` flag | Explicit opt-in | |
| Separate `azure` subcommand | `infracanvas azure scan ./tf` | |

**User's choice:** Auto-detect Azure .tf files (recommended)

---

| Option | Description | Selected |
|--------|-------------|----------|
| ARM_* env vars only | Read standard ARM_CLIENT_ID etc. from environment | ✓ |
| Azure CLI auth fallback | Try env vars, fall back to `az login` credentials | |
| Explicit `--azure-creds` flag | Service principal JSON file path | |

**User's choice:** ARM_* env vars only (recommended)

---

| Option | Description | Selected |
|--------|-------------|----------|
| Combined diagram, visually grouped | Single diagram with AWS groups + Azure groups | ✓ |
| Separate tabs / toggle | One diagram per cloud, switchable | |
| Claude's discretion | Planner decides based on GroupNode capabilities | |

**User's choice:** Combined diagram, visually grouped (recommended)

---

## Policy Engine Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Findings in diagram + CI exit code | Violations in diagram as findings + non-zero exit in CI | ✓ |
| Separate policy report | Separate `infracanvas-policy.html`, not in main diagram | |
| CI-only, no diagram overlay | Pure CI gate, text report only | |

**User's choice:** Findings in diagram + CI exit code (recommended)

---

| Option | Description | Selected |
|--------|-------------|----------|
| Always blocks in CI when violations exist | Uses existing CI auto-detection (D-11 Phase 1) | ✓ |
| Report-only by default, `--fail-on-policy` to block | Permissive default | |
| Controlled by `--fail-on` flag (CLX-01) | Policy violations get a severity level | |

**User's choice:** Always blocks in CI when violations exist (recommended)

---

| Option | Description | Selected |
|--------|-------------|----------|
| Severity from policy YAML | Each rule declares its own severity | ✓ |
| Always 'critical' | All policy violations are Critical | |
| Claude's discretion | Planner picks default severity scheme | |

**User's choice:** Severity from policy YAML (recommended)

---

| Option | Description | Selected |
|--------|-------------|----------|
| Extend scan pipeline | `infracanvas scan --policy ./policies` | ✓ |
| Separate command | `infracanvas policy ./terraform --policy ./policies` | |

**User's choice:** Extend scan pipeline (recommended)

---

## Drift Diff UX

| Option | Description | Selected |
|--------|-------------|----------|
| DetailPanel expansion | "Changes" tab in DetailPanel alongside "Findings" | ✓ |
| Inline tooltip on hover | Diff tooltip overlay on hover | |

**User's choice:** DetailPanel expansion (recommended) — confirmed the mockup showing `Findings | Changes` tabs

---

| Option | Description | Selected |
|--------|-------------|----------|
| Changed attributes only | Only attributes that differ | ✓ |
| All resource attributes | Every attribute, changed ones highlighted | |

**User's choice:** Changed attributes only (recommended)

---

| Option | Description | Selected |
|--------|-------------|----------|
| Node border colour | Green/red/amber/grey border; body stays normal | ✓ |
| Node background tint | Subtle colour fill on node card | |

**User's choice:** Node border colour (recommended)

---

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, same as scan | Saves `infracanvas-plan.html` and opens browser | ✓ |
| Save only, no auto-open | File saved, no browser open | |

**User's choice:** Yes, same as scan (recommended)

---

## Claude's Discretion

- Shadow infra resource type scope (EC2/RDS/S3 likely candidates — planner decides)
- Exact 20 new AWS security rules (SEC-011 through SEC-030)
- Compliance framework tag mapping for all 40 rules
- Azure icon sources
- CI flag design (CLX-01 `--ci`, `--fail-on`, `--quiet`, `--ignore`, `--severity`)
- Watch mode debounce timing (CLX-02)
- Docker base image and multi-arch configuration (DST-01)

## Deferred Ideas

- Infracost pricing API integration — static fallback sufficient for Phase 2; API key UX deferred to planner
- Azure CLI auth fallback (`az login`) — Phase 4+ enhancement
- Cross-cloud cost comparison — Phase 4 CostLens
- Multi-region parallel scanning — Phase 4 SaaS
- Policy engine v2 (OPA/Rego) — Phase 5 Enterprise
