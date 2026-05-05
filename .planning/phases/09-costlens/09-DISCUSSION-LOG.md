# Phase 9: CostLens - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-05
**Phase:** 9-costlens
**Areas discussed:** Allocation method, CostLens viewer tab, Dashboard panel (CLA-06)

---

## Allocation method

### Q1: How to split shared resource costs

| Option | Description | Selected |
|--------|-------------|----------|
| Equal split | Divide cost evenly by number of attached workloads from Terraform graph | ✓ |
| Tag-weighted | Each workload tag carries a weight (e.g., prod=60%, dev=40%) | |
| You decide | Claude picks the approach that fits best | |

**User's choice:** Equal split

---

### Q2: Workload tag key

| Option | Description | Selected |
|--------|-------------|----------|
| tags.Service | Most common AWS/Azure tagging convention | |
| tags.Team | Group by team ownership | |
| tags.App | Group by application name | |
| Configurable | User sets tag key in infracanvas.yaml | ✓ |

**User's choice:** Configurable via `costlens.workload_tag_key` in `infracanvas.yaml`

---

### Q3: Untagged resources

| Option | Description | Selected |
|--------|-------------|----------|
| Bucket as 'untagged' | Collect into synthetic 'untagged' workload, receives equal share | ✓ |
| Exclude from split | Don't allocate — share goes to 'unallocated' bucket | |
| Use resource type | Fall back to resource type string as workload name | |

**User's choice:** Bucket as 'untagged' (receives full equal share, not silently dropped)

---

## CostLens viewer tab

### Q1: Layout organization

| Option | Description | Selected |
|--------|-------------|----------|
| Workload view | Each workload card: total cost + breakdown of shared contributions | ✓ |
| Shared resource view | Each shared resource card: how its cost is split among workloads | |
| Both views, tabbed | Two sub-tabs inside CostLens | |

**User's choice:** Workload view (confirmed mockup with payment-svc/auth-svc/untagged cards)

---

### Q2: Idle/oversized recommendations placement

| Option | Description | Selected |
|--------|-------------|----------|
| Bottom section of tab | Recommendations below workload cards, same scroll context | ✓ |
| Badge on workload cards | Warning badge per card, inline expansion | |
| Separate 'Recommendations' sub-header | Collapsible block at top of tab | |

**User's choice:** Bottom section of the CostLens tab

---

### Q3: Idle/oversized detection basis

| Option | Description | Selected |
|--------|-------------|----------|
| Static Terraform heuristics | NAT GW with 0 attachments, TGW with no routes, etc. | ✓ |
| Tag-based heuristics | dev/test/staging resources flagged for scheduled shutdown | |
| Both | Combine topology + tag-based checks | |

**User's choice:** Static Terraform heuristics only (no CloudWatch metrics required)

---

## Dashboard panel (CLA-06)

### Q1: Placement in SaaS dashboard

| Option | Description | Selected |
|--------|-------------|----------|
| Scan detail page — new 'Cost' tab | Native React tab alongside Viewer on scan detail page | ✓ |
| New /costlens route | Top-level route, cross-scan aggregation | |
| CLA-06 = viewer tab only | No separate SaaS surface for Phase 9 | |

**User's choice:** New 'Cost' tab on `app/(dashboard)/scans/[id]/page.tsx`

---

### Q2: Data source

| Option | Description | Selected |
|--------|-------------|----------|
| Extend scan JSON (CLI writes costlens block) | CLI pre-computes, dashboard reads from R2 | ✓ |
| Compute client-side | Dashboard runs allocation logic in browser | |
| New backend endpoint /v1/scans/{id}/costlens | Backend computes on-demand | |

**User's choice:** CLI extends scan JSON with `costlens` block at scan time; dashboard reads from R2

---

## Claude's Discretion

- **CPC-01/03:** Topology-based per-path data transfer cost estimation using static egress rate tables. CPC-03 cost-aware path ranking in FlowMap PathDetailPanel. No flow logs needed.
- **CPC-02:** Deferred to Phase 12 (DC Agent + NetFlow required).

## Deferred Ideas

- CPC-02 (flow-log attribution) — Phase 12
- Per-team cost aggregation / `/costlens` route — future phase post-validation
- CloudWatch / Azure Monitor idle detection — needs metrics pipeline
- Tag-based weight configuration — Phase 9 follow-up if requested
