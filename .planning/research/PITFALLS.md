# Domain Pitfalls

**Domain:** Hybrid Cloud Infrastructure Intelligence Platform (IaC visualization, network topology analysis, DC device integration)
**Researched:** 2026-04-15
**Confidence:** HIGH (grounded in codebase analysis + domain-specific research)

---

## Critical Pitfalls

### Pitfall 1: HCL Parser Silent Failures Create Ghost Infrastructure Diagrams

**What goes wrong:**
`python-hcl2` silently fails on approximately 15% of complex real-world Terraform modules. Common triggers: conditional expressions inside dynamic blocks, `templatefile()` calls in variable defaults, complex `for` expressions as object keys, two provider blocks with the same name, and unclosed strings that cause exponential parse time. The parser returns a partial result or empty dict rather than raising. The diagram renders with missing resources and edges. The user's security score reflects 70% of their infrastructure but shows no warning.

This is confirmed as a pre-existing issue in the codebase (`cli/infracanvas/parser/hcl.py` uses `except Exception: return` patterns per CONCERNS.md).

**Why it happens:**
python-hcl2 is a Lark-based parser implementing the HCL2 grammar, not Terraform's actual evaluator. Terraform expressions are lazily evaluated at plan time — values like `var.name`, `module.output`, `local.computed` are not literal strings. A pure lexer/parser cannot resolve them and must decide: fail hard or return a partial result. python-hcl2 chooses partial results.

**Consequences:**
- Security findings missed (resources not in graph cannot be scored)
- Drift detection false negatives (missing resources appear as deletions on next scan)
- In SaaS context: users trust incomplete security scores to gate deployments

**Prevention:**
1. Never swallow parser exceptions. Log the failing file path and the exception message to a structured `parse_warnings` list on every scan result.
2. Add an integration test corpus of 20+ real-world Terraform modules (pulled from Terraform Registry examples) that must parse without warnings.
3. For expressions that cannot be resolved (unbound variables), record the attribute as `"<unresolved: var.name>"` rather than dropping the resource entirely. Preserve the node in the graph with a "values unavailable" badge.
4. Consider migrating the parser to `tfparse` (cloud-custodian), which wraps the actual Terraform binary for expression evaluation — higher fidelity at the cost of requiring `terraform` on PATH, which is acceptable for CI/CD use.

**Warning signs:**
- Resource count in diagram differs from `terraform state list | wc -l` by more than 5%
- `dynamic` blocks in user's .tf files produce fewer nodes than expected
- Users report "my RDS instance is missing" from the diagram

**Phase:** Phase 2 (Canvas v1.0) pre-work. Blocking. Must be fixed before Azure parser work begins or the same pattern propagates.

---

### Pitfall 2: Module Graph Resolution Requires Multi-Pass — Single-Pass Parsers Break on Cross-Module References

**What goes wrong:**
Terraform modules reference each other: `module.vpc.subnet_id` in one file references an `output "subnet_id"` block in `modules/vpc/main.tf`. A single-pass parser that reads files sequentially cannot resolve these references. Resources that depend on module outputs appear as disconnected nodes. The dependency graph has false negative edges. Topology analysis built on this incomplete graph produces incorrect path computations in FlowMap.

**Why it happens:**
Phase 1 CLI was built for flat Terraform in a single directory. Module resolution requires a two-pass strategy: first pass builds a symbol table (all outputs, variables, locals), second pass resolves cross-file references. This is non-trivial to retrofit once the parser's output schema is locked.

**Consequences:**
- VPC/subnet grouping breaks when subnet IDs come from a child module
- Security findings for resources in child modules may be missed
- FlowMap network path tracer receives incorrect topology data, producing wrong asymmetric routing classifications

**Prevention:**
Before Azure parser work (Phase 2), add multi-pass resolution to the existing parser:
1. Walk all `.tf` files, collect all `output`, `variable`, `local`, and `module` blocks into a symbol table keyed by module path.
2. Second pass resolves interpolations against the symbol table. Unresolvable references (dynamic values known only at plan time) are recorded as unresolved, not dropped.
3. Add a test fixture with a 3-level module hierarchy and assert all cross-module edges are present in the graph output.

**Warning signs:**
- Module source paths in the graph are present but show no edges to consumer resources
- A `module.vpc.vpc_id` reference resolves to an empty string in the parsed output
- Users with module-heavy repos report empty or sparse diagrams

**Phase:** Phase 2 pre-work. Required before FlowMap topology integration (Phase 3) since FlowMap depends on accurate AWS resource graph.

---

### Pitfall 3: Network Topology Accuracy Requires Handling BGP Asymmetry as a First-Class Concept, Not an Edge Case

**What goes wrong:**
BGP asymmetric routing is the norm, not the exception, in enterprise networks. Traffic from A to B follows a different path than traffic from B to A by design — inbound traffic is influenced by BGP attributes (MED, local preference, AS path prepending) that are independent on each end. Tools that model network paths as bidirectional symmetric edges will misclassify every intentionally asymmetric BGP path as a problem, producing false positives that lose user trust immediately.

The deeper trap: a path tracer that works on static routes (AWS VPC route tables, TGW route tables) appears to work in demos but silently fails in real DC environments where BGP local-pref overrides static route decisions.

**Why it happens:**
Static route analysis is deterministic and tractable. BGP path selection requires knowledge of the full BGP RIB from each router's perspective, which requires querying each device individually. Most visualization tools stop at the route table layer.

**Consequences:**
- FlowMap shows false asymmetry alerts on correctly-configured enterprise networks
- Engineers lose trust in the tool after the first alert storm
- The tool is deprecated internally within weeks of deployment

**Prevention:**
1. The FlowMap data model must separate forward path and return path from the beginning. `NetworkPath` should have `forward_hops: List[PathHop]` and `return_hops: List[PathHop]` as separate fields — never a single `path` field.
2. Asymmetric routing detector must classify divergence by cause: `BGP_LOCAL_PREF` (expected, policy-driven), `BGP_MED` (expected, policy-driven), `ROUTE_LEAK` (unexpected), `MISSING_RETURN` (unexpected). Only the latter two should alert.
3. DC Collector Agent must collect BGP RIB table (`show bgp ipv4 unicast`) alongside route table data — the RIB is required to reconstruct BGP path selection decisions.
4. Provide a suppress-by-rule mechanism: annotation in the DC site config, or a policy in `.infracanvas.yml` that whitelists known-asymmetric paths.

**Warning signs:**
- `NetworkPath` data model has a single `hops` field (not `forward_hops` / `return_hops`)
- DC Collector Agent only collects `show ip route`, not `show bgp` output
- FlowMap demo uses only AWS TGW topology (symmetric by design) — no physical DC with BGP

**Phase:** Phase 3 design, before any FlowMap data model code is written.

---

### Pitfall 4: DC Agent Enterprise Deployment Blocked by Security Approval Process

**What goes wrong:**
In enterprise data centres, a "read-only agent" still requires a Change Advisory Board (CAB) approval process that takes 4–12 weeks. The approval requires: a formal description of every network protocol used, every port opened, every credential required, data residency documentation, an audit trail of what the agent reads, and sign-off from the security team. If the agent is deployed and begins collecting data before security review, it will be recalled and the vendor relationship damaged.

Specific blockers observed in practice:
- Security teams reject agents that require `privilege 15` (full admin) access on Cisco devices, even in read-only mode
- `NETCONF` requires enabling a service (`netconf-yang` or `netconf agent ssh`) on the device that may not be permitted by the network baseline configuration
- SSH key distribution to network devices requires a formal access request in most enterprises
- Outbound connections from DC devices to cloud APIs require firewall rule changes (weeks)

**Why it happens:**
Developers test against lab environments where they have full control. Lab devices have no change management, no security review. The friction only appears in the first real enterprise deployment.

**Consequences:**
- First enterprise customer takes 3 months to deploy, not 1 week
- The agent design is modified late to satisfy security requirements, introducing architectural debt
- Enterprise deals are delayed 1–2 quarters waiting for CAB approval

**Prevention:**
1. Minimum privilege design: create a dedicated read-only user on Cisco IOS XE/XR with exactly the commands needed. Document this as a Cisco IOS command list in the onboarding docs. The commands are: `show ip route`, `show bgp ipv4 unicast`, `show interfaces`, `show version`, `show cdp neighbors`, and (for ASA) REST API read-only role. No `privilege 15` required for read-only data collection.
2. Provide a "security review packet" as part of the agent distribution: architecture diagram, data flow diagram, ports opened (outbound 443 only), credential scope, data retention policy, and a formal description of what data is collected and what is not (no configuration writes, no ACL changes).
3. SSH is always available as the fallback transport. NETCONF is preferred but optional. Design the agent to degrade gracefully: if NETCONF is not enabled, fall back to SSH command parsing. This removes the need to enable a new service on the device.
4. Support an "air-gapped" mode: agent writes collected data to a local JSON file rather than sending to cloud. Security team reviews the file before approving outbound connectivity.

**Warning signs:**
- Agent documentation says "requires `privilege 15` access"
- First enterprise prospect says "our security team needs to review this" and there is no security packet to send them
- Agent requires NETCONF to be explicitly enabled and there is no SSH fallback

**Phase:** Phase 3 DC Agent design. The security review packet must exist before the first enterprise conversation.

---

### Pitfall 5: Multi-Tenant Scan Artifact Isolation Breaks Under Connection Pool Session State

**What goes wrong:**
PostgreSQL Row Level Security (RLS) isolates scan artifacts by tenant correctly in theory. In practice, PgBouncer (or any connection pooler) leaks session state between requests. RLS works via `SET LOCAL app.current_tenant = 'org_123'` which must be set on every connection before any query. In transaction-mode pooling (the default for PgBouncer), the session variable set in one transaction can persist into the next tenant's transaction if the variable is not explicitly cleared.

Additional trap: the table owner (the `postgres` superuser role used by migrations) bypasses RLS by default. If migrations are applied with the superuser role and application queries also run as superuser (common in development), RLS policies are silently bypassed in tests.

**Why it happens:**
Developers test with a single user and never hit cross-tenant access. The RLS policy appears to work. The session leak is invisible until two concurrent users with different tenants share the same pooled connection in production.

**Consequences:**
- Tenant A can read Tenant B's scan artifacts (security incident)
- Compliance audit failure (SOC2 CC6.1 violated)
- Regulatory exposure if scan artifacts contain sensitive resource attributes

**Prevention:**
1. Use Neon's built-in connection pooling (Neon Serverless driver) rather than self-managed PgBouncer. Neon's pooler is session-mode aware.
2. Create a dedicated application role (`infracanvas_app`) that has neither `SUPERUSER` nor `BYPASSRLS`. All application queries run as this role. Migrations run as a separate privileged role.
3. Every API handler that queries the database must set the tenant context before any query: `SET LOCAL app.current_org_id = ?`. Use a middleware/dependency injection pattern that enforces this on every request — not an opt-in pattern per endpoint.
4. Write a CI test that: (1) creates two tenants, (2) inserts a scan for Tenant A, (3) sets session context to Tenant B, (4) asserts the scan is not visible.
5. Enable `FORCE ROW LEVEL SECURITY` on all tables that contain scan artifacts. Without this, the table owner bypasses RLS.

**Warning signs:**
- Database migrations applied with the same role as application queries
- No `SET LOCAL app.current_org_id` in API request middleware
- RLS tests only test single-user access, not cross-tenant access

**Phase:** Phase 4 (SaaS Dashboard) database schema design. Must be in place before the first scan upload endpoint is deployed.

---

### Pitfall 6: Viewer Bundle Divergence Between CLI HTML Export and SaaS Dashboard

**What goes wrong:**
The CLI HTML export bundles the React viewer via `vite-plugin-singlefile` into a self-contained HTML file (~5MB target). The SaaS dashboard is a Next.js app. These feel like different delivery targets, so developers build a new DiagramCanvas component in the Next.js app rather than reusing the CLI viewer. Within three months, there are two rendering paths for the same graph data. Security finding severity badges render differently. Edge routing logic diverges. A bug fixed in one is not fixed in the other.

Secondary trap: the `window.__INFRACANVAS_DATA__` injection pattern used in CLI export is re-used in the SaaS context. In SaaS, this data comes from a server API that was populated by a different user — a script injection risk if resource names or attribute values contain script content.

**Why it happens:**
The path-of-least-resistance in Next.js is to build components in the app directory. The CLI viewer's Vite build configuration makes it feel like a separate project, not a library. No one creates the monorepo boundary early enough to make sharing the natural choice.

**Consequences:**
- Bug fix backlog doubles (every viewer fix must be applied to two codebases)
- CLI export and SaaS dashboard have different visual behavior — confuses users who switch between them
- Script injection risk in SaaS if window injection pattern is copied

**Prevention:**
1. Before any SaaS frontend work begins, extract `viewer/src/` into a workspace package: `packages/infracanvas-viewer`. Export a single component: `<InfracanvasViewer graph={InfracanvasGraph} />` that accepts graph data as a prop.
2. The CLI Vite build imports from `packages/infracanvas-viewer` and wraps it with a thin bootstrap that reads from `window.__INFRACANVAS_DATA__`.
3. The Next.js SaaS app imports from `packages/infracanvas-viewer` and passes graph data via React props from an API fetch.
4. The `window` injection pattern must never exist in the SaaS application — all data flows through React props.
5. Add a test that renders the viewer component with the same graph fixture in both the Vite and Next.js environments and asserts identical node/edge counts.

**Warning signs:**
- A DiagramCanvas.tsx or InfraGraph.tsx file exists in both `viewer/src/` and `apps/web/components/`
- The SaaS page uses raw script injection to load graph data
- "Fixed in web, not in CLI export" appears in commit messages

**Phase:** First action of Phase 4 (SaaS Dashboard), before any Next.js component is built.

---

### Pitfall 7: Cost Estimation Accuracy Erodes Due to Pricing API Staleness and Shared Resource Attribution

**What goes wrong:**
Two distinct accuracy problems compound each other:

**Staleness:** Cloud provider pricing APIs are updated weekly by Infracost's pipeline. AWS pricing pages update without notice. Instance type retirement, Savings Plans discounts, regional pricing variations (us-west-2 vs eu-central-1), and data transfer fees are frequently wrong in any cached pricing dataset. The hardcoded `us-east-1` pricing in the existing codebase (per PROJECT.md CONCERNS) means all multi-region estimates are wrong by default.

**Shared cost attribution:** Transit Gateway charges are per-attachment and per-GB processed. ExpressRoute charges are per circuit-hour. Checkpoint Firewall throughput costs are shared across all traffic passing through. There is no single correct formula for allocating these costs to individual workloads — every formula is an approximation that will be disputed by someone. Building cost allocation that looks precise (two decimal places) but is methodologically approximate creates user trust problems when the number differs from the actual AWS bill.

**Why it happens:**
Phase 1 cost estimation was built with hardcoded `us-east-1` pricing for simplicity (acknowledged in PROJECT.md). The problem is deferred. When multi-region and shared cost features are built, the pricing data pipeline and attribution methodology are designed under time pressure without enough domain depth.

**Consequences:**
- Cost estimates for non-us-east-1 resources are wrong by 5–40% depending on region and instance type
- Users compare CostLens shared cost attribution to their AWS Cost Explorer and find different numbers — they stop trusting the tool
- Enterprise customers with FinOps teams reject the tool because the methodology is not documented

**Prevention:**
1. Replace hardcoded pricing with the Infracost Cloud Pricing API (self-hostable, weekly-updated, 3M+ prices). This is a one-time integration that solves staleness. Do not build a custom pricing scraper.
2. Multi-region cost estimation must be region-parameterized from the start. Every pricing lookup must take a `(resource_type, region, instance_type)` tuple — never a default region constant.
3. For shared cost allocation (TGW, ExpressRoute, Firewall), be explicit about the methodology in the UI: "TGW cost allocated proportionally by GB processed per attachment (estimate)." Show the formula. Do not show a single number without the methodology.
4. Add a "cost confidence" indicator per resource: HIGH (on-demand, fixed hourly rate), MEDIUM (data transfer estimate), LOW (shared allocation). This is more useful to FinOps users than false precision.

**Warning signs:**
- `PRICING_REGION = "us-east-1"` constant anywhere in the codebase when multi-region support is being built
- CostLens UI shows cost to two decimal places without any methodology footnote
- No integration tests that assert pricing data is fetched from an external API rather than a hardcoded dict

**Phase:** Phase 4 (CostLens), before any cost display is rendered in the SaaS dashboard.

---

### Pitfall 8: Open-Source CLI Core Creates a Fork Vector That Erodes Commercial Moat

**What goes wrong:**
The MIT-licensed CLI core (parser, layout, icons, basic HTML export, JSON schema) is the acquisition channel for Pro/Team/Enterprise. The risk is a fork that adds just enough of the commercial features (basic security rules, simple cost estimation) to satisfy the majority of free users, eliminating the upgrade pressure. This has occurred to HashiCorp (OpenTofu), Redis (Valkey), and Elasticsearch (OpenSearch) — all infrastructure developer tools.

The specific InfraCanvas risk: the parser, graph builder, and ReactFlow viewer are the hardest parts to build. If those are MIT, a determined contributor (or a funded competitor) can add 10 more security rules and a simple cost table, ship it as "InfraCanvas Community," and capture the free tier permanently.

**Why it happens:**
Open-core is the correct PLG strategy for developer tools. The mistake is drawing the open/commercial boundary in the wrong place — too much capability in the open tier undercuts the commercial tier.

**Consequences:**
- Free tier users have no incentive to upgrade
- A community fork captures mindshare and the GitHub star graph
- Enterprise buyers use the fork to avoid vendor lock-in concerns

**Prevention:**
The boundary between open and commercial must be drawn at capability leverage points, not at feature count:
- **Open (MIT):** HCL parser, resource graph builder, ReactFlow viewer, JSON schema, basic CLI commands (`scan`, `export`). These are infrastructure — necessary but not the product.
- **Commercial:** Security engine (rules beyond the 10 included in open), FlowMap topology collection and path analysis, DC Collector Agent, CostLens allocation, SaaS backend, team features. These are the value delivery.
- Add proprietary behavioral elements to the open components that make the commercial features work better (e.g., the graph JSON schema is MIT, but the schema includes extension points only the commercial engine uses). This makes forking the open core less useful without the commercial engine.
- Do not open-source the security rule schema or the network findings schema in the first year. Schema lock-in is a moat.
- If a fork emerges, respond with community engagement (blog posts, Discord), not legal threats. Legal responses harm developer reputation and accelerate the fork.

**Warning signs:**
- GitHub issues requesting security rules as a community contribution ("can we add rules as plugins?")
- A fork appears on GitHub with more stars than the original within 6 months
- Enterprise prospect asks "can we fork the CLI and host internally without a license?"

**Phase:** Defined at project launch (Phase 1). The open/commercial boundary must be in the LICENSE file and README before the first public release.

---

### Pitfall 9: Solo Founder Operational Load Collapses Under Service Proliferation

**What goes wrong:**
The current stack has 8+ external services: Vercel, Railway/Fly.io, Neon, Cloudflare R2, Upstash Redis, Clerk, Stripe, and GitHub Actions. Each service has: a billing account, a secrets rotation cycle, an incident/status page to monitor, and a support escalation path. When any service has an incident, debugging requires correlating logs across 5 dashboards simultaneously. At 3 AM with an Enterprise customer SLA, this is not manageable for one person.

The specific failure mode: adding observability as an afterthought. Without centralized logging from the start, a FlowMap topology collection failure in the DC Agent (Go binary, remote execution) produces no actionable error signal. The engineer spends hours SSH-ing into customer environments with no telemetry.

**Why it happens:**
Each service is added for a good reason (R2 for egress costs, Upstash for serverless Redis, Neon for scale-to-zero). The operational complexity of the combination is not evaluated at addition time.

**Consequences:**
- Incident response time degrades as service count grows
- Solo founder spends 30% of time on operational tasks instead of product development
- First Enterprise customer SLA breach due to inability to diagnose distributed failure

**Prevention:**
1. Add structured logging + error tracking before Phase 4 goes live. Sentry (Python SDK + JavaScript SDK) covers both FastAPI errors and Next.js errors in one dashboard. The free tier is sufficient until $5K MRR.
2. Set a hard rule: every new external service must replace an existing one or remove a significant maintenance burden. No net additions after Phase 4 launch.
3. For the DC Agent specifically: agent must send structured JSON telemetry to the SaaS backend on every collection cycle — success/failure, bytes collected, connection method used, errors encountered. This is the only observability path for remote Go binaries.
4. Runbook for each critical failure mode must exist before the first enterprise customer onboards. Not after.
5. Use Railway or Fly.io's built-in metrics (CPU, memory, request rate) as the primary operational dashboard — do not add a separate APM tool until MRR justifies it.

**Warning signs:**
- Phase 4 ships without Sentry installed
- DC Agent returns exit code 1 with no structured error output
- More than 8 distinct vendor billing dashboards in use simultaneously

**Phase:** Phase 4 pre-work (before SaaS launch). Sentry installation is a pre-launch checklist item.

---

## Moderate Pitfalls

### Pitfall 10: ReactFlow Layout Performance Collapses at 500+ Nodes

**What goes wrong:**
The existing codebase has a confirmed O(n²) layout issue (per PROJECT.md CONCERNS). ReactFlow's built-in layout algorithms recompute positions for all nodes on every structural change. At 200 nodes this is noticeable. At 500 nodes (a medium-sized enterprise Terraform project) the browser tab hangs for 3–8 seconds on filter changes and re-renders. This is documented in ReactFlow's own GitHub discussions and is a known limitation of synchronous layout in the main thread.

**Prevention:**
1. Move layout computation to a Web Worker. The graph structure is serializable — send nodes/edges to a worker, receive computed positions, update React state once. This eliminates main-thread blocking.
2. Use `elkjs` (Eclipse Layout Kernel, WASM port) for layout rather than any pure-JS implementation. ELK handles graphs of 1000+ nodes with better performance characteristics.
3. Implement viewport culling: only render nodes that intersect the current viewport (`onlyRenderVisibleElements` prop). Off-screen nodes are present in the graph data but not in the DOM.
4. On filter changes, update node opacity/visibility without triggering layout recomputation. Layout should only run on structural changes (nodes added/removed), not visual changes (show/hide by type).

**Warning signs:**
- Layout computation runs synchronously on the React render thread
- Filter panel causes a visible repaint delay with a 200-node graph in the demo
- No Web Worker in the viewer build configuration

**Phase:** Phase 2 (Canvas v1.0) before large infrastructure demos are attempted.

---

### Pitfall 11: Cisco IOS vs IOS XE vs IOS XR NETCONF Behavioral Differences Break DC Agent

**What goes wrong:**
Cisco has three distinct operating systems with different NETCONF implementations. IOS XE 16.3+ supports NETCONF on port 830 with `netconf-yang` enabled. IOS XR uses a different YANG model namespace. Classic IOS may have a legacy NETCONF implementation that is incompatible with RFC 6241. Device firmware versions within the same OS family have breaking changes — a NETCONF query that works on IOS XE 16.12.4 returns a `bad-element` error on IOS XE 17.3.1a (confirmed in Cisco community forums).

Additionally, `show bgp ipv4 unicast` parsing via SSH fallback differs in output format between IOS and IOS XR — the regex patterns are not portable.

**Prevention:**
1. DC Agent must detect the device OS and version at connection time and route requests through OS-specific adapters. Do not write a "universal" NETCONF query that tries to work across all Cisco platforms.
2. Maintain a compatibility matrix (tested OS versions) in the agent repository. Fail explicitly with a clear error for untested versions rather than silently returning incomplete data.
3. For SSH fallback, use structured output where possible (`show bgp ipv4 unicast | json` on NX-OS, `show ip route | xml` on IOS XE 16.3+) rather than regex parsing of human-readable output.
4. Ship the agent with a `diagnose` subcommand that validates connectivity and reports the detected OS, version, and supported collection methods before any production collection is attempted.

**Warning signs:**
- DC Agent has a single NETCONF query path without OS-version branching
- SSH fallback uses regex on `show bgp` output without OS-version detection
- No `diagnose` or `--dry-run` mode in the agent

**Phase:** Phase 3 (FlowMap, DC Collector Agent design).

---

### Pitfall 12: Terraform Workspace and Provider Alias Handling Produces Duplicate Resource Nodes

**What goes wrong:**
Terraform workspaces allow the same configuration to be applied multiple times with different variable values (e.g., `prod` and `staging` workspaces). Provider aliases allow multiple AWS accounts or regions in a single configuration (`provider "aws" { alias = "us-west" region = "us-west-2" }`). A parser that does not handle these creates duplicate resource nodes with identical IDs — the graph has two `aws_vpc.main` nodes that are actually different resources in different regions or accounts.

**Prevention:**
1. Resource IDs in the graph must be qualified by workspace and provider alias: `aws:us-east-1:default:aws_vpc.main` not just `aws_vpc.main`.
2. When workspace is unknown (no `terraform.tfvars` file read), show a workspace selector UI in the viewer that lets users specify which workspace they are viewing.
3. Provider alias detection: parse all `provider` blocks and build a map of alias to region. Qualify resource nodes with their provider alias.

**Warning signs:**
- Graph contains two nodes with identical resource addresses
- Provider alias is parsed but not included in node IDs
- PROJECT.md notes "Terragrunt / workspaces — not supported at launch" — ensure this is an explicit message to users, not a silent parsing failure

**Phase:** Phase 2 (Canvas v1.0) — must be resolved before multi-region support is added.

---

## Minor Pitfalls

### Pitfall 13: Single-File HTML Export Exceeds 5MB with Complex Infrastructure

**What goes wrong:**
`vite-plugin-singlefile` inlines all JS, CSS, and data into one HTML file. The ReactFlow bundle + React + Zustand + Tailwind + embedded graph data grows quickly. At 500 resources with security findings, the JSON data alone is 1–2MB. Gzip is not applied to HTML files loaded from `file://` URLs (disk). The browser parses 5–8MB of inline JavaScript synchronously on tab open.

**Prevention:**
1. Separate the viewer bundle (JS/CSS) from the graph data. Inject data as a `<script id="infracanvas-data" type="application/json">` tag rather than a JS variable assignment. JSON parsing is faster than JS evaluation.
2. Strip all development-only code from the production bundle (`process.env.NODE_ENV === 'production'` tree-shaking).
3. Compress graph data before embedding: `LZ-string` provides browser-compatible LZ compression that reduces JSON size by 60–70% for repetitive infrastructure JSON. Decompress at runtime.
4. Set a hard file size budget of 5MB (per PROJECT.md performance requirements). Add a CI check that fails if the export exceeds 5MB.

**Warning signs:**
- HTML export file is over 5MB for a 200-resource project
- No build-time bundle size analysis configured in Vite

**Phase:** Phase 2 (Canvas v1.0) — set up size budget before Azure resources inflate the bundle further.

---

### Pitfall 14: Cloudflare R2 Signed URL Expiry Breaks Viewer Mid-Session

**What goes wrong:**
R2 signed URLs have a maximum expiry of 7 days and are generated at API request time. If the signed URL is generated with a short expiry (60 seconds, for security), the viewer component that embeds the URL will fail to load graph data for any user who opens the tab after 60 seconds. This produces a blank diagram with no error message unless explicitly handled.

**Prevention:**
1. Generate signed URLs with a minimum 4-hour expiry for any URL embedded in a viewer response.
2. The Next.js API route that returns scan data must always return a fresh signed URL — never cache the URL itself. Cache the scan metadata, not the signed URL.
3. Add a viewer-level error boundary that detects a 403 response on the graph data fetch and prompts the user to refresh rather than showing a blank canvas.

**Phase:** Phase 4 (SaaS Dashboard) — must be in the scan detail page implementation.

---

### Pitfall 15: API Key Scoping Allows Cross-Team Resource Access

**What goes wrong:**
Clerk API keys, when not explicitly scoped to an organization, default to user-scoped. A CI/CD pipeline that generates an API key for scan uploads uses the key of the engineer who set up the pipeline. When that engineer leaves the organization, the key is revoked, and the pipeline breaks. More seriously: if a Team member accidentally creates a user-scoped key (instead of org-scoped), that key can access all their personal projects including projects outside the team's organization.

**Prevention:**
1. In the SaaS dashboard, API key creation must require explicit scope selection (user vs. organization). Default to organization scope for keys created in an organization context.
2. The FastAPI key validation middleware must enforce that any key used to push a scan to a project belongs to an organization that owns that project — never allow a user-scoped key to write to an organization project.
3. On engineer offboarding, organization-scoped keys are automatically rotated if the departing member was the creator. Add this to the team management UI.

**Phase:** Phase 4 (SaaS Dashboard) — API key UI and FastAPI key validation middleware.

---

## Pre-Existing Pitfalls From CLI Codebase (Carry-Forward)

These were identified in the original codebase analysis and must be resolved before SaaS phases begin.

### CLI Auth Token Stored Insecurely
Token written to plaintext config file. Use OS keychain (`keyring` Python package) + `INFRACANVAS_API_KEY` env var override for CI/CD. **Phase: Phase 2 pre-work.**

### Viewer Code Split Risk
`viewer/src/` is currently a standalone Vite app. Extract to `packages/infracanvas-viewer` before any Next.js work begins. **Phase: First action of Phase 4.**

### Scan Artifact Storage Schema Locked In Too Early
Store scan metadata (counts, scores, timestamps) in queryable PostgreSQL columns. Store the full graph blob in R2. Never store the blob as a database column. **Phase: Phase 4 database design.**

### Injected Window Data as Script Vector in SaaS
`window.__INFRACANVAS_DATA__` is acceptable for CLI HTML export (user's own data). In SaaS, data must flow through React props from an API fetch — never through window injection. **Phase: Phase 4 viewer integration.**

### Stripe Webhook Handling Missing
`customer.subscription.deleted`, `invoice.payment_failed`, `invoice.payment_succeeded` handlers are acceptance criteria for billing, not optional follow-up work. **Phase: Phase 4 billing.**

### CLI Push Command Couples Scan Format to API Version
Version the push API from day one: `POST /api/v1/scans`. Include `cli_version` and `payload_version` in every push payload. **Phase: Phase 4 API design.**

### Auth Session Not Propagated Next.js to FastAPI
Write an integration test on day one: Next.js server component to FastAPI with valid JWT returns user-scoped data. **Phase: Phase 4 auth infrastructure.**

### Silent Parse Failures Become Trust Failures in SaaS
Fix all `except Exception: return` patterns in `cli/infracanvas/parser/hcl.py` before SaaS launch. Surface parse warnings in the dashboard. **Phase: Phase 2 pre-work.**

---

## Phase-Specific Warnings

| Phase Topic | Most Likely Pitfall | Mitigation |
|-------------|-------------------|------------|
| Canvas v1.0 — Azure parser | Replicates python-hcl2 silent failure pattern from AWS parser | Fix silent failures (Pitfall 1) before starting Azure work |
| Canvas v1.0 — multi-region cost | Hardcoded us-east-1 pricing | Replace with Infracost pricing API before multi-region ships |
| Canvas v1.0 — ReactFlow at scale | O(n²) layout on large projects | Web Worker + ELK layout before any 500-node demo |
| FlowMap — data model design | Single `hops` field on NetworkPath | Forward/return path separation required from day one |
| FlowMap — DC Collector Agent | Requires privilege 15 / no SSH fallback | Read-only role + SSH fallback + security packet |
| FlowMap — BGP analysis | False asymmetry alerts on BGP policy-driven routing | BGP RIB collection + cause classification |
| SaaS Dashboard — shared viewer | DiagramCanvas duplicated in Next.js app | Extract shared package before first Next.js component |
| SaaS Dashboard — RLS | PgBouncer session leak exposes tenant data | Neon pooler + FORCE ROW LEVEL SECURITY |
| SaaS Dashboard — cost display | False precision without methodology | Confidence indicators + methodology footnotes |
| SaaS Dashboard — launch | No error observability for distributed failures | Sentry + DC Agent telemetry before first customer |
| Enterprise — open-source fork | Security rules contributed back, reducing upgrade pressure | Commercial boundary at rules engine, not CLI |

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Silent HCL parse failures in production | HIGH | Add parse warnings to all historical scans; flag affected scans in UI; re-scan required to get accurate results |
| Viewer code diverged | HIGH | Audit both implementations; extract shared package; coordinate CLI + SaaS release |
| BGP false positive alert storm | HIGH | Emergency suppression toggle; post-mortem with customer; redesign path classifier |
| Tenant data exposed via RLS bypass | CRITICAL | Immediate rollback; audit access logs; notify affected tenants; security incident report |
| DC Agent rejected by security team | MEDIUM | Deliver security packet; remove privilege 15 requirement; redesign as SSH-only if needed |
| Cost estimates disputed by FinOps team | MEDIUM | Add methodology documentation; switch to Infracost API; add confidence indicators |
| Open-source fork captures free tier | LOW-MEDIUM | Community engagement + feature acceleration; not legal escalation |
| Service proliferation causes SLA breach | MEDIUM | Add Sentry immediately; build runbooks; reduce service count on next infrastructure review |

---

## Sources

- Codebase analysis: `.planning/PROJECT.md` — stack decisions, confirmed CONCERNS (HIGH confidence)
- python-hcl2 known issues: GitHub amplify-education/python-hcl2 issues #76, #149, #150, #253 — exponential parse time, conditional statement failures, duplicate block failures (HIGH confidence)
- BGP asymmetric routing: Noction BGP blog, RIPE Labs BGPPlay documentation — BGP asymmetry as normal behaviour, detection approaches (HIGH confidence)
- PostgreSQL RLS pitfalls: permit.io RLS implementation guide, AWS multi-tenant RLS blog, thenile.dev RLS blog — PgBouncer session leaks, FORCE ROW LEVEL SECURITY, superuser bypass (HIGH confidence)
- Cisco NETCONF compatibility: Cisco community forums (IOS XE 17.3.1a breaking change), Cisco NX-OS programmability guide — version-specific NETCONF behaviours (MEDIUM confidence — verify against target device baseline)
- ReactFlow performance: xyflow/xyflow GitHub discussions #4975, #4617, #3044 — confirmed performance limits and mitigation strategies (HIGH confidence)
- Infracost pricing API: infracost/infracost GitHub, IBM-Cloud/infracost-cloud-pricing-api — weekly update cycle, pricing API architecture (HIGH confidence)
- Open-source fork risk: The New Stack "Forks, Clouds and the New Economics of Open Source Licensing", DEV Community "Open Source in 2026: The Fork Wars Are Getting Ugly" — HashiCorp/OpenTofu, Redis/Valkey precedents (HIGH confidence)
- Solo founder operational complexity: DEV Community solo founder SaaS infrastructure post — service proliferation risks (MEDIUM confidence)
- vite-plugin-singlefile limitations: GitHub richardtallent/vite-plugin-singlefile — storage limitations, size considerations (HIGH confidence)
- Clerk multi-tenant API key scoping: Clerk official docs, clerk.com blog "Add API Key support" — org vs user scope behaviour (HIGH confidence)

---
*Pitfalls research for: InfraCanvas — hybrid cloud infrastructure intelligence platform*
*Researched: 2026-04-15*
