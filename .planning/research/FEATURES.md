# Feature Research

**Domain:** IaC Visualization and Security SaaS (Terraform-focused)
**Researched:** 2026-04-15
**Confidence:** MEDIUM — based on training knowledge of competitors (Terraform Cloud, Spacelift, Firefly, env0, Infracost Cloud, Bridgecrew/Prisma Cloud, Brainboard, Terravision). Web search unavailable; flag for validation before roadmap lock.

---

## Competitive Landscape Context

Direct and adjacent competitors inform what's expected:

- **Terraform Cloud / HCP Terraform** — run history, state locking, team access, policy enforcement (Sentinel/OPA). The market reference point for what "IaC SaaS" means.
- **Spacelift** — policy-as-code, approval workflows, drift detection, run history. Strong on GitOps/CI integration.
- **env0** — cost visibility, team collaboration, environment lifecycle management, self-service portals.
- **Firefly** — cloud asset inventory + IaC drift detection, read-only posture focus. No execution.
- **Brainboard** — Terraform diagram editor with direct code generation. Visual-first approach.
- **Infracost Cloud** — cost estimation SaaS with PR comments, policy rules, team dashboards.
- **Bridgecrew (now Prisma Cloud)** — CSPM + IaC scanning, compliance frameworks, PR gate.
- **Terravision / Blast Radius** — open-source diagram generators, no SaaS. Proof users want visualization.

InfraCanvas occupies a distinct niche: **read-only analysis + visualization** (not execution) combined with **security posture scoring** and **cost attribution**. This informs what table stakes look like — users aren't expecting Terraform execution, they're expecting the analysis/sharing layer to be solid.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete or unprofessional.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Email/password + OAuth login (GitHub, Google) | Every SaaS has auth; CLI-push workflow requires account | LOW | Clerk or Supabase Auth handle this; must include GitHub OAuth given the target audience |
| Project/organization dashboard | Users have multiple Terraform repos; need a home screen | LOW | List of projects, last scan date, aggregate score |
| Scan history with timestamps | Without history, it's just a file viewer not a SaaS | MEDIUM | Store `ResourceGraph` JSON as artifacts in Supabase Storage; render timeline |
| Persistent shareable diagram links | Core stated feature; also the primary viral loop | MEDIUM | Public/private toggle, optional password; UUID slug URLs |
| Per-scan security score visible in dashboard | Score card is already built in CLI; surfacing it in SaaS is expected | LOW | Aggregate display; trend arrow (better/worse than last scan) |
| CLI authentication (`infracanvas login`) | Without this, users can't push scans from CI | LOW | OAuth device flow or API key; store token in `~/.infracanvas/credentials` |
| CLI `push` command | The bridge between CLI and SaaS; without it there's no SaaS | LOW | Upload JSON artifact, create scan record, return scan URL |
| Team member invitations | $199/mo Team tier meaningless without invite+accept flow | MEDIUM | Email invite, role assignment (admin/member); Supabase Row Level Security enforces access |
| Basic billing/subscription management | Pro/Team upgrade, cancel, billing portal | MEDIUM | Stripe Billing + Customer Portal; webhook for subscription state changes |
| Scan detail view (interactive diagram) | The core product — must work in browser, not just CLI | HIGH | Embed the existing ReactFlow viewer; adapt from single-file HTML to React component |

### Differentiators (Competitive Advantage)

Features that set InfraCanvas apart. Not required on day one but define the competitive moat.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Side-by-side scan comparison (diff view) | No competitor offers visual diff of two infra states; Terraform Cloud shows text diffs | HIGH | Compare two `ResourceGraph` snapshots; highlight added/removed/changed nodes visually |
| Security trend over time (score history chart) | Shows "are we getting more secure?" — security managers love this | MEDIUM | Store score per scan; render sparkline or trend chart per category (IAM, encryption, networking) |
| CI/CD webhook auto-scan on push | Closes the loop: every PR/push auto-generates a new scan without developer action | MEDIUM | Webhook endpoint receives push event, triggers backend scan job using stored repo config |
| Per-finding remediation guidance in SaaS UI | CLI already has remediation text; surfacing it prominently in SaaS + linking to AWS docs differentiates from pure-score tools | LOW | Already in `Finding.remediation`; render with copy-to-clipboard code blocks |
| Cost attribution by team/project over scans | Infracost Cloud does this for PR comments; InfraCanvas does it at diagram level with history | MEDIUM | Aggregate estimated monthly cost per project, trend over scans |
| Public scan gallery / "Show your infra" | Viral sharing loop — publicly shareable diagrams with security scores; differentiates from tools that hide everything | LOW | Index of public scans; opt-in; good for OSS GTM |
| Scan-level compliance summary (CIS, NIST references) | Security teams need to map findings to frameworks; competitors charge extra for this | HIGH | Requires tagging rules with framework identifiers; build on expanded 30-rule set |
| Webhook delivery log with retry | CI/CD integrations break; showing delivery status + retry builds trust | MEDIUM | Store webhook attempt log; show success/failure per delivery |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create operational complexity or pull focus from the core.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Terraform plan execution in SaaS | "Could you just run `terraform apply` for me?" | Requires state locking, blast-radius analysis, approval workflows, blast-radius rollback — months of work that Terraform Cloud/Spacelift already do better | Stay read-only; link to Terraform Cloud/Spacelift for execution |
| Real-time cloud sync (direct AWS API) | "Show me live resources without a Terraform file" | Requires AWS credentials stored in SaaS, IAM role management per customer, drift between cloud state and IaC — security liability and massive scope | Drift detection via `terraform plan` JSON is sufficient for v1 |
| GitHub PR review bot (auto-comment on PRs) | "Fail my PR if score drops" | Requires GitHub App installation, permissions review, per-org configuration, rate limiting — high support burden | CI/CD webhook + exit codes cover the use case without GitHub App complexity |
| Slack / Teams notifications | "Alert me when a new critical finding appears" | Low value relative to engineering cost; webhook + email covers it; each integration becomes a support surface | Email notification on scan completion with summary; revisit post-PMF |
| Custom policy engine (Rego/YAML user rules) | "I want to write my own security rules" | Policy authoring UX is a product in itself; Checkov/OPA already do this; support burden is high | Expand built-in rule set to 30; allow rule suppression via `.infracanvas.yml` |
| Self-hosted / on-prem option | Enterprise requirement for regulated industries | Requires packaging, versioning, customer infrastructure support, license management — not viable solo | SaaS-only for v1; note it as v2 roadmap for enterprise sales conversations |
| SSO / SAML | Enterprise requirement | Requires SAML IdP integration, session management, JIT provisioning — weeks of work | Defer; Clerk and Supabase Auth support SAML add-on when needed |
| Multi-cloud (Azure, GCP) | "We use both AWS and GCP" | Parser rewrite scope; different resource models, different security rule sets; triples the rule maintenance burden | AWS-only for v1; structured as clear future milestone |
| AI "fix my infra" suggestions | "Tell me how to fix all my findings with AI" | LLM costs at scale, prompt injection risk with user HCL, hallucinated Terraform code is dangerous | Deterministic remediation guidance (already in rules) is safer and cheaper |

---

## Feature Dependencies

```
[CLI login command]
    └──requires──> [Auth system (Clerk/Supabase)]
                       └──requires──> [User + session model in DB]

[CLI push command]
    └──requires──> [CLI login command]
    └──requires──> [Scan storage (Supabase Storage + DB record)]
                       └──requires──> [Project model in DB]

[Scan history timeline]
    └──requires──> [Scan storage]
    └──requires──> [Project dashboard]

[Shareable diagram links]
    └──requires──> [Scan storage]
    └──requires──> [ReactFlow viewer as SaaS component]

[Scan comparison (diff view)]
    └──requires──> [Scan history timeline]  (need >= 2 scans)
    └──requires──> [Scan storage]

[CI/CD webhook auto-scan]
    └──requires──> [Project model in DB]
    └──requires──> [Backend scan job execution]  (FastAPI background task or queue)

[Team member invitations]
    └──requires──> [Auth system]
    └──requires──> [Team/org model in DB]

[Pro/Team billing]
    └──requires──> [Auth system]
    └──requires──> [Team model]  (Team tier)
    └──enables──>  [Scan history]  (gated feature)
    └──enables──>  [Webhook auto-scan]  (gated feature)
    └──enables──>  [Team invitations]  (Team tier gate)

[Security trend chart]
    └──requires──> [Scan history]  (need >= 3 scans for trend to be meaningful)

[Cost trend]
    └──requires──> [Scan history]
```

### Dependency Notes

- **Auth is the root dependency**: Nothing SaaS works without it. Must be in Phase 1.
- **Scan storage enables everything**: Dashboard, history, sharing, comparison, trends all flow from being able to store and retrieve scans. Phase 1.
- **Billing gates features**: Pro/Team tier restrictions require billing to be working before gating logic can be enforced. Phase 2.
- **Comparison requires history**: Can't build scan diff until users have accumulated scans. Phase 3.
- **Webhook auto-scan requires a backend job system**: Even a simple FastAPI `BackgroundTask` works; don't need a full queue for v1 volumes.
- **ReactFlow viewer as SaaS component is the hardest adaptation**: Currently renders from `window.__INFRACANVAS_DATA__`; SaaS needs it fetching from API. This is HIGH complexity and blocks sharing and history views.

---

## MVP Definition

### Launch With (v1)

Minimum viable product to validate the SaaS concept and charge the first subscriber.

- [ ] Auth (GitHub OAuth + email/password) — without this, nothing is personalized
- [ ] Project creation + scan storage — users need a place to push scans to
- [ ] CLI `login` + `push` commands — the bridge; without it no one can get scans in
- [ ] Project dashboard — aggregate view of projects and last scan score
- [ ] Scan detail view with embedded ReactFlow diagram — the core product experience
- [ ] Shareable diagram links (public/private) — viral loop and core stated feature
- [ ] Scan history timeline (last N scans per project) — differentiates from just a file host
- [ ] Stripe billing with Pro tier ($49/mo) — must be able to charge before launch
- [ ] Basic per-finding remediation display — surfaces existing `Finding.remediation` data, low effort, high value

### Add After Validation (v1.x)

Add once first 20 paying users are in and core is stable.

- [ ] Team tier ($199/mo) + member invitations — monetization expansion; add when first team inquiry arrives
- [ ] CI/CD webhook auto-scan — reduces friction for repeat users; add when user feedback identifies manual push as pain point
- [ ] Scan comparison (side-by-side diff) — add when users start asking "what changed since last week?"
- [ ] Security score trend chart — add when users have enough history to make it meaningful (30+ days)
- [ ] Webhook delivery log — add alongside webhooks

### Future Consideration (v2+)

Defer until product-market fit is established and revenue covers the engineering cost.

- [ ] Compliance framework mapping (CIS, NIST) — HIGH complexity; needs rule tagging system first
- [ ] Public scan gallery — nice for GTM but not blocking revenue
- [ ] SSO/SAML — enterprise requirement; pursue when first enterprise deal is on the table
- [ ] Multi-cloud (Azure, GCP) — massive scope; defer until AWS is proven
- [ ] Self-hosted option — enterprise; defer post-PMF
- [ ] PR review bot (GitHub App) — defer; webhook covers the functional need
- [ ] Cost trend analytics — defer; cost display in diagram is sufficient for v1

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Auth (GitHub OAuth + email) | HIGH | LOW | P1 |
| CLI login + push | HIGH | LOW | P1 |
| Scan storage (project + artifact) | HIGH | LOW | P1 |
| Project dashboard | HIGH | LOW | P1 |
| ReactFlow viewer as SaaS component | HIGH | HIGH | P1 |
| Shareable diagram links | HIGH | MEDIUM | P1 |
| Stripe Pro billing | HIGH | MEDIUM | P1 |
| Scan history timeline | HIGH | MEDIUM | P1 |
| Per-finding remediation display | MEDIUM | LOW | P1 |
| Team invitations + Team billing | HIGH | MEDIUM | P2 |
| CI/CD webhook auto-scan | MEDIUM | MEDIUM | P2 |
| Scan comparison diff view | HIGH | HIGH | P2 |
| Security score trend chart | MEDIUM | MEDIUM | P2 |
| Webhook delivery log | MEDIUM | MEDIUM | P2 |
| Compliance framework mapping | MEDIUM | HIGH | P3 |
| Public scan gallery | LOW | LOW | P3 |
| SSO/SAML | LOW | HIGH | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

---

## Competitor Feature Analysis

| Feature | Terraform Cloud | Spacelift / env0 | Firefly | Our Approach |
|---------|-----------------|------------------|---------|--------------|
| Diagram/visualization | None (text only) | None | Read-only graph view | Interactive ReactFlow with security/cost overlays — unique |
| Security scanning | Sentinel/OPA policy | Checkov integration (external) | CSPM posture | Native 10→30 rules with visual annotation on diagram nodes |
| Drift detection | Run-based drift | Drift detection (execution-based) | Cloud vs IaC drift | Terraform plan overlay on diagram — visual, not just text |
| Scan/run history | Yes (runs) | Yes (runs) | Yes (resource history) | Scan history with point-in-time diagram replay |
| Scan comparison | Text diff of plans | Text diff | Not offered | Visual side-by-side diagram diff — clear differentiator |
| Cost estimation | Infracost integration | Infracost integration | Not offered | Native per-resource cost on diagram nodes |
| Sharing | Workspace sharing (team) | Workspace sharing | Not offered | Public/private shareable links with password option |
| CI/CD integration | Native (runs) | Native (runs) | Webhook-based | Webhook endpoint for auto-scan; lighter than execution-based |
| CLI → SaaS bridge | Yes (Terraform CLI) | Yes (Spacelift CLI) | Agent-based | `infracanvas push` — simple artifact upload, no execution |
| Execution | Yes (apply/plan) | Yes | No | No — read-only is the explicit position |

**Key insight:** No competitor combines interactive visualization + native security scoring + cost estimation + visual scan comparison in a read-only, no-execution SaaS. The "no execution" position is a feature, not a limitation — it dramatically reduces the compliance, blast-radius, and support burden.

---

## Sources

- Training knowledge of Terraform Cloud (HCP Terraform), Spacelift, env0, Firefly, Infracost Cloud, Bridgecrew/Prisma Cloud, Brainboard, Terravision/Blast Radius — confidence MEDIUM (training data through mid-2025, web search unavailable for current validation)
- PROJECT.md: InfraCanvas stated requirements, out-of-scope decisions, and target pricing
- ARCHITECTURE.md: Existing CLI pipeline and data models (ResourceGraph, Finding, SecurityRule)
- Market pattern: Product-Led Growth (PLG) via open-source CLI → SaaS upsell is well-established in DevOps tooling (Infracost, Terraform Cloud, Spacelift all use variants of this)

---
*Feature research for: IaC Visualization and Security SaaS (InfraCanvas)*
*Researched: 2026-04-15*
