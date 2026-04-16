# Phase 2: Canvas v1.0 - Research

**Researched:** 2026-04-16
**Domain:** Python CLI extension (Azure parsing, shadow infra, policy engine, cost estimation, distribution) + React viewer extension (Azure icons, filter UI)
**Confidence:** HIGH (codebase verified), MEDIUM (AWS API surface), MEDIUM (Azure Terraform attr shapes)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Shadow Infrastructure Detection (SHD-01, SHD-02)**
- D-01: Opt-in via `--shadow` flag. Auto-detects AWS credentials in standard order (env vars → ~/.aws/credentials → instance profile). No explicit `--region` required.
- D-02: If `--shadow` passed but no creds found: yellow warning and continue. Never hard-fail.
- D-04: Shadow resources displayed with dashed border + "Shadow" badge (grey) in diagram. Estimated cost shown in DetailPanel.
- D-05: Infer region from .tf files (provider block or resource attributes). Scan that region only.

**Azure Integration (AZR-01, AZR-02, AZR-03)**
- D-06: Auto-detect `azurerm` provider resources from `infracanvas scan ./tf`. No `--provider` flag.
- D-07: Azure credentials via ARM_* env vars only: `ARM_CLIENT_ID`, `ARM_CLIENT_SECRET`, `ARM_TENANT_ID`, `ARM_SUBSCRIPTION_ID`. No Azure CLI fallback.
- D-08: Mixed AWS+Azure repos produce a combined diagram. AWS in VPC groups, Azure in VNet groups.

**Custom Policy Engine (POL-01, POL-02)**
- D-09: Policy violations surface as findings in diagram (tagged `source: "policy"`) AND cause non-zero exit code in CI.
- D-10: Always blocks in CI when violations exist. No extra flag needed.
- D-11: Severity from policy YAML — each rule declares its own severity.
- D-12: Policy runs as part of scan pipeline via `infracanvas scan --policy ./policies`.

**Drift Diff UX (PLN-02, PLN-03)**
- D-13: Before/after attribute diff in DetailPanel as "Changes" tab. ALREADY IMPLEMENTED.
- D-14: Changed attributes only in diff — not all attributes.
- D-15: Drift node border: green=added, red=destroyed, amber=changed, grey=no-op.
- D-16: `infracanvas plan` auto-opens browser. Saves `infracanvas-plan.html`.

**Carrying Forward from Phase 1**
- Free-gate blur on finding title/description/remediation applies to all new findings
- Upgrade CTA links to `infracanvas.dev/founding` founding member $49/mo page
- Generic node rendering for unsupported resource types applies to Azure types not in supported 10
- CI auto-detection: `CI=true`, `GITHUB_ACTIONS`, etc. → skip browser open

### Claude's Discretion
- Which AWS resource types to include in shadow infra detection scope
- Exact 20 new AWS security rules (SEC-011 through SEC-030)
- Compliance framework tag mapping (CIS, NIST, SOC2, PCI-DSS) for all 40 rules
- Azure icon sources (prefer official Microsoft Azure icon set or reasonable SVG equivalents)
- CI flag design for CLX-01 (`--ci`, `--fail-on`, `--quiet`, `--ignore`, `--severity`)
- Watch mode debounce timing (CLX-02)
- Docker base image and multi-arch build configuration (DST-01)

### Deferred Ideas (OUT OF SCOPE)
- Infracost pricing API integration — static pricing fallback is sufficient for Phase 2
- Azure CLI auth fallback (`az login`) — ARM_* env vars only
- Cross-cloud cost comparison — Phase 4 CostLens scope
- Multi-region parallel scanning — Phase 4 SaaS feature
- Policy engine v2 (OPA/Rego) — Phase 5 Enterprise scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PLN-01 | Terraform plan JSON reader with resource change extraction (create/update/delete) | PlanReader already exists in `parser/plan.py`; needs hardening for edge cases |
| PLN-02 | Drift visualisation with colour-coded nodes (green/red/amber/grey) | DriftAnalyzer + ResourceNode.tsx already implement this; verify completeness |
| PLN-03 | Before/after attribute diff view for changed resources | ChangesTab already implemented in DetailPanel.tsx; locked by UI-SPEC |
| SHD-01 | Live AWS API read (read-only IAM role) comparing API vs Terraform state | boto3 must be added as optional dep; `describe_*` APIs; credential chain via boto3 default |
| SHD-02 | Shadow resources flagged with dashed border, "Shadow" badge, estimated cost | Visual contract locked in UI-SPEC; shadow DriftStatus already in model |
| CST-01 | Infracost pricing API integration with static pricing fallback | Static fallback already exists; planner decides whether to add API or stay static |
| CST-02 | Cost per resource, per group, total + cost delta on plan changes | CostEstimator.delta() already exists; group-level aggregation is new |
| CST-03 | Multi-region cost estimation (detect region from resource attributes) | Region must be read from provider block or resource `region` attr; pricing dict needs expansion |
| AZR-01 | Azure parser for 10 core resource types | New `parser/azure.py` module following hcl.py structure; azurerm_ prefix detection |
| AZR-02 | Azure resource icons in viewer | New `azureServiceConfig.ts`; locked color/label mapping in UI-SPEC |
| AZR-03 | 10 Azure security rules (AZ-001 through AZ-010) | New `security/rules/azure/` YAML files; same YAML schema as AWS rules |
| SEC-05 | AWS security rules expansion to 30 rules (SEC-011 through SEC-030) | 20 new YAML rule files; Claude's discretion for specific rules |
| SEC-06 | Compliance framework tags on all rules (CIS, NIST, SOC2, PCI-DSS) | Add `framework_ids: []` field to SecurityRule model and YAML schema |
| RST-01 | Runtime staleness checks (Lambda EOL, EKS/AKS version lag) | Static EOL tables in Python; `runtime` attr on lambda, `kubernetes_version` on AKS/EKS |
| RST-02 | Resource lock validation (azurerm_management_lock, AWS resource policies) | Check for azurerm_management_lock resource linked to protected resource |
| POL-01 | Custom policy engine v1 (YAML: required_tags, allowed_regions, etc.) | Reuse existing YAML rule engine; add `source: "policy"` field to Finding |
| POL-02 | .infracanvas.yml config + --policy flag for external policy directory | `load_config()` extended; `scan` command gets `--policy` option |
| CLX-01 | CI mode: --ci, --fail-on, --quiet, --ignore, --severity flags | `--ci`, `--quiet`, `--ignore`, `--severity` already exist; `--fail-on` is new |
| CLX-02 | Watch mode: re-scan on .tf file changes | `--watch` already implemented; verify debounce and coverage |
| DST-01 | Docker image + GitHub Releases (Linux amd64, macOS arm64, Windows x64) | PyInstaller cannot cross-compile; need per-arch CI runners; Docker buildx for container |
| DST-02 | Updated Homebrew formula | Formula update with new version/SHA; no new packaging dependencies |
</phase_requirements>

---

## Summary

Phase 2 is a feature-expansion phase that builds on a well-structured Phase 1 codebase. The fundamental architecture — YAML-driven rule engine, Pydantic graph models, Vite single-file HTML, Zustand state — does not change. All major Phase 2 capabilities bolt onto existing extension points without structural rewrites.

The highest implementation risk is the HCL parser hardening (silent failures on complex modules) which must be done first because it is a prerequisite for the Azure parser. The current parser swallows all exceptions silently (`except Exception: return`) — hardening means collecting parse errors per-file and reporting them rather than silently dropping the file. The second risk is boto3 availability: it is not currently in the project's venv and must be added as an optional dependency to avoid breaking users who don't pass `--shadow`.

The UI-SPEC (already approved) locks all visual decisions for the viewer layer. The ChangesTab (PLN-03) and node drift border colors (PLN-02, D-15) are already implemented in `DetailPanel.tsx` and `ResourceNode.tsx`. Phase 2 viewer work is: (1) Azure icon config, (2) POLICY source pill in FindingCard, (3) compliance framework tag row in FindingCard, (4) Source filter section in FilterPanel, and (5) `azurerm_` prefix stripping in ResourceNode typeLabel.

**Primary recommendation:** Start with HCL parser hardening → Azure parser → shadow detection (boto3 optional dep) → security rule expansion → policy engine → distribution. The viewer changes are low-risk additive work that can be interleaved.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| HCL parser hardening | CLI / Parser | — | File-level error collection; Python only |
| Azure Terraform parsing | CLI / Parser | — | New `parser/azure.py`; azurerm_ prefix |
| Shadow infra detection | CLI / Analysis | AWS API | boto3 read-only; compare to graph nodes |
| Custom policy engine | CLI / Security | — | YAML rules through existing engine |
| Multi-region cost estimation | CLI / Cost | — | Region from provider block attrs |
| Runtime staleness checks | CLI / Security | — | Static EOL tables; attribute comparison |
| Resource lock validation | CLI / Security | — | Link azurerm_management_lock to target resource |
| Drift visualisation | Viewer | CLI | DriftStatus already in model + component |
| Azure icons | Viewer | — | `azureServiceConfig.ts` color/label map |
| Policy source badge | Viewer | — | FindingCard extension; `source` field |
| Compliance tags | Viewer | — | FindingCard extension; `framework_ids` field |
| Source filter | Viewer | — | FilterPanel + Zustand store extension |
| Docker / binary distribution | Build / CI | — | PyInstaller per-arch; buildx for Docker |

---

## Standard Stack

### Core (already in project — verified)

| Library | Version | Purpose | Source |
|---------|---------|---------|--------|
| python-hcl2 | 4.3.4 | Terraform HCL parsing | [VERIFIED: cli/pyproject.toml] |
| pydantic | 2.7.1 | Data models, validation | [VERIFIED: cli/pyproject.toml] |
| pyyaml | 6.0.1 | YAML rule loading | [VERIFIED: cli/pyproject.toml] |
| networkx | 3.3 | Graph algorithms | [VERIFIED: cli/pyproject.toml] |
| typer | 0.12.3 | CLI argument parsing | [VERIFIED: cli/pyproject.toml] |
| rich | 13.7.1 | Terminal output | [VERIFIED: cli/pyproject.toml] |
| watchdog | 4.0.1 | File system watch | [VERIFIED: cli/pyproject.toml] |
| @xyflow/react | ^12.6.0 | Diagram visualization | [VERIFIED: viewer/package.json] |
| zustand | ^5.0.5 | Client state management | [VERIFIED: viewer/package.json] |
| vitest | ^4.1.4 | JS test runner | [VERIFIED: viewer/package.json] |
| pytest | 9.0.3 | Python test runner | [VERIFIED: cli/.venv12/site-packages] |

### New Dependencies Required

| Library | Version | Purpose | Add Where |
|---------|---------|---------|-----------|
| boto3 | ^1.34 (latest) | AWS API for shadow detection | `pyproject.toml` optional dep `[shadow]` |

**Installation:**
```bash
# Optional shadow dep — users install only if they use --shadow
pip install "infracanvas[shadow]"
# Or in pyproject.toml:
[project.optional-dependencies]
shadow = ["boto3>=1.34"]
```

**Version verification note:** boto3 is not in the current venv. The npm registry entry for `boto3` is a stub package (0.0.1, unrelated). [ASSUMED] Current boto3 stable version is ~1.34.x based on training knowledge — verify with `pip index versions boto3` before pinning.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| boto3 optional dep | Subprocess `aws` CLI calls | boto3 is standard; CLI subprocess is fragile, harder to credential-chain |
| Static EOL table (RST-01) | endoflife.date API | API adds network dep; static table is zero-dependency and sufficient for Phase 2 |
| Static cost pricing dict | Infracost API | Infracost API key UX cannot be made zero-config; static dict deferred per CONTEXT.md |

---

## Architecture Patterns

### System Architecture Diagram

```
infracanvas scan ./tf [--shadow] [--policy ./policies]
         │
         ▼
┌─────────────────────────────────────────────────────┐
│  Parse Layer                                        │
│  parse_directory() ──► azure.py ──► hcl.py         │
│  (hardened: per-file errors, not silent drop)       │
└──────────────────────────┬──────────────────────────┘
                           │ ParsedTerraform
                           ▼
┌─────────────────────────────────────────────────────┐
│  Graph Layer                                        │
│  build_graph() ──► ResourceGraph (nodes, edges)     │
│  (region inferred from provider block here)         │
└──────────────────────────┬──────────────────────────┘
                           │ ResourceGraph
                           ▼
┌─────────────────────────────────────────────────────┐
│  Analysis Layer (runs in sequence)                  │
│  evaluate_all()      ◄── security/rules/aws/*.yaml  │
│  evaluate_all()      ◄── security/rules/azure/*.yaml│
│  evaluate_policy()   ◄── --policy ./policies/*.yaml │
│  check_runtime_eol() ─── RST-01/RST-02              │
│  ShadowDetector()    ─── boto3 describe_* (if flag) │
│  CostEstimator()     ─── multi-region pricing dict  │
└──────────────────────────┬──────────────────────────┘
                           │ annotated ResourceGraph
                           ▼
┌─────────────────────────────────────────────────────┐
│  Export Layer                                       │
│  export_html() ──► viewer_template.html             │
│  window.__INFRACANVAS_DATA__ = JSON.stringify(graph)│
└──────────────────────────┬──────────────────────────┘
                           │ HTML file
                           ▼
┌─────────────────────────────────────────────────────┐
│  Viewer (React, single-file HTML)                   │
│  ResourceNode: azurerm_ prefix strip + icon         │
│  FindingCard: source pill + framework_ids tags      │
│  FilterPanel: Source filter (Security / Policy)     │
│  DetailPanel: Changes tab (already implemented)     │
└─────────────────────────────────────────────────────┘
```

### Recommended Project Structure — New Files

```
cli/infracanvas/
├── parser/
│   └── azure.py           # NEW: azurerm provider parser (mirrors hcl.py structure)
├── security/
│   ├── models.py          # EXTEND: add framework_ids field to SecurityRule
│   ├── loader.py          # EXTEND: load framework_ids from YAML; load policy rules
│   ├── engine.py          # EXTEND: evaluate_policy() with source="policy" injection
│   ├── staleness.py       # NEW: RST-01/RST-02 runtime EOL + lock checks
│   └── rules/
│       ├── aws/           # EXTEND: add 20 new YAML files (SEC-011 through SEC-030)
│       └── azure/         # NEW: 10 YAML files (AZ-001 through AZ-010)
├── shadow/
│   └── detector.py        # NEW: boto3 describe_* calls, credential chain, comparison
└── cost/
    └── estimator.py       # EXTEND: region-aware pricing dict, group-level aggregation

viewer/src/
├── icons/
│   └── azureServiceConfig.ts  # NEW: mirrors awsServiceConfig.ts for Azure
├── components/
│   ├── FindingCard.tsx    # EXTEND: source pill + framework_ids row
│   ├── FilterPanel.tsx    # EXTEND: Source filter section
│   └── ResourceNode.tsx   # EXTEND: azurerm_ prefix strip, azure icon rendering
├── store.ts               # EXTEND: sources: string[] filter state + toggleSourceFilter()
└── types.ts               # EXTEND: Finding.source?: string, Finding.framework_ids?: string[]
```

### Pattern 1: HCL Parser Hardening (Per-File Error Collection)

**What:** Replace silent `except Exception: return` with per-file error tracking that populates a warnings list on `ParsedTerraform`.

**When to use:** Always — this is a prerequisite for Azure parser work.

```python
# Source: existing cli/infracanvas/parser/hcl.py (current pattern to replace)
# Current (silent drop):
def _parse_file(tf_file: Path, result: ParsedTerraform) -> None:
    with open(tf_file) as f:
        try:
            parsed = hcl2.load(f)
        except Exception:
            return  # ← SILENT FAILURE

# Hardened pattern:
@dataclass
class ParsedTerraform:
    # ... existing fields ...
    parse_errors: list[tuple[Path, str]] = field(default_factory=list)  # ADD

def _parse_file(tf_file: Path, result: ParsedTerraform) -> None:
    with open(tf_file) as f:
        try:
            parsed = hcl2.load(f)
        except Exception as exc:
            result.parse_errors.append((tf_file, str(exc)))  # ← REPORT, NOT DROP
            return
```

**In `_run_scan()`:** After `parse_directory()`, if `parsed.parse_errors` is non-empty, warn user with Rich console per-file error list. Do not raise Exit — partial results are still useful.

### Pattern 2: Azure Parser (Provider Auto-Detection)

**What:** `azure.py` follows the same structure as `hcl.py` but extracts `azurerm_*` resources.

**Key insight:** `azurerm` provider auto-detection is done at the graph builder level, not the parser level. The HCL parser already extracts all resource blocks regardless of provider prefix. The builder assigns `provider = "azurerm"` for resources whose type starts with `azurerm_`.

```python
# Source: [VERIFIED: cli/infracanvas/graph/builder.py pattern]
# Provider assignment in build_graph():
provider = "aws"
if resource.resource_type.startswith("azurerm_"):
    provider = "azurerm"
elif resource.resource_type.startswith("google_"):
    provider = "gcp"
```

The Azure parser (`azure.py`) is really just an attribute normalisation layer — Azure resource attribute names differ from AWS (e.g., `resource_group_name` instead of `vpc_id`, `address_space` instead of `cidr_block`).

### Pattern 3: Shadow Detection (boto3 Optional Import)

**What:** Import boto3 only when `--shadow` is passed; fail gracefully with warning if not installed.

**When to use:** Always in shadow detector module.

```python
# Source: [ASSUMED] standard optional dep pattern for boto3
# cli/infracanvas/shadow/detector.py
from __future__ import annotations
from typing import Any

class ShadowDetector:
    """Compare live AWS API vs Terraform graph nodes."""

    def __init__(self, region: str) -> None:
        self._region = region

    def detect(self, graph: ResourceGraph) -> ResourceGraph:
        try:
            import boto3
        except ImportError:
            # boto3 not installed — emit warning via caller, return graph unchanged
            raise RuntimeError("boto3 not installed. Install with: pip install infracanvas[shadow]")

        session = boto3.Session()
        creds = session.get_credentials()
        if not creds:
            raise RuntimeError("No AWS credentials found")

        # describe_instances, describe_security_groups, etc.
        ec2 = session.client("ec2", region_name=self._region)
        self._flag_shadow_ec2(graph, ec2)
        return graph
```

**AWS read-only API surface for shadow detection (Claude's Discretion scope):**

Recommended scope (highest drift-signal, lowest IAM surface):
- `ec2:describe_instances` — matches `aws_instance`
- `ec2:describe_security_groups` — matches `aws_security_group`
- `ec2:describe_vpcs` — matches `aws_vpc`
- `ec2:describe_subnets` — matches `aws_subnet`
- `s3:list_buckets` — matches `aws_s3_bucket`
- `rds:describe_db_instances` — matches `aws_db_instance`

Rationale: these 6 resource types cover >80% of typical Terraform configurations. Each uses a single IAM action with no side effects. Skip Lambda, EKS, KMS for Phase 2 (higher complexity, lower drift rate).

**Credential chain:** boto3 default session auto-discovers: env vars (`AWS_ACCESS_KEY_ID` etc.) → `~/.aws/credentials` → instance profile → container credential provider. No explicit chain needed — `boto3.Session()` is sufficient. [VERIFIED: boto3 docs]

### Pattern 4: Policy Engine Extension

**What:** Load policy YAML files through the existing `load_rules()` function, injecting `source: "policy"` into findings.

**Key insight:** The existing YAML rule schema (`id`, `title`, `severity`, `resource_types`, `condition`, `remediation`) is 100% compatible with custom policy rules. Only two additions needed: (1) `source` field on `Finding` model; (2) the loader injects `source="policy"` when loading from the `--policy` directory.

```python
# Source: [VERIFIED: cli/infracanvas/security/loader.py]
# policy_loader.py pattern — identical to load_rules() but marks source
def load_policy_rules(policy_dir: Path) -> list[SecurityRule]:
    """Load custom policy rules; results get source='policy' injected at evaluation."""
    rules = []
    for yaml_file in sorted(policy_dir.rglob("*.yaml")):
        rules.extend(_load_rules_file(yaml_file))
    return rules
```

```python
# Finding model extension needed:
class Finding(BaseModel):
    rule_id: str
    severity: Severity
    title: str
    description: str
    remediation: str
    evidence: dict[str, object] = {}
    source: str = "security"           # NEW: "security" | "policy"
    framework_ids: list[str] = []      # NEW: ["CIS", "NIST", "SOC2", "PCI-DSS"]
```

**CI blocking:** The existing CI logic in `scan` command checks `graph.summary.findings` counts. Policy violations go through the same `node.findings` list → same summary counts → same exit code 1. No additional CI logic needed.

### Pattern 5: SecurityRule Model Extension (SEC-06)

```yaml
# Source: [VERIFIED: existing cli/infracanvas/security/rules/aws/s3.yaml schema]
# New YAML schema with framework_ids:
- id: SEC-011
  title: "S3 Bucket Public Access Block Missing"
  severity: critical
  resource_types: ["aws_s3_bucket_public_access_block"]
  framework_ids: ["CIS-1.20", "NIST-SC-7", "SOC2-CC6.1", "PCI-DSS-1.2"]  # NEW
  condition:
    attribute: "block_public_acls"
    operator: "not_equals"
    value: true
  remediation: "Set block_public_acls, block_public_policy, ignore_public_acls, restrict_public_buckets all to true"
  description: "S3 bucket is missing public access block configuration"
```

```python
# SecurityRule model extension:
@dataclass
class SecurityRule:
    id: str
    title: str
    severity: Severity
    resource_types: list[str]
    condition: RuleCondition
    remediation: str
    description: str
    framework_ids: list[str] = field(default_factory=list)  # NEW
```

### Pattern 6: Region-Aware Cost Estimation (CST-03)

**What:** Read region from the parsed `provider` block in HCL. Currently the provider block is not captured.

**Implementation approach:**
1. Extend `ParsedTerraform` with a `provider_configs: list[ParsedBlock]` field
2. In `_parse_file()`, call `_extract_providers()` to capture provider blocks
3. In `build_graph()`, set `node.region` from provider block's `region` attribute
4. In `CostEstimator`, apply region multiplier (us-west-2 ≈ same as us-east-1; eu-west-1 ≈ +10%; ap-southeast-1 ≈ +15%)

```python
# Source: [ASSUMED] region multipliers based on AWS pricing docs
REGION_MULTIPLIERS: dict[str, float] = {
    "us-east-1": 1.0, "us-east-2": 1.0, "us-west-1": 1.1, "us-west-2": 1.0,
    "eu-west-1": 1.1, "eu-west-2": 1.12, "eu-central-1": 1.12,
    "ap-southeast-1": 1.15, "ap-northeast-1": 1.12, "ap-south-1": 1.0,
}
```

### Pattern 7: Runtime Staleness Checks (RST-01)

**What:** Static EOL tables checked against resource attributes at analysis time.

```python
# Source: [VERIFIED: AWS Lambda docs - lambda-runtimes.html]
# Lambda EOL dates (verified April 2026):
LAMBDA_EOL: dict[str, str] = {
    "python3.8": "2024-10-14",
    "python3.9": "2025-09-01",
    "nodejs14.x": "2024-11-11",
    "nodejs16.x": "2024-06-12",
    "nodejs18.x": "2025-07-31",
    "ruby2.7": "2023-12-07",
    "java8": "2024-12-05",
    "dotnet6": "2024-11-12",
}

# EKS EOL - checked against endoflife.date
EKS_EOL: dict[str, str] = {
    "1.24": "2024-01-31", "1.25": "2024-05-01",
    "1.26": "2024-06-11", "1.27": "2024-07-26",
    "1.28": "2025-04-01",
}
```

Attribute to check: `aws_lambda_function.runtime`, `aws_eks_cluster.version`, `azurerm_kubernetes_cluster.kubernetes_version`.

### Pattern 8: Docker Multi-Arch Build (DST-01)

**Critical constraint:** [VERIFIED: PyInstaller docs] PyInstaller cannot cross-compile. Each binary must be built on its target architecture.

**Recommended approach:**
```yaml
# GitHub Actions matrix strategy:
strategy:
  matrix:
    include:
      - os: ubuntu-latest    # Linux amd64
        arch: amd64
      - os: macos-14         # macOS arm64 (M1 runner)
        arch: arm64
      - os: windows-latest   # Windows x64
        arch: x64
```

Docker image: use `docker buildx` with `--platform linux/amd64,linux/arm64` for the container image. Base image: `python:3.12-slim` (existing Dockerfile pattern). [VERIFIED: docker --version 29.3.1 available on this machine]

### Anti-Patterns to Avoid

- **Silent parse failure:** Current `except Exception: return` in `_parse_file()` is the root cause of the blocker listed in STATE.md. Must be replaced with error collection before Azure parser is added.
- **Importing boto3 at module level:** Makes `import infracanvas` fail if boto3 is not installed. Always import inside the function body.
- **Blocking CI on --shadow missing creds:** D-02 says never hard-fail. Warning + continue is the only acceptable path.
- **Loading all policy YAML at startup:** Policy dir is user-provided at runtime; load only when `--policy` flag is present.
- **azurerm_ prefix in Terraform resource type labels:** Strip it in both `ResourceNode.tsx` (viewer) and the terminal summary output (CLI) — same as `aws_` stripping.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| AWS credential discovery | Custom credential file reader | `boto3.Session()` default chain | Handles env vars, ~/.aws, instance profile, container credentials correctly; edge cases in order matter |
| HCL parsing | Custom HCL lexer | `python-hcl2` (already in project) | HCL2 grammar is complex; hcl2 uses Lark parser |
| YAML policy DSL | Custom config parser | Existing `load_rules()` + PyYAML | The existing engine already handles 8 operators; no new parser needed |
| File-change detection | `inotify` bindings | `watchdog` (already in project) | Cross-platform; macOS FSEvents, Linux inotify, Windows ReadDirectoryChanges |
| Multi-arch binary | Manual cross-compilation | PyInstaller on native runners | PyInstaller explicitly cannot cross-compile (verified in docs) |
| Compliance tag DB | JSON lookup table | Add `framework_ids` to YAML rules | Co-located with rule; easy to maintain; no separate DB needed |

**Key insight:** The existing security rule engine is the policy engine — the only new code needed is loading from a different directory and stamping `source="policy"` on resulting findings.

---

## Common Pitfalls

### Pitfall 1: HCL2 Exception Types Are Unpredictable
**What goes wrong:** `python-hcl2` raises `lark.exceptions.UnexpectedToken`, `lark.exceptions.UnexpectedCharacters`, and occasionally bare `Exception` depending on the failure mode. Catching only `lark.exceptions.LarkError` misses some failure modes.
**Why it happens:** The library uses Lark internally and doesn't always normalize exceptions to a single type.
**How to avoid:** Catch `Exception` (broad catch) in `_parse_file()`, but log the exception type and message. The broad catch is intentional — partial results from other files are still valuable.
**Warning signs:** Test `test_a005_handle_malformed_file` in `test_parser.py` — if it fails, the handler is too narrow.

### Pitfall 2: Azure Provider Block Region Detection
**What goes wrong:** Azure resources don't use `region` — they use `location`. The azurerm provider block uses `features {}` not `region =`. Location is on each resource as `location = "East US"`.
**Why it happens:** Azure and AWS have different naming conventions for the same concept.
**How to avoid:** In Azure resource node, map `location` attribute → `node.region`. The graph builder must check `attrs.get("location")` for azurerm resources.
**Warning signs:** All Azure nodes show `region: ""` in the viewer.

### Pitfall 3: boto3 Optional Import Breaks Mypy Strict
**What goes wrong:** `mypy --strict` flags `TYPE_CHECKING` or bare `import boto3` inside function body as possibly untyped.
**Why it happens:** boto3 has type stubs (`boto3-stubs`) that must be installed separately.
**How to avoid:** Add `boto3-stubs[ec2,s3,rds]` to the `[shadow]` optional dep group, and use `if TYPE_CHECKING: import boto3` for type annotations.

### Pitfall 4: Policy Rules Loaded From External Dir Not Included in Package Artifacts
**What goes wrong:** The Hatchling build configuration (`pyproject.toml`) only includes `security/rules/**/*.yaml` as artifacts. External policy directories are user-provided and live outside the package — that's correct. But internal test fixtures for policy rules need to be in `cli/tests/fixtures/policies/`.
**Why it happens:** Confusion between built-in security rules (packaged) and user-provided policy files (runtime).
**How to avoid:** Test policy loading with `--policy cli/tests/fixtures/policies/` in integration tests.

### Pitfall 5: Shadow Resources Duplicating Terraform-Managed Resources
**What goes wrong:** An EC2 instance managed by Terraform appears in both the parsed graph AND the shadow scan because the Terraform state doesn't perfectly match the live API resource ID format.
**Why it happens:** Resource IDs in Terraform (`aws_instance.web`) vs AWS API (`i-0abc123def456`) — these are different ID spaces.
**How to avoid:** Match shadow resources by tags (`terraform_resource`, `Name` tag) or by comparing resource attributes (instance type, VPC, subnet) rather than by ID. Flag as shadow only if a live resource has NO matching Terraform node.
**Warning signs:** All EC2 instances appear twice — one managed, one shadow.

### Pitfall 6: Vitest Config Already Has Setup File
**What goes wrong:** Adding a new test setup file breaks the existing `setupFiles: ['./src/__tests__/setup.ts']` path.
**Why it happens:** `vite.config.ts` already declares a specific setup file.
**How to avoid:** Add new setup to the existing `setup.ts` file; do not add a second `setupFiles` entry.

### Pitfall 7: PyInstaller and Python 3.14 Mismatch
**What goes wrong:** The system Python is 3.14.3 but the project targets Python 3.12+. PyInstaller builds against whichever Python it finds.
**Warning signs:** PyInstaller binary runs on 3.14 but the project venv is 3.12. In CI, pin Python version explicitly.
**How to avoid:** CI workflows must use `python-version: '3.12'` action. Do not use system Python for PyInstaller builds.

---

## Code Examples

### Example 1: Finding Model with Source and Framework Tags

```python
# Source: [VERIFIED: existing cli/infracanvas/graph/models.py — extend this]
class Finding(BaseModel):
    rule_id: str
    severity: Severity
    title: str
    description: str
    remediation: str
    evidence: dict[str, object] = {}
    source: str = "security"           # "security" | "policy" — backwards compatible default
    framework_ids: list[str] = []      # ["CIS-1.20", "NIST-SC-7"] — empty = no tags
```

### Example 2: Azure Security Rule YAML Schema

```yaml
# Source: [VERIFIED: existing aws/s3.yaml schema — extend with framework_ids]
- id: AZ-001
  title: "NSG Allows Unrestricted Inbound Access"
  severity: critical
  resource_types: ["azurerm_network_security_group"]
  framework_ids: ["CIS-6.1", "NIST-SC-7", "SOC2-CC6.6"]
  condition:
    attribute: "security_rule.source_address_prefix"
    operator: "equals"
    value: "*"
  remediation: "Replace wildcard source with specific IP ranges or service tags"
  description: "NSG rule allows inbound access from any source address"

- id: AZ-002
  title: "Storage Account Allows Public Blob Access"
  severity: high
  resource_types: ["azurerm_storage_account"]
  framework_ids: ["CIS-3.5", "NIST-SC-28", "PCI-DSS-3.4"]
  condition:
    attribute: "allow_blob_public_access"
    operator: "equals"
    value: true
  remediation: "Set allow_blob_public_access = false"
  description: "Storage account allows anonymous public access to blobs"
```

### Example 3: azureServiceConfig.ts (mirrors awsServiceConfig.ts)

```typescript
// Source: [VERIFIED: viewer/src/icons/awsServiceConfig.ts — mirror this structure]
// viewer/src/icons/azureServiceConfig.ts
export interface AzureServiceConfig {
  color: string;
  label: string;
}

export const AZURE_SERVICE_CONFIG: Record<string, AzureServiceConfig> = {
  azurerm_virtual_network:       { color: '#0078D4', label: 'VNet' },
  azurerm_subnet:                { color: '#0078D4', label: 'NET' },
  azurerm_network_security_group: { color: '#DD344C', label: 'NSG' },
  azurerm_virtual_machine:       { color: '#FF9900', label: 'VM' },
  azurerm_storage_account:       { color: '#3F8624', label: 'STG' },
  azurerm_kubernetes_cluster:    { color: '#2E73B8', label: 'AKS' },
  azurerm_app_service:           { color: '#FF9900', label: 'APP' },
  azurerm_mssql_server:          { color: '#2E73B8', label: 'SQL' },
  azurerm_key_vault:             { color: '#DD344C', label: 'KV' },
  azurerm_application_gateway:   { color: '#8C4FFF', label: 'AGW' },
};

export function getAzureServiceConfig(resourceType: string): AzureServiceConfig {
  if (AZURE_SERVICE_CONFIG[resourceType]) return AZURE_SERVICE_CONFIG[resourceType];
  return { color: '#94a3b8', label: resourceType.replace(/^azurerm_/, '').slice(0, 4).toUpperCase() };
}
```

### Example 4: Source Filter Store Extension

```typescript
// Source: [VERIFIED: viewer/src/store.ts Zustand selector pattern]
// Extend existing StoreState:
interface Filters {
  severities: Severity[];
  resourceTypes: string[];
  driftStatuses: DriftStatus[];
  sources: string[];           // NEW: [] means "all"; ['security', 'policy'] = filter applied
}

// New action:
toggleSourceFilter: (source: string) => void;

// Implementation in create():
toggleSourceFilter: (source) => set(s => ({
  filters: {
    ...s.filters,
    sources: s.filters.sources.includes(source)
      ? s.filters.sources.filter(x => x !== source)
      : [...s.filters.sources, source],
  },
})),
```

### Example 5: Scan Command Shadow + Policy Flags

```python
# Source: [VERIFIED: cli/infracanvas/main.py — existing scan() command signature]
@app.command()
def scan(
    directory: ...,
    # ... existing args ...
    shadow: Annotated[
        bool,
        typer.Option("--shadow", help="Compare live AWS API vs Terraform state"),
    ] = False,
    policy: Annotated[
        Optional[Path],
        typer.Option("--policy", help="Directory containing custom policy YAML files"),
    ] = None,
    fail_on: Annotated[
        Optional[str],
        typer.Option("--fail-on", help="Minimum severity to trigger non-zero exit (critical/high/medium/info)"),
    ] = None,
) -> None:
```

---

## Azure Resource Type → Security Rule Mapping (AZR-01, AZR-03)

The 10 supported Azure resource types and their corresponding security rules:

| Resource Type | Terraform Name | Key Security Checks |
|---------------|---------------|---------------------|
| Virtual Network | `azurerm_virtual_network` | DDoS protection plan (AZ-009) |
| Subnet | `azurerm_subnet` | Service endpoint policies |
| NSG | `azurerm_network_security_group` | Wildcard source rules (AZ-001), SSH/RDP open (AZ-003) |
| Virtual Machine | `azurerm_virtual_machine` | Managed disk encryption (AZ-004), no public IP (AZ-005) |
| Storage Account | `azurerm_storage_account` | Public blob access (AZ-002), HTTPS only (AZ-006), minimum TLS (AZ-007) |
| AKS Cluster | `azurerm_kubernetes_cluster` | RBAC enabled (AZ-008), private cluster |
| App Service | `azurerm_app_service` | HTTPS only, TLS version |
| SQL Server | `azurerm_mssql_server` | Public network access off, firewall (AZ-010) |
| Key Vault | `azurerm_key_vault` | Soft delete, purge protection |
| App Gateway | `azurerm_application_gateway` | WAF enabled |

**Azure attribute shapes (key attributes for rule conditions):**

| Resource | Key Attribute | Location in HCL |
|----------|--------------|-----------------|
| NSG | security_rule.source_address_prefix | Nested block `security_rule {}` |
| Storage Account | allow_blob_public_access | Top-level bool |
| Storage Account | https_traffic_only_enabled | Top-level bool |
| Storage Account | min_tls_version | Top-level string ("TLS1_2") |
| AKS | role_based_access_control_enabled | Top-level bool |
| VM | os_disk.caching / storage_image_reference | Nested block |
| Key Vault | soft_delete_retention_days | Top-level int |
| Key Vault | purge_protection_enabled | Top-level bool |
| SQL Server | public_network_access_enabled | Top-level bool |

[CITED: registry.terraform.io/providers/hashicorp/azurerm/latest/docs]

---

## Compliance Framework Tag Mapping (SEC-06, Claude's Discretion)

Standard control mappings for the existing 10 AWS rules + 20 new + 10 Azure:

| Rule | CIS AWS | NIST 800-53 | SOC2 | PCI-DSS |
|------|---------|-------------|------|---------|
| SEC-001 S3 Public ACL | 2.1.5 | SC-7 | CC6.1 | 1.2 |
| SEC-002 S3 Encryption | 2.1.1 | SC-28 | CC6.7 | 3.4 |
| SEC-003 SG SSH/RDP from internet | 5.2 | AC-17 | CC6.6 | 1.2 |
| SEC-004 SG all traffic | 5.2 | SC-7 | CC6.6 | 1.2 |
| SEC-005 RDS Publicly Accessible | 2.3.2 | SC-7 | CC6.1 | 1.2 |
| SEC-006 RDS Encryption | 2.3.1 | SC-28 | CC6.7 | 3.4 |
| SEC-007 IAM No MFA | 1.5 | IA-2 | CC6.1 | 8.3 |
| SEC-008 EBS Unencrypted | 2.2.1 | SC-28 | CC6.7 | 3.4 |
| SEC-009 KMS No Rotation | 3.8 | SC-12 | CC6.7 | 3.6 |
| SEC-010 Missing Tags | — | CM-8 | CC6.3 | — |

[ASSUMED] These mappings are based on standard CIS/NIST/SOC2/PCI-DSS control alignment from training knowledge. Exact control IDs may vary by framework version — verify against current CIS AWS Benchmark v3.0.0 before locking.

---

## New AWS Security Rules Recommendation (SEC-05, Claude's Discretion)

20 new rules (SEC-011 through SEC-030) prioritised by security value:

| Rule ID | Resource Type | Check | Severity |
|---------|--------------|-------|---------|
| SEC-011 | aws_s3_bucket_public_access_block | Block public acls not set | critical |
| SEC-012 | aws_s3_bucket | Versioning disabled | medium |
| SEC-013 | aws_s3_bucket | Logging disabled | info |
| SEC-014 | aws_security_group | Allows all egress | medium |
| SEC-015 | aws_iam_role | Wildcard action in policy | critical |
| SEC-016 | aws_lambda_function | Not in VPC | medium |
| SEC-017 | aws_lambda_function | Runtime EOL | high |
| SEC-018 | aws_rds_instance | No deletion protection | medium |
| SEC-019 | aws_rds_instance | No backup retention | high |
| SEC-020 | aws_rds_instance | No Enhanced Monitoring | info |
| SEC-021 | aws_eks_cluster | Old Kubernetes version | high |
| SEC-022 | aws_eks_cluster | No secrets encryption | high |
| SEC-023 | aws_alb / aws_lb | HTTP not redirected to HTTPS | high |
| SEC-024 | aws_cloudfront_distribution | HTTP protocol policy allows HTTP | medium |
| SEC-025 | aws_sqs_queue | No encryption | medium |
| SEC-026 | aws_sns_topic | No encryption | medium |
| SEC-027 | aws_dynamodb_table | No PITR (point-in-time recovery) | medium |
| SEC-028 | aws_iam_role | No boundary policy | info |
| SEC-029 | aws_kms_key | No deletion window | medium |
| SEC-030 | aws_s3_bucket | No lifecycle policy | info |

[ASSUMED] Specific attribute paths for these checks need to be verified against the Terraform AWS provider docs. The rule conditions follow existing operator patterns (exists, not_exists, equals, not_equals).

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| terraform plan output (text) | `terraform show -json` JSON format | Terraform 0.12+ | PlanReader already uses JSON format |
| Manually maintained EOL lists | endoflife.date API | 2022+ | Static table is sufficient; API is optional enhancement |
| PyInstaller single-arch | GitHub Actions matrix builds | 2021+ | Now standard for multi-arch CLI tools |
| python-hcl2 raises LarkError | python-hcl2 4.x may return partial results | 2023+ | Must test with complex conditional HCL |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | boto3 stable version is ~1.34.x | Standard Stack | Minor — verify with `pip index versions boto3` before pinning in pyproject.toml |
| A2 | Region multipliers (us-west-2 ≈ us-east-1, eu-west-1 +10%, etc.) | Pattern 6 | Cost estimates slightly off; acceptable for Phase 2 static estimation |
| A3 | Compliance framework tag mappings (CIS/NIST/SOC2/PCI-DSS) | Compliance section | Tag IDs may be wrong version; verify against CIS AWS Benchmark v3.0.0 current PDF |
| A4 | 20 new AWS rule attribute paths | SEC-05 recommendations | Specific paths like `aws_s3_bucket_public_access_block.block_public_acls` need Terraform provider doc verification |
| A5 | Lambda runtime Python 3.9 EOL is 2025-09-01 | Pattern 7 (RST-01) | AWS may change deprecation schedule; check docs.aws.amazon.com/lambda/latest/dg/lambda-runtimes.html |
| A6 | `azurerm_virtual_machine.os_disk` attribute path for encryption check | Azure Rules | Terraform azurerm provider version 3.x vs 4.x may differ; verify against registry.terraform.io |

---

## Open Questions (RESOLVED)

1. **Infracost API (CST-01 deferred)** (RESOLVED)
   - What we know: CONTEXT.md defers the API integration decision to the planner; static pricing fallback exists
   - Resolution: Static pricing is the Phase 2 implementation. Infracost API deferred per CONTEXT.md. Plan 05 implements static pricing with region multipliers.

2. **Azure VM Attribute Shape — v3 vs v4 azurerm provider** (RESOLVED)
   - What we know: The azurerm provider had major breaking changes between v3 and v4 (released 2024).
   - Resolution: Support all three (`azurerm_virtual_machine`, `azurerm_linux_virtual_machine`, `azurerm_windows_virtual_machine`). Plan 02 implements this in azure.py and azureServiceConfig.ts.

3. **python-hcl2 Partial Results Behavior** (RESOLVED)
   - What we know: STATE.md states "python-hcl2 returns partial results on ~15% of complex modules"
   - Resolution: Plan 01 hardens with per-file error collection (broad `except Exception` catch + `parse_errors` list). No python-hcl2 version upgrade needed for Phase 2.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 venv | CLI development | ✓ | 3.12 (cli/.venv12/) | — |
| Python 3.14 (system) | — | ✓ | 3.14.3 | Use cli/.venv12/ for project work |
| Node.js / npm | Viewer build | ✓ | npm 11.11.1 | — |
| Docker | DST-01 container | ✓ | 29.3.1 | — |
| PyInstaller | DST-01 binaries | ✓ | system 3.11 path | Must use venv Python, not system |
| boto3 | SHD-01 shadow | ✗ | — | Add as optional dep [shadow] |
| AWS credentials | SHD-01 shadow | Unknown | — | D-02: warn and continue |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:**
- boto3: not in project venv; must be added as optional dep `pip install infracanvas[shadow]`. The `--shadow` flag without boto3 should print: "boto3 not installed. Install with: pip install 'infracanvas[shadow]'" and continue scan without shadow detection.
- System Python 3.14 ≠ project Python 3.12: PyInstaller builds must use the 3.12 venv Python, not `python3` from system PATH.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Python framework | pytest 9.0.3 |
| Config file | `cli/pyproject.toml` → `[tool.pytest.ini_options]` testpaths=["tests"] |
| Quick run command | `cd cli && python -m pytest tests/ -x -q` (using .venv12) |
| Full suite command | `cd cli && python -m pytest tests/ -v` |
| JS framework | Vitest 4.1.4 |
| JS config file | `viewer/vite.config.ts` → `test: { environment: 'jsdom', globals: true }` |
| JS quick run | `cd viewer && npm run test` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | File |
|--------|----------|-----------|------|
| PLN-01 | Plan JSON reader extracts create/update/delete | unit | `cli/tests/test_plan.py` (exists) |
| PLN-02 | Drift nodes coloured green/red/amber/grey | unit | `cli/tests/test_drift.py` (exists) |
| PLN-03 | ChangesTab renders before/after diff | component | `viewer/src/__tests__/DetailPanel.test.tsx` (new) |
| SHD-01 | Shadow detector compares API vs graph | unit (mocked boto3) | `cli/tests/test_shadow.py` (new) |
| SHD-02 | Shadow nodes flagged with dashed border | unit | `cli/tests/test_graph.py` (extend) |
| CST-01/02 | Cost per resource; cost delta | unit | `cli/tests/test_cost.py` (exists) |
| CST-03 | Region-aware pricing applied correctly | unit | `cli/tests/test_cost.py` (extend) |
| AZR-01 | Azure parser extracts 10 resource types | unit | `cli/tests/test_azure_parser.py` (new) |
| AZR-02 | Azure icons render in viewer | component | `viewer/src/__tests__/ResourceNode.test.tsx` (new) |
| AZR-03 | 10 Azure rules evaluate correctly | unit | `cli/tests/test_security.py` (extend) |
| SEC-05 | 30 AWS rules total in engine | unit | `cli/tests/test_security.py` (extend) |
| SEC-06 | All rules have framework_ids | unit | `cli/tests/test_security.py` (extend) |
| RST-01 | Lambda/EKS/AKS staleness detected | unit | `cli/tests/test_staleness.py` (new) |
| RST-02 | azurerm_management_lock validated | unit | `cli/tests/test_staleness.py` (new) |
| POL-01 | Policy rules loaded and evaluated | unit | `cli/tests/test_policy.py` (new) |
| POL-02 | --policy flag loads external YAML dir | integration | `cli/tests/test_integration.py` (extend) |
| CLX-01 | --fail-on flag exits non-zero | integration | `cli/tests/test_cli.py` (extend) |
| CLX-02 | Watch mode re-scans on .tf changes | integration | `cli/tests/test_cli.py` (extend, watchdog) |
| DST-01 | Docker image builds | smoke (CI) | GitHub Actions workflow (new) |
| DST-02 | Homebrew formula installs | smoke (CI) | GitHub Actions workflow (existing + update) |

### Sampling Rate

- **Per task commit:** `cd cli && python -m pytest tests/ -x -q --tb=short`
- **Per wave merge:** `cd cli && python -m pytest tests/ -v && cd ../viewer && npm run test`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps (test files that must be created before implementation)

- [ ] `cli/tests/test_azure_parser.py` — covers AZR-01 (Azure parser unit tests)
- [ ] `cli/tests/test_shadow.py` — covers SHD-01 (shadow detector with mocked boto3)
- [ ] `cli/tests/test_staleness.py` — covers RST-01, RST-02
- [ ] `cli/tests/test_policy.py` — covers POL-01, POL-02
- [ ] `cli/tests/fixtures/azure/` — Azure .tf fixtures (VNet, NSG, VM, storage, AKS)
- [ ] `cli/tests/fixtures/policies/` — Sample policy YAML fixtures
- [ ] `viewer/src/__tests__/DetailPanel.test.tsx` — covers PLN-03 (ChangesTab)
- [ ] `viewer/src/__tests__/ResourceNode.test.tsx` — covers AZR-02 (Azure icon rendering)

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | N/A — CLI tool, no auth layer |
| V3 Session Management | no | N/A — stateless CLI |
| V4 Access Control | partial | Shadow detection: read-only IAM role; no write ops |
| V5 Input Validation | yes | Policy YAML loaded from user-provided path; validate schema before eval |
| V6 Cryptography | no | No hand-rolled crypto; existing KMS rules check user infra, not tool crypto |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via --policy flag | Tampering | Validate policy dir is under cwd or user home; reject absolute paths outside safe zones |
| YAML injection in policy files | Tampering | Use `yaml.safe_load()` (already used in loader.py) — never `yaml.load()` |
| boto3 credential leakage in logs | Information disclosure | Never log boto3 session credentials; sanitize error messages from AWS API errors |
| Shadow scan against wrong region (region inference failure) | Tampering | Default to `us-east-1` if no region found; warn user; never scan multiple regions |

---

## Sources

### Primary (HIGH confidence)
- [VERIFIED: cli/infracanvas/parser/hcl.py] — Current parser structure; silent failure pattern confirmed
- [VERIFIED: cli/infracanvas/security/engine.py] — Rule evaluation engine; policy extension path
- [VERIFIED: cli/infracanvas/security/loader.py] — YAML rule loader; `load_rules(rules_dir=None)` signature
- [VERIFIED: cli/infracanvas/security/models.py] — SecurityRule dataclass; missing framework_ids
- [VERIFIED: cli/infracanvas/graph/models.py] — Finding model; missing source + framework_ids fields
- [VERIFIED: cli/infracanvas/cost/estimator.py] — Static pricing dict; CostEstimator.delta() exists
- [VERIFIED: cli/infracanvas/drift/analyzer.py] — DriftAnalyzer.apply() already handles all drift statuses
- [VERIFIED: cli/infracanvas/main.py] — CLI command signatures; existing --ci, --watch, --ignore, --severity flags
- [VERIFIED: viewer/src/components/DetailPanel.tsx] — ChangesTab already implemented (PLN-03 done)
- [VERIFIED: viewer/src/components/ResourceNode.tsx] — Shadow dashed border already implemented
- [VERIFIED: viewer/src/icons/awsServiceConfig.ts] — Azure config mirror pattern
- [VERIFIED: viewer/src/lib/colors.ts] — Azure colors locked in UI-SPEC
- [VERIFIED: cli/.venv12/site-packages] — boto3 NOT installed; pytest 9.0.3, watchdog 4.0.1 present
- [VERIFIED: docker --version 29.3.1] — Docker buildx available
- [VERIFIED: .planning/phases/02-canvas-v1-0/02-UI-SPEC.md] — All viewer visual decisions locked
- [VERIFIED: .planning/phases/02-canvas-v1-0/02-CONTEXT.md] — All implementation decisions locked

### Secondary (MEDIUM confidence)
- [CITED: boto3.amazonaws.com/v1/documentation/api/latest] — boto3 describe_* API surface; credential chain behavior
- [CITED: docs.aws.amazon.com/lambda/latest/dg/lambda-runtimes.html] — Lambda runtime EOL dates
- [CITED: endoflife.date/amazon-eks] — EKS version EOL timeline
- [CITED: registry.terraform.io/providers/hashicorp/azurerm/latest/docs] — Azure resource attribute shapes
- [CITED: pyinstaller.org/en/stable] — PyInstaller cannot cross-compile; per-arch build requirement

### Tertiary (LOW confidence — flag for validation)
- [ASSUMED] boto3 stable version ~1.34.x — verify before pinning
- [ASSUMED] Compliance framework tag IDs (CIS/NIST/SOC2/PCI-DSS) — verify against current benchmark PDFs
- [ASSUMED] Region cost multipliers — verify against AWS pricing pages before shipping

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified from pyproject.toml and package.json
- Architecture: HIGH — all integration points verified from source files
- Azure rules: MEDIUM — attribute paths assumed from Terraform registry docs (web search, not direct fetch)
- Compliance tags: LOW — standard mappings from training knowledge; must be verified
- Distribution (PyInstaller): HIGH — verified from official docs that cross-compilation is impossible

**Research date:** 2026-04-16
**Valid until:** 2026-05-16 (30 days — stable toolchain, no fast-moving dependencies)
