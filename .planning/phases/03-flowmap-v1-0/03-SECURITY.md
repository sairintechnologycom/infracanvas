---
phase: 03
slug: flowmap-v1-0
status: verified
threats_open: 0
asvs_level: 1
created: 2026-04-19
---

# Phase 03 — Security (FlowMap v1.0)

> Per-phase security contract: threat register, accepted risks, and audit trail.
> Aggregates 9 plan-level STRIDE registers (PLAN 03-01 … 03-09) into a single phase view.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| CLI process → AWS SDK (boto3) | Customer-local read-only IAM credentials flow into boto3 session; signed API calls egress to AWS control plane | Credentials (HIGH); account/VPC/TGW IDs, CIDRs, route tables (MEDIUM) |
| CLI process → Azure SDK (azure-identity / azure-mgmt-network) | ARM_* env vars → ClientSecretCredential; signed Entra ID token requests egress to ARM | ARM_CLIENT_SECRET (HIGH); subscription/tenant IDs, NSG rules, peer ASNs (MEDIUM) |
| Collector RuntimeError → Rich Console | Exception strings surface via Console.print; any interpolation of raw env-var values would leak credentials | Exception message text only (never traceback, never logger.exception) |
| graph.nodes.attributes → single-file HTML viewer | Raw AWS/Azure SDK attributes embedded in Pydantic JSON + injected into viewer_template.html | Resource IDs, IPs, ASNs, flow-log metadata (MEDIUM — customer-owned offline artifact) |
| YAML rules/network/*.yaml → security/loader.py | NET-* rule files parsed at runtime by PyYAML safe_load | Declarative rule definitions (LOW — check-in, CODEOWNERS-reviewed) |
| window.__INFRACANVAS_DATA__ → Zustand store | Pre-existing Phase 1 boundary; 3a adds additive network_paths / dc_sites fields | JSON payload (same trust as Phase 1) |
| React.lazy chunks → runtime import | Single-file HTML bundle inlines all chunks via vite-plugin-singlefile — no network fetch | Chunk bytecode (same-origin, no external) |
| viewer/src → viewer/dist → cli/infracanvas/export/viewer_template.html | Build-pipeline supply-chain boundary (`npm run build` → postbuild `cp`) | Bundle bytes shipped to all CLI customers |
| pyproject.toml / package.json → package resolvers | Supply-chain surface (pip, npm) | Transitive dependency graph |

---

## Threat Register

*Status legend — `closed`: mitigation verified in code/tests, or risk formally accepted, or risk transferred to an owning plan.*

### PLAN 03-01 — Schema + dependencies

| Threat ID | Category | Component | Disposition | Mitigation / Evidence | Status |
|-----------|----------|-----------|-------------|-----------------------|--------|
| T-03-01-01 | T (Tampering) | pyproject.toml supply chain | mitigate | All four new Python deps pinned with upper bounds at `cli/pyproject.toml:43-49` (`boto3>=1.40,<2`, `azure-identity>=1.20,<2`, `azure-mgmt-network>=28,<31`, `azure-mgmt-resource>=23,<26`) | closed |
| T-03-01-02 | I (Information Disclosure) | NetworkFinding.evidence + DCCollectorReading.payload | accept | Inherits existing `Finding.evidence` pattern — no new exposure surface. Phase 4 RLS will isolate per-tenant. | closed |
| T-03-01-03 | T (Tampering) | viewer/package.json elkjs pin | mitigate | `viewer/package.json:20` — `"elkjs": "^0.11.1"` (patch-only range) | closed |
| T-03-01-04 | D (Denial of Service) | ResourceGraph.network_paths unbounded list | accept | Empty in 3a (no path tracer); 3b bounded by topology node count | closed |
| T-03-01-05 | S (Spoofing) | Additive schema bump v2.0→v2.1 | mitigate | `cli/infracanvas/graph/models.py:176-177` — `network_paths`/`dc_sites` use `default_factory=list`; backcompat asserted in `cli/tests/test_flowmap_models.py:19,37` | closed |

### PLAN 03-02 — Orchestrator + `--flowmap` flag

| Threat ID | Category | Component | Disposition | Mitigation / Evidence | Status |
|-----------|----------|-----------|-------------|-----------------------|--------|
| T-03-02-01 | I (Information Disclosure) | RuntimeError → Console.print in run_flowmap_collection | mitigate | `cli/infracanvas/flowmap/collector.py:53-57,65-69` — prints only `f"[yellow]Warning:[/yellow] {exc}"`; never traceback or logger.exception | closed |
| T-03-02-02 | D (Denial of Service) | Unbounded AWS/Azure pagination | transfer | Out of scope for orchestrator. Ownership transferred to plans 03-03 (T-03-03-04) and 03-04 (T-03-04-04), both verified closed. | closed |
| T-03-02-03 | E (Elevation of Privilege) | boto3 / azure SDK credentials chain | accept | Standard SDK chain (D-05); IAM scope is read-only per CONTEXT.md security_enforcement. No write APIs invoked from collector.py. | closed |
| T-03-02-04 | T (Tampering) | `--flowmap` flag silently dropped by Typer | mitigate | `cli/tests/test_flowmap_cli.py:100-108` — `test_help_lists_flowmap` asserts `"--flowmap"` present in `--help` output | closed |
| T-03-02-05 | R (Repudiation) | Missing-creds silent skip | accept | D-05 explicitly prefers "warn and continue" over hard-fail. Warning IS logged to Console; operator sees it at scan time. Non-repudiation not a v1 beta-preview goal. | closed |

### PLAN 03-03 — AWS FlowMap collectors

| Threat ID | Category | Component | Disposition | Mitigation / Evidence | Status |
|-----------|----------|-----------|-------------|-----------------------|--------|
| T-03-03-01 | E (Elevation of Privilege) | boto3 session scope | mitigate | `cli/infracanvas/flowmap/aws.py:82,110,134,139,166,190,213,237,257,287` — only `describe_*` / `search_*` (read-only) AWS API calls; no write APIs | closed |
| T-03-03-02 | I (Information Disclosure) | RuntimeError on ImportError | mitigate | `cli/infracanvas/flowmap/aws.py:32-34` — `raise RuntimeError(...) from None` with credential-free message | closed |
| T-03-03-03 | I (Information Disclosure) | AWS account IDs / IPs in graph.attributes → HTML | accept | Viewer is offline single-file HTML, customer-owned artifact (CONTEXT.md D-05). Phase 4 RLS isolates per-tenant in SaaS mode. | closed |
| T-03-03-04 | D (Denial of Service) | Unbounded TGW route lookup | mitigate | `cli/infracanvas/flowmap/aws.py:141` — `Filters=[{"Name":"state","Values":["active","blackhole"]}]`; single-region session at line 36 | closed |
| T-03-03-05 | T (Tampering) | Placebo fixtures injected with malicious TGW IDs | accept | Fixtures are check-in artifacts reviewed at PR time; out of scope for runtime collector | closed |
| T-03-03-06 | S (Spoofing) | boto3 session credential chain | accept | Standard AWS SDK chain (D-05); spoofing equivalent to compromising user's shell/IAM | closed |
| T-03-03-07 | I (Information Disclosure) | describe_flow_logs metadata → HTML | mitigate | `cli/infracanvas/flowmap/aws.py:279-305` — `_collect_flow_log_metadata` stores only FlowLogId / LogGroupName / destination_type / traffic_type / log_format; NO log contents | closed |

### PLAN 03-04 — Azure FlowMap collectors

| Threat ID | Category | Component | Disposition | Mitigation / Evidence | Status |
|-----------|----------|-----------|-------------|-----------------------|--------|
| T-03-04-01 | E (Elevation of Privilege) | ClientSecretCredential scope | mitigate | `cli/infracanvas/flowmap/azure.py:57-62` — ClientSecretCredential only; `list()` / `list_all()` read-only calls at lines 117, 141, 161, 196, 225, 266, 288, 315, 352, 362. IAM Reader role per user_setup. | closed |
| T-03-04-02 | I (Information Disclosure) | RuntimeError leaking ARM_CLIENT_SECRET | mitigate | `cli/infracanvas/flowmap/azure.py:48` `from None`; lines 52-55 emit only MISSING-var names (never set-var values). `cli/tests/test_flowmap_azure.py:138-143` — `test_credential_values_not_leaked_in_exception` uses sentinel `super-secret-v4lue-xyz` and asserts absence. | closed |
| T-03-04-03 | I (Information Disclosure) | Azure tenant/subscription IDs → HTML | accept | Same surface as Phase 2 Azure parser + T-03-03-03 (CONTEXT.md D-05) | closed |
| T-03-04-04 | D (Denial of Service) | Unbounded `list_all()` iteration | mitigate | `cli/infracanvas/flowmap/azure.py:62` — subscription-scoped `NetworkManagementClient(cred, ARM_SUBSCRIPTION_ID)`; defensive try/except at every collector (lines 116, 140, 195, 265, 287, 350) | closed |
| T-03-04-05 | S (Spoofing) | ARM_CLIENT_SECRET compromise | accept | Customer-managed credential chain; compromise out of CLI's control | closed |
| T-03-04-06 | I (Information Disclosure) | flow_logs.list metadata | mitigate | `cli/infracanvas/flowmap/azure.py:346-388` — `_collect_flow_log_metadata` attaches only flow_log_id / enabled / retention_days / format_type / storage_id; no log contents | closed |
| T-03-04-07 | T (Tampering) | Fixture tampering with malicious IDs | accept | Fixtures are check-in artifacts reviewed at PR time | closed |

### PLAN 03-05 — NET-* security rules

| Threat ID | Category | Component | Disposition | Mitigation / Evidence | Status |
|-----------|----------|-----------|-------------|-----------------------|--------|
| T-03-05-01 | T (Tampering) | Malicious YAML in rules/network/ | accept | Rules are check-in artifacts under CODEOWNERS/PR review; runtime uses PyYAML `safe_load` (Phase 1 precedent) | closed |
| T-03-05-02 | I (Information Disclosure) | NET rule Finding.evidence exposing raw attributes | accept | Existing Phase 1+2 pattern — `_sanitize_evidence` helper in engine.py; NET-* inherits automatically | closed |
| T-03-05-03 | D (Denial of Service) | Rule eval cost (500 nodes × 40 rules) | accept | Phase 1 perf budget (< 10s for 500 nodes); NET-* ~20% increase, within budget | closed |
| T-03-05-04 | S (Spoofing) | Forged framework_ids implying compliance | mitigate | `cli/infracanvas/security/rules/network/aws_tgw.yaml:5,17` — `framework_ids` present but documented as "plausible mappings — NOT authoritative compliance assertions" in `03-05-SUMMARY.md:43,109,163`. Phase 5 CMP-* will introduce authoritative mapping. | closed |
| T-03-05-05 | R (Repudiation) | Findings disappearing silently (rule regression) | mitigate | `cli/tests/test_flowmap_network_rules.py:113-144` — `TestNetworkRuleEvaluation` with `@pytest.mark.parametrize("rule_id", AWS_NET_IDS)` + `AZURE_NET_IDS` locks positive fixtures | closed |

### PLAN 03-06 — Store + TabBar

| Threat ID | Category | Component | Disposition | Mitigation / Evidence | Status |
|-----------|----------|-----------|-------------|-----------------------|--------|
| T-03-06-01 | T (Tampering) | Malicious activeTab value via devtools | accept | Only 'canvas' / 'flowmap' valid; TS compile-time check. Runtime tamper = bookmarklet attack — out of v1 scope (viewer read-only). | closed |
| T-03-06-02 | I (Information Disclosure) | selectedPath exposure | accept | Same-origin React state; same surface as existing selectedNode | closed |
| T-03-06-03 | D (Denial of Service) | React.lazy chunk load failure | mitigate | `viewer/src/App.tsx:12-22` lazy imports + Suspense fallback at line 51; `viewer/src/components/flowmap/FlowMapCanvas.tsx:145-150` `.catch(() => { setNodes([]); setEdges([]); })`. Single-file HTML inlines all chunks (vite-plugin-singlefile) — network load is physically impossible at runtime. | closed |
| T-03-06-04 | S (Spoofing) | ARIA tablist misreporting activeTab | mitigate | `viewer/src/__tests__/flowmap/TabBar.test.tsx:21,34` — asserts `aria-selected === 'true'` reflects store state | closed |
| T-03-06-05 | R (Repudiation) | No audit log in 3a viewer | accept | Viewer is single-shot report, not stateful app. Audit trail lands in Phase 4 SaaS. | closed |

### PLAN 03-07 — FlowMapCanvas + nodes + edges

| Threat ID | Category | Component | Disposition | Mitigation / Evidence | Status |
|-----------|----------|-----------|-------------|-----------------------|--------|
| T-03-07-01 | T (Tampering) | XSS via attribute values | mitigate | Grep of `viewer/src/**` returns ZERO hits for unsafe DOM sinks (`innerHTML`, `srcDoc`, React's escape-hatch prop). All attribute renderings use JSX text-children (React auto-escapes). | closed |
| T-03-07-02 | D (Denial of Service) | elkjs layout on adversarial 10k-node graph | mitigate | `viewer/src/components/flowmap/FlowMapCanvas.tsx:116` + `viewer/src/components/flowmap/lib/elkLayout.ts:1,6,67` — ELK invoked asynchronously via microtask, not frame-blocking. Realistic 3a graph < 500 nodes (single-region per cloud scope). | closed |
| T-03-07-03 | I (Information Disclosure) | MiniMap rendering highlighted nodes with IPs | accept | Same surface as existing DiagramCanvas — miniview colors only, no label text. No new exposure. | closed |
| T-03-07-04 | S (Spoofing) | FirewallNode gauge accepting spoofed throughput | accept | Attribute source is upstream Azure/AWS SDK metadata (Plan 03-03/04); upstream trust boundary — not a viewer concern | closed |
| T-03-07-05 | R (Repudiation) | window.keydown Escape clearing selection silently | accept | Non-destructive, reversible UX per UI-SPEC | closed |
| T-03-07-06 | E (Elevation of Privilege) | React.lazy dynamic import for FlowMapCanvas | mitigate | `viewer/package.json:38` — `vite-plugin-singlefile` bundles all chunks inline; same-origin guaranteed, no runtime network fetch | closed |

### PLAN 03-08 — FilterPanel + PathDetailPanel + EmptyState

| Threat ID | Category | Component | Disposition | Mitigation / Evidence | Status |
|-----------|----------|-----------|-------------|-----------------------|--------|
| T-03-08-01 | T (Tampering) | XSS via attribute values in Attributes tab | mitigate | `viewer/src/components/flowmap/PathDetailPanel.tsx:183` — `{JSON.stringify(attributes, null, 2)}` inside JSX `<pre>` (React auto-escapes). Zero unsafe-DOM-sink grep hits across viewer/src. | closed |
| T-03-08-02 | I (Information Disclosure) | External docs link leaking window.opener | mitigate | `viewer/src/components/flowmap/FlowMapEmptyState.tsx:122-123` — `target="_blank"` + `rel="noopener noreferrer"` | closed |
| T-03-08-03 | D (Denial of Service) | Massive attributes blob crashing JSON.stringify | accept | Realistic attribute payload < 1MB per node; performance not a v1 concern | closed |
| T-03-08-04 | S (Spoofing) | Clipboard API overridden by malicious extension | accept | Browser extension attacks out of v1 scope | closed |
| T-03-08-05 | R (Repudiation) | Copy action silent on failure | accept | Fallback catch is silent; CLI command is user-selectable inline so copy-failure does not block the user | closed |
| T-03-08-06 | E (Elevation of Privilege) | Beta pill link misuse | accept | Pill is cosmetic; no elevation surface | closed |

### PLAN 03-09 — Viewer bundle rebundle + regression guard

| Threat ID | Category | Component | Disposition | Mitigation / Evidence | Status |
|-----------|----------|-----------|-------------|-----------------------|--------|
| T-03-09-01 | T (Tampering, supply chain) | `cp` into cli/infracanvas/export/viewer_template.html | mitigate | `viewer/package.json:9` — `"postbuild": "cp dist/index.html ../cli/infracanvas/export/viewer_template.html"` uses local relative paths only; no `/tmp` or external fetch. Supply chain is `git checkout → npm install → npm run build → cp`, all under developer control. | closed |
| T-03-09-02 | E (Elevation / CI bypass) | pytest regression guard skipped in CI | mitigate | `cli/pyproject.toml:62-63` — `testpaths = ["tests"]`. `cli/tests/test_viewer_template_bundle.py` present with no skip markers and no conditional gates. 3 assertions: Phase-3 tokens present, placeholder intact, size ≥ 1MB. | closed |

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-03-01 | T-03-01-02 | Finding.evidence may hold sensitive attrs (IPs, ASNs); inherited Phase 1 pattern; Phase 4 RLS isolates per-tenant in SaaS | Bhushan | 2026-04-19 |
| AR-03-02 | T-03-01-04 | ResourceGraph.network_paths array stays empty in 3a; bounded by topology node count in 3b | Bhushan | 2026-04-19 |
| AR-03-03 | T-03-02-03 | Standard SDK credential chain; read-only IAM per CONTEXT.md security_enforcement | Bhushan | 2026-04-19 |
| AR-03-04 | T-03-02-05 | Missing-creds path warns and continues per D-05; non-repudiation not a v1 beta-preview goal | Bhushan | 2026-04-19 |
| AR-03-05 | T-03-03-03 | AWS account IDs / IPs in single-file HTML are customer-owned offline artifact (D-05); Phase 4 RLS handles SaaS tenant isolation | Bhushan | 2026-04-19 |
| AR-03-06 | T-03-03-05 | Fixture tampering is a PR-review surface, not a runtime collector threat | Bhushan | 2026-04-19 |
| AR-03-07 | T-03-03-06 | boto3 credential chain spoofing = compromising the user's shell; out of CLI scope | Bhushan | 2026-04-19 |
| AR-03-08 | T-03-04-03 | Azure tenant/subscription IDs in HTML — same posture as AR-03-05 | Bhushan | 2026-04-19 |
| AR-03-09 | T-03-04-05 | ARM_CLIENT_SECRET compromise is customer-managed; out of CLI scope | Bhushan | 2026-04-19 |
| AR-03-10 | T-03-04-07 | Fixture tampering — see AR-03-06 | Bhushan | 2026-04-19 |
| AR-03-11 | T-03-05-01 | rules/network/*.yaml are check-in artifacts under CODEOWNERS + PyYAML safe_load | Bhushan | 2026-04-19 |
| AR-03-12 | T-03-05-02 | Finding.evidence sanitized by engine._sanitize_evidence; NET-* inherits automatically | Bhushan | 2026-04-19 |
| AR-03-13 | T-03-05-03 | Rule evaluation cost within Phase 1 perf budget (<10s / 500 nodes) | Bhushan | 2026-04-19 |
| AR-03-14 | T-03-06-01 | activeTab tamper via devtools = bookmarklet attack; viewer is read-only — out of v1 scope | Bhushan | 2026-04-19 |
| AR-03-15 | T-03-06-02 | selectedPath is same-origin React state; no cross-frame/cross-origin exposure | Bhushan | 2026-04-19 |
| AR-03-16 | T-03-06-05 | Viewer is single-shot report; audit log lands in Phase 4 SaaS | Bhushan | 2026-04-19 |
| AR-03-17 | T-03-07-03 | MiniMap miniview colors only; no label text — same surface as DiagramCanvas | Bhushan | 2026-04-19 |
| AR-03-18 | T-03-07-04 | Firewall throughput source is upstream SDK metadata; upstream trust boundary | Bhushan | 2026-04-19 |
| AR-03-19 | T-03-07-05 | Escape-to-clear-selection is non-destructive and reversible UX per UI-SPEC | Bhushan | 2026-04-19 |
| AR-03-20 | T-03-08-03 | Realistic attribute payload < 1MB per node; perf not a v1 concern | Bhushan | 2026-04-19 |
| AR-03-21 | T-03-08-04 | Browser extension attacks out of v1 scope | Bhushan | 2026-04-19 |
| AR-03-22 | T-03-08-05 | Copy-failure is silent but CLI command is user-selectable inline; non-blocking | Bhushan | 2026-04-19 |
| AR-03-23 | T-03-08-06 | Beta pill is cosmetic; no elevation surface | Bhushan | 2026-04-19 |

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-04-19 | 48 | 48 | 0 | gsd-security-auditor (sonnet) |

### Audit 2026-04-19

- **ASVS level:** L1
- **Block condition:** `mitigate` threats must be verified
- **Result:** `## SECURED` — 24/24 mitigate threats verified with file:line evidence; 22 accept + 2 transfer dispositions acknowledged
- **Transfer reconciliation:** T-03-02-02 (unbounded pagination) transferred from PLAN 03-02 to PLAN 03-03 (T-03-03-04) and PLAN 03-04 (T-03-04-04) — both verified closed, so the transfer chain terminates in closed state
- **No unregistered threat flags:** the only `## Threat Flags` section found (03-08-SUMMARY.md:134-136) explicitly maps to registered T-03-08-01 and T-03-08-02
- **Implementation files inspected (read-only):** cli/pyproject.toml, viewer/package.json, cli/infracanvas/graph/models.py, cli/infracanvas/flowmap/{collector,aws,azure}.py, cli/infracanvas/security/rules/network/*.yaml, cli/tests/test_flowmap_{cli,models,aws,azure,network_rules}.py, cli/tests/test_viewer_template_bundle.py, viewer/src/App.tsx, viewer/src/components/flowmap/{FlowMapCanvas,FlowMapEmptyState,PathDetailPanel}.tsx, viewer/src/components/flowmap/lib/elkLayout.ts, viewer/src/__tests__/flowmap/TabBar.test.tsx

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-04-19
