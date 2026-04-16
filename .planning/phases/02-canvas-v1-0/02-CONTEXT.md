# Phase 2: Canvas v1.0 - Context

**Gathered:** 2026-04-16
**Status:** Ready for planning

<domain>
## Phase Boundary

The CLI handles Azure alongside AWS, detects drift and shadow infrastructure, enforces custom policies, and ships multi-region cost estimation — with the HCL parser hardened against silent failures first.

This phase does NOT include: SaaS dashboard, team collaboration, Go DC Agent, network path tracing, compliance reports (SOC2/HIPAA), or SSO.

</domain>

<decisions>
## Implementation Decisions

### Shadow Infrastructure Detection (SHD-01, SHD-02)

- **D-01:** Opt-in via `--shadow` flag: `infracanvas scan ./tf --shadow`. Auto-detects AWS credentials in standard order (env vars → ~/.aws/credentials → instance profile). No explicit `--region` required alongside the flag.
- **D-02:** If `--shadow` is passed but no AWS credentials are found: print a yellow warning ("--shadow requires AWS credentials. Skipping shadow scan.") and continue the rest of the scan normally. Never hard-fail on missing creds.
- **D-03:** Shadow resource scope (which AWS types to compare): **Claude's discretion** — planner picks the most feasible set based on read-only IAM surface area and highest drift-detection signal.
- **D-04:** Shadow resources displayed with **dashed border + "Shadow" badge** (grey) in the diagram, consistent with SHD-02 spec. Estimated cost shown in DetailPanel.
- **D-05:** Region: infer from `.tf` files (provider block or resource attributes). Scan only that region. No multi-region sweep by default.

### Azure Integration (AZR-01, AZR-02, AZR-03)

- **D-06:** **Auto-detect Azure .tf files** — `infracanvas scan ./tf` detects `azurerm` provider resources automatically. No `--provider azure` flag needed. Same UX as AWS scanning today.
- **D-07:** Azure credentials via **ARM_* env vars only**: `ARM_CLIENT_ID`, `ARM_CLIENT_SECRET`, `ARM_TENANT_ID`, `ARM_SUBSCRIPTION_ID`. Same pattern as Terraform. No Azure CLI fallback in Phase 2.
- **D-08:** Mixed AWS+Azure repos produce a **combined diagram**: AWS resources in AWS-styled groups (VPC), Azure resources in Azure-styled groups (VNet), edges can cross cloud boundaries (e.g., VPN peering).

### Custom Policy Engine (POL-01, POL-02)

- **D-09:** Policy violations surface as **findings in the diagram** (tagged with a "POLICY" source indicator and YAML-declared severity) AND cause non-zero exit code in CI. Same findings pipeline as security rules — one HTML report with all findings combined.
- **D-10:** **Always blocks in CI** when policy violations exist, using the existing CI auto-detection from Phase 1 (D-11: CI env vars). No extra `--fail-on-policy` flag needed.
- **D-11:** **Severity from policy YAML** — each policy rule declares its own severity (`critical` / `high` / `medium` / `info`). Users tune what's a hard block vs a warning at the rule level.
- **D-12:** Policy runs as part of the **scan pipeline** — `infracanvas scan --policy ./policies`. Not a separate command. One command, one report.

### Drift Diff UX (PLN-02, PLN-03)

- **D-13:** Before/after attribute diff appears in the **DetailPanel** as a "Changes" tab alongside "Findings". Layout: tabs at the top of the panel (`Findings | Changes`). Diff shows as a simple before/after table (- old value, + new value).
- **D-14:** **Changed attributes only** in the diff — not all resource attributes. Keeps the diff focused and readable for large resources.
- **D-15:** Drift **node border colour**: green border = added, red border = destroyed, amber border = changed, grey border = no-op/unknown. Node body and icon stay normal — border only.
- **D-16:** `infracanvas plan` **auto-opens browser** same as `scan` (Phase 1 D-10). Saves `infracanvas-plan.html` in the current directory and opens it. CI detection skips browser open.

### Carrying Forward from Phase 1

- Free-gate blur on finding title/description/remediation (D-01 Phase 1) applies to all new findings (Azure + Policy + shadow infra)
- Upgrade CTA links to `infracanvas.dev` founding member $49/mo page (D-02 Phase 1)
- Generic node rendering for unsupported resource types (D-06 Phase 1) — applies to Azure types not in the supported 10
- CI auto-detection (D-11 Phase 1): `CI=true`, `GITHUB_ACTIONS`, etc. → skip browser open, print file path

### Claude's Discretion

- Which AWS resource types to include in shadow infra detection scope (guided by: read-only IAM surface, drift-signal value, implementation complexity)
- Exact 20 new AWS security rules (SEC-011 through SEC-030) — write rules with highest security value across S3, IAM, RDS, EC2, KMS, Lambda, ALB, EKS
- Compliance framework tag mapping (CIS, NIST, SOC2, PCI-DSS) for all 40 rules — use standard control mappings
- Azure icon sources (prefer official Microsoft Azure icon set or reasonable SVG equivalents)
- CI flag design for CLX-01 (`--ci`, `--fail-on`, `--quiet`, `--ignore`, `--severity`) — plan sensible defaults
- Watch mode debounce timing (CLX-02)
- Docker base image and multi-arch build configuration (DST-01)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Context
- `.planning/PROJECT.md` — Product vision, constraints, solo-founder budget, target personas, pricing tiers
- `.planning/REQUIREMENTS.md` §Canvas v1.0 — PLN-01 through DST-02 acceptance criteria (all Phase 2 requirements)
- `.planning/ROADMAP.md` §Phase 2 — Success criteria (5 items), dependency on Phase 1

### Phase 1 Context (prior decisions that carry forward)
- `.planning/phases/01-canvas-mvp/01-CONTEXT.md` — Free-gate blur (D-01), upgrade CTA (D-02), generic node (D-06), CI detection (D-11), browser-open behaviour (D-10)

### Existing Codebase — Key Integration Points
- `cli/infracanvas/main.py` — Typer CLI; scan/score/plan/export commands; where `--shadow` and `--policy` flags land
- `cli/infracanvas/parser/hcl.py` — HCL parser (to harden for silent failures)
- `cli/infracanvas/parser/plan.py` — Terraform plan JSON reader (PLN-01 extends this)
- `cli/infracanvas/drift/analyzer.py` — Drift annotator (PLN-02 extends this)
- `cli/infracanvas/security/engine.py` — Rule evaluation engine (policy rules plug in here)
- `cli/infracanvas/security/rules/aws/` — 5 YAML rule files with 10 existing rules (SEC-001 through SEC-010); extend to 30
- `cli/infracanvas/cost/estimator.py` — Static cost estimator (us-east-1); multi-region logic (CST-03) extends this
- `viewer/src/components/DetailPanel.tsx` — Where "Changes" tab (D-13) gets added
- `viewer/src/store.ts` — Zustand store; drift status and shadow flag state live here

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `cli/infracanvas/security/engine.py` — Policy rules can be evaluated with the same engine (YAML conditions, resource type matching)
- `cli/infracanvas/drift/analyzer.py` — `DriftAnalyzer.apply()` already handles added/changed/destroyed; D-15 border colours map to existing `DriftStatus` enum
- `cli/infracanvas/cost/estimator.py` — Static pricing dict exists; multi-region extension needs region detection from provider block
- `viewer/src/components/DetailPanel.tsx` — Already renders findings list; "Changes" tab is an additive panel section
- `viewer/src/components/DiagramCanvas.tsx` — Node rendering; border colour for drift status is a style extension
- `cli/infracanvas/graph/models.py` — `ResourceNode` already has `drift`, `drift_changes`, `cost` fields; shadow and policy fields need to be added

### Established Patterns
- YAML-driven security rules (`id`, `title`, `severity`, `resource_types`, `condition`, `remediation`) — policy rules should follow the same schema with a `source: policy` field added
- Single-file HTML export via `vite-plugin-singlefile` — plan diagram (`infracanvas-plan.html`) follows the same export pattern
- Data injection via `window.__INFRACANVAS_DATA__` — shadow and policy data injected into same `ResourceGraph` object
- Zustand store with selector pattern — drift status and shadow badge state added as node-level data, not store-level flags

### Integration Points
- `cli/infracanvas/main.py` `scan` command → `--shadow` flag triggers AWS API comparison after graph build
- `cli/infracanvas/main.py` `scan` command → `--policy` flag loads additional YAML rule files and runs through existing rule engine
- `cli/infracanvas/parser/` → new `azure.py` module follows `hcl.py` structure for azurerm provider resource extraction
- `viewer/src/components/DetailPanel.tsx` → tabs component needed (Findings | Changes) — no existing tab component in `viewer/src/components/ui/`

</code_context>

<specifics>
## Specific Ideas

- DetailPanel diff mockup confirmed: tabs at top (`Findings | Changes`), diff table shows `- old value` / `+ new value` per changed attribute. Clean, familiar git-diff-style presentation.
- Shadow badge: grey "Shadow" badge, dashed border — visually distinct from severity badges (Critical/High/Medium) but same badge component
- Policy finding source field: findings tagged with `source: "policy"` to distinguish from security rule findings in the UI — allows filtering by source in the FilterPanel
- `infracanvas scan --policy ./policies` is the primary UX — engineers point at a policies directory containing multiple YAML files (one per rule or grouped by domain)

</specifics>

<deferred>
## Deferred Ideas

- Infracost pricing API integration (CST-01 mentions it): static pricing fallback is sufficient for Phase 2 unless Infracost API key UX can be made zero-config — defer API integration decision to planner
- Azure CLI auth fallback (`az login` credentials) — ARM_* env vars only in Phase 2; Azure CLI support is a Phase 4+ enhancement
- Cross-cloud cost comparison (AWS vs Azure equivalent resource costs) — interesting but Phase 4 CostLens scope
- Multi-region parallel scanning — region sweep beyond inferred region is a Phase 4 SaaS feature
- Policy engine v2 (OPA/Rego) — Phase 5 Enterprise scope

</deferred>

---

*Phase: 02-canvas-v1-0*
*Context gathered: 2026-04-16*
