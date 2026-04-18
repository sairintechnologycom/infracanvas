# Phase 3: FlowMap v1.0 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-18
**Phase:** 03-flowmap-v1-0
**Areas discussed:** Phase split, Topology collector, FlowMap viewer surface, Tier-gate bootstrap
**Follow-up areas:** 3a/3b boundary line, CLI surface

---

## Gray Area Selection

| Area | Description | Selected |
|------|-------------|----------|
| Phase split | 37 reqs in one phase vs. split into 3a/3b | ✓ |
| Tier-gate bootstrap | How to gate paid FlowMap before SaaS ships | ✓ |
| Topology collector | CLI vs DC Agent vs hybrid for cloud topology data | ✓ |
| FlowMap viewer surface | Tab / overlay / separate HTML | ✓ |

All four gray areas selected for discussion.

---

## Phase split

| Option | Description | Selected |
|--------|-------------|----------|
| Split 3a/3b (Recommended) | 3a = data model + cloud collectors + viewer + cloud-only NET findings; 3b = DC Agent + Cisco/Checkpoint + path tracer + asymmetric detection + tier gate | ✓ |
| Three-way split (3a/3b/3c) | 3a = data model + cloud collectors + viewer; 3b = DC Agent; 3c = path tracer + asymmetric + ASA + Checkpoint + tier gate | |
| Keep as one phase | Ship FlowMap v1.0 as a single coherent release — one big marketing moment | |
| Different split | User-described cut | |

**User's choice:** Split 3a/3b (Recommended)
**Notes:** Two-way split preserves the v1.0 coherence (3a + 3b both released under FlowMap banner) while unblocking cloud-only verification before the Go toolchain work starts.

---

## Topology collector

| Option | Description | Selected |
|--------|-------------|----------|
| CLI for cloud, agent for DC (Recommended) | Cloud collectors in CLI Python; DC Agent only for on-prem hardware | ✓ |
| Agent collects everything | DC Agent is single ingest path; mandatory even for cloud-only customers | |
| CLI for everything (no agent in P3) | Defer Go DC Agent entirely; CLI does cloud now, on-prem later | |

**User's choice:** CLI for cloud, agent for DC (Recommended)
**Notes:** Cloud-only customers get FlowMap value with zero agent install. Mirrors `--shadow` UX precedent from Phase 2.

---

## FlowMap viewer surface

| Option | Description | Selected |
|--------|-------------|----------|
| Tab inside existing viewer (Recommended) | Top-level `[Canvas | FlowMap]` toggle in single-file HTML; same store, same export pipeline | ✓ |
| Layer overlay on Canvas | FlowMap paths rendered on top of Canvas diagram; toggle layers on/off | |
| Separate `infracanvas flowmap` command | New CLI command produces its own HTML file | |

**User's choice:** Tab inside existing viewer (Recommended)
**Notes:** One HTML to share, one URL to open, familiar UX. Layer-overlay risks layout conflicts between dagre tier layout and path-flow layout.

---

## Tier-gate bootstrap

| Option | Description | Selected |
|--------|-------------|----------|
| Free during P3 beta, gate in P4 (Recommended) | FlowMap ships open in Phase 3; TIR-01/02 moves to Phase 4 with SaaS billing | ✓ |
| License-token paste | Stripe checkout emails a signed JWT; CLI verifies with embedded public key | |
| Hard-gate now, license server in P3 | Minimal FastAPI license API on Railway; CLI calls it every FlowMap invocation | |

**User's choice:** Free during P3 beta, gate in P4 (Recommended)
**Notes:** Zero auth/billing code in Phase 3. Beta window produces design-partner signal and word-of-mouth before paywalling. "Beta, free during preview" becomes the marketing frame.

---

## 3a/3b boundary (follow-up)

| Option | Description | Selected |
|--------|-------------|----------|
| 3a = topology + viewer only, 3b = all path math (Recommended) | 3a ships FDM-01..03 + AWS-01..03 + AZN-01..03 + FMV-01..05 + cloud-only NET findings. All path tracing, asymmetric detection, classification, and DC integrations land in 3b | ✓ |
| 3a includes cloud-only paths + cloud-only asymmetric | 3a extends to cloud-only forward/return path computation and AWS↔Azure direct asymmetric detection | |
| Different boundary | User-described cut | |

**User's choice:** 3a = topology + viewer only, 3b = all path math (Recommended)
**Notes:** Cleaner mental model — 3a is "collect + show", 3b is "analyze". Less code rewriting when 3b lands.

---

## CLI surface (follow-up)

| Option | Description | Selected |
|--------|-------------|----------|
| `scan --flowmap` flag (Recommended) | Existing `scan` gets a new flag; one command, one HTML output with both tabs | ✓ |
| Separate `infracanvas flowmap` subcommand | New top-level command; separate HTML | |
| Always-on (no flag) | FlowMap runs automatically when cloud creds present | |

**User's choice:** `scan --flowmap` flag (Recommended)
**Notes:** Mirrors `--shadow` pattern. Explicit opt-in respects users who don't want surprise network API calls.

---

## Claude's Discretion (captured in CONTEXT.md)

- Exact AWS / Azure SDK calls, batching, and retry strategy
- Flow-log ingestion mechanism (S3 pull vs CloudWatch Logs Insights vs Azure Monitor)
- FlowMapCanvas layout algorithm (custom vs elkjs vs hierarchical-with-fixed-ranks)
- Dual-color edge rendering technique
- Exact NET-id allocation across 3a vs 3b based on rule path-dependency
- Number of cloud-only NET rules shipped in 3a
- Test fixture strategy for cloud network collection (moto/placebo vs hand-crafted JSON vs sanitized live snapshots)

## Deferred Ideas (captured in CONTEXT.md)

- Phase 3b: DC Agent (DCA-01..09), Cisco ASA (ASA-01..03), Checkpoint (CKP-01..02), path tracer (PTH-01..03), asymmetric detector (ASY-01..03), path-dependent NET findings, route-change alerting (NFN-02)
- Phase 4: Tier gating (TIR-01, TIR-02) alongside SaaS + Stripe infrastructure
