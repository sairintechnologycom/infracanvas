# Phase 12 Discussion Log

**Date:** 2026-05-17
**Phase:** Path Computation + Asymmetric Routing
**Mode:** Standard discuss (no flags)

## Pre-discussion framing

- Domain: backend-side path computation + asymmetric routing detection over Phase 10 (routes/NetFlow) + Phase 11 (firewall rules/NAT) data.
- Locked from prior phases (not re-asked): `NetworkPath`/`PathHop`/`NetworkFinding` Pydantic models already in `cli/infracanvas/graph/models.py`; `firewall_rules` + `firewall_nat_rules` schema (Phase 11 D-15 "do not rename"); `dc_sites` + site-token auth (Phase 10 D-03/04); existing FlowMap viewer + `PathEdge` dual-color edge component; Slack-alert dispatcher and `teams.slack_webhook_url` (Phase 8); NET-010 reservation test slot (Phase 3-05).
- Pre-question framing: "Compute home" — where does path computation actually run? Selected: **Backend worker (taskiq)**. This locked the architectural shape before gray-area selection.

## Gray areas presented

Multi-select prompt. User selected **all four**:

1. Asymmetry scope & triggers
2. NetFlow correlation strategy (PTH-03)
3. Root cause classifier (ASY-02) + impact (ASY-03)
4. NET-010 form + FMV-02 marker + NFN-02 alerting

## Area 1 — Asymmetry scope & triggers

### Q1: What traffic pairs should Phase 12 compute paths for?
- Options: DC↔Cloud only (Recommended) / DC↔Cloud + Cloud↔Cloud / All three
- **User chose:** DC ↔ Cloud only (hybrid edge)
- Captured: D-02

### Q2: Which traffic pairs do we actually compute?
- Options: Observed pairs from NetFlow top-K (Recommended) / All declared subnet pairs (cartesian) / Both
- **User chose:** Observed pairs from NetFlow (top-K by volume)
- Captured: D-03

### Q3: When does path computation run?
- Options: Scheduled (every 15 min) + on-demand (Recommended) / On every push / On scan upload only
- **User chose:** Scheduled (every 15 min) + on-demand
- Captured: D-04

## Area 2 — NetFlow correlation strategy (PTH-03)

### Q1: How do we decide an observed flow matches a computed path?
- Options: Endpoint + edge-hop match (Recommended) / Strict hop-by-hop / Endpoint-only
- **User chose:** Endpoint + edge-hop match
- Captured: D-05

### Q2: What's the NetFlow time window for matching?
- Options: Rolling 1 hour (Recommended) / Rolling 15 min / Last N samples per pair
- **User chose:** Rolling 1 hour
- Captured: D-06

### Q3: What happens when observed ≠ computed?
- Options: Flag as `path_divergence` finding (separate from asymmetry) (Recommended) / Treat as asymmetry evidence / Informational only
- **User chose:** Flag as `path_divergence` finding (not asymmetry)
- Captured: D-07

## Area 3 — Root cause classifier (ASY-02) + impact (ASY-03)

### Q1: How does the classifier pick a cause when multiple signals overlap?
- Options: Evidence-scored + deterministic tiebreaker (Recommended) / Strict precedence only / Multi-label
- **User chose:** Evidence-scored with deterministic tiebreaker (NAT > LEAK > LOCAL_PREF)
- Captured: D-08

### Q2: What if no cause's evidence threshold fires?
- Options: UNKNOWN with evidence dump (Recommended) / Suppress / Default to BGP_LOCAL_PREF
- **User chose:** Emit `UNKNOWN` with evidence dump
- Captured: D-09

### Q3: How do we score ASY-03 impact?
- Options: Flow-byte volume + affected-firewall count (Recommended) / Affected-firewall count only / Severity tier only
- **User chose:** Flow-byte volume + affected-firewall count
- Captured: D-10

## Area 4 — NET-010 form + FMV-02 marker + NFN-02 alerting

### Q1: How does NET-010 ship?
- Options: Python detector module path-aware (Recommended) / YAML rule with new path-pattern operators / Hybrid
- **User chose:** Python detector module (path-aware)
- Captured: D-11

### Q2: FMV-02 — how do we mark divergence in the FlowMap viewer?
- Options: Dual-edge in PathEdge (forward solid, return dashed-red) (Recommended) / Badge overlay on affected nodes / Toggle forward vs return view
- **User chose:** Dual-edge in PathEdge
- Captured: D-12

### Q3: NFN-02 — how do route-change alerts fire?
- Options: Reuse Phase 8 Slack model + new severity threshold (Recommended) / Dashboard inbox only / Slack + email
- **User chose:** Reuse Phase 8 Slack model + new severity threshold
- Captured: D-13

## Scope creep redirected

None this session — all gray areas stayed inside the Phase 12 boundary defined by REQUIREMENTS Category 12 + 13.

## Claude's Discretion Items (recorded in CONTEXT.md, not re-asked)

- Top-K NetFlow pair selection value (suggest K=200)
- Snapshot retention TTL for `computed_paths` (suggest 14 days)
- Per-cause evidence-rule details (planner research)
- NFN-02 byte-volume threshold default
- Internal Python module layout under `cli/infracanvas/security/network/`
- Dual-strand edge offset / dashed-red styling
- NetFlow raw-vs-rollup data source
- Scheduler jitter for thundering-herd
- Recompute API return shape (202 vs 200)
- On-demand recompute coalescing strategy
- Whether to re-declare Pydantic models in `backend/app/schemas/` or import from `cli/infracanvas/graph/models.py`

## Outcome

- 13 numbered decisions (D-01..D-13) + 3 implicit decisions (D-14 read API shape, D-15 storage tables, D-16 snapshot-per-compute reconciliation) captured in `12-CONTEXT.md`
- Canonical refs catalogued (REQUIREMENTS / ROADMAP / Phase 10 + 11 contracts / viewer / NET-010 reservation sites / Phase 8 alerting / vendor routing references)
- 15 deferred ideas preserved for future phases
- Phase boundary explicit: in-scope (path compute job, asymmetry detector, classifier, NET-010 detector, FMV-02 viewer edits, NFN-02 alert, read API) vs out-of-scope (cloud↔cloud, DC↔DC, dashboard UI, scan-JSON embedding, multi-label, email/inbox channels, push-triggered compute)

## Next step

`/clear` then `/gsd-plan-phase 12`
