# Phase 12: Path Computation + Asymmetric Routing — Research

**Researched:** 2026-05-17
**Domain:** Backend-side longest-prefix-match path computation, NetFlow correlation, evidence-scored root-cause classification, dual-strand FlowMap rendering, Slack alert reuse
**Confidence:** HIGH (Phase 10/11 integration verified by reading actual code; vendor-neutral routing concepts cross-verified; one blocker found and surfaced)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Compute location (PTH-01..03, ASY-01..03)**
- **D-01:** Path computation runs **backend-side as a taskiq worker job**. Job reads the latest `firewall_ruleset_snapshots` per device (Phase 11 D-15 contract), the latest route push per site (Phase 10), and the most recent NetFlow window from the existing flow tables. CLI/dashboard read paths via the new backend API; no path computation in `infracanvas scan`.

**Asymmetry scope (PTH-01..03)**
- **D-02:** Phase 12 only computes **DC ↔ Cloud** paths (hybrid edge). Cloud↔Cloud (TGW/ER cross-cloud) and DC↔DC are deferred.

**Pair selection (PTH-03 driver)**
- **D-03:** Pairs are selected from **observed NetFlow, top-K by byte volume** over the last 1h window. K is planner-tunable (suggest K=200 default, env-overridable).

**Recompute trigger**
- **D-04:** A **scheduled taskiq job runs every 15 minutes** per active DC site, plus an on-demand `POST /v1/sites/{site_id}/paths/recompute` endpoint (Clerk JWT, owner role, idempotent — coalesces concurrent calls). Route-push and firewall-push events do NOT directly trigger recomputation.

**NetFlow correlation (PTH-03)**
- **D-05:** Correlation is **endpoint + edge-hop match**: an observed flow matches a computed path iff (a) the flow's src/dst IPs fall inside the path's src/dst CIDRs, AND (b) the first hop's ingress interface and the last hop's egress interface match the observed flow's exporter/interface metadata. Mid-path hops are trusted from routing data.
- **D-06:** Correlation uses a **rolling 1-hour NetFlow window**. Flow samples older than 1h are not considered.
- **D-07:** When observed flow ≠ computed path, emit a **`path_divergence`** finding (a distinct kind from `asymmetry_finding`). Both kinds surface in the FlowMap viewer, with different colors and copy.

**Root cause classifier (ASY-02)**
- **D-08:** Classifier is **evidence-scored with a deterministic tiebreaker**. Each cause (BGP_LOCAL_PREF, ROUTE_LEAK, NAT_ASYMMETRY) gets a 0–1 confidence from its own evidence rules. Highest confidence wins. On tie, fixed precedence **NAT > LEAK > LOCAL_PREF** (most specific first). All non-winning scores are persisted in `evidence` JSONB for the diagnostic detail panel.
- **D-09:** When no cause clears its evidence threshold, the finding is emitted with cause = **`UNKNOWN`** and the full evidence dump in `evidence`.

**Impact scoring (ASY-03)**
- **D-10:** Impact is **two scalars**: (a) flow-byte volume of affected flows over the last 1h (from NetFlow), and (b) count of distinct stateful firewalls that see only one leg of the asymmetric pair. Viewer sorts asymmetries by `firewall_count DESC, byte_volume DESC`.

**NET-010 activation**
- **D-11:** NET-010 ships as a **Python detector module** under `cli/infracanvas/security/network/` (path-aware), NOT a YAML rule. Catalog count rises from 51 → 52. The reservation test `test_net_010_reserved_for_phase_3b` is updated to assert the detector exists and emits `NET-010` findings under the rule-id contract. **Source:** `cli/tests/test_flowmap_network_rules.py:71` and `cli/tests/test_security.py:64`.

**FMV-02 — Path divergence marker in viewer**
- **D-12:** FMV-02 is implemented as **dual-edge rendering in the existing `PathEdge` component**: forward leg as a solid stroke (existing color), return leg as a parallel stroke offset slightly. Asymmetric segments get a **red dashed** style on the affected leg. `PathDetailPanel` adds a side-by-side forward/return hop table when an asymmetric path is selected.

**NFN-02 — Route change / asymmetry alerting**
- **D-13:** NFN-02 alerts reuse the **Phase 8 Slack dispatcher** (`teams.slack_webhook_url` + the Phase 8 alert job). Phase 12 adds a new severity threshold: fire when **(impact byte-volume > planner-tunable bytes/s threshold)** OR **(affected stateful-firewall count ≥ 1)**.

**Read API (D-14), Storage model (D-15), Snapshot semantics (D-16)** — See CONTEXT.md verbatim.

### Claude's Discretion
- Top-K NetFlow pair selection value (suggest K=200, env-overridable)
- Snapshot retention TTL for `computed_paths` (suggest 14 days, mirror Phase 11 firewall snapshots)
- Per-cause evidence-rule details (BGP attrs → LOCAL_PREF, route-leak fingerprint, NAT mismatch shapes) — researched below
- NFN-02 byte-volume threshold default + override surface (env var first, per-team in a later phase)
- Internal Python module layout under `cli/infracanvas/security/network/` (one module vs split detector/engine)
- Exact dual-strand edge offset / red dashed stroke styling in `PathEdge`
- Whether NetFlow window math runs against raw flow records or a pre-aggregated rollup table — researched below
- Backoff/jitter on the 15-min scheduler tick to avoid thundering-herd across many sites
- Whether `POST /v1/sites/{site_id}/paths/recompute` returns 202 + job_id or 200 + result
- Coalescing strategy for concurrent on-demand recomputes (per-site lock vs queue dedup)
- Whether to re-declare Pydantic models in `backend/app/schemas/` or import from `cli/infracanvas/graph/models.py`

### Deferred Ideas (OUT OF SCOPE)
- Cloud↔Cloud paths (TGW peering, ExpressRoute cross-cloud)
- DC↔DC intra-site paths
- Cartesian path computation over all declared subnet pairs
- Embedding computed paths into the scan JSON `ResourceGraph.network_paths` field
- Multi-label root cause classification
- Email or in-app inbox alert channels for NFN-02
- Path-pattern operators in the YAML rule engine
- Real-time recomputation on every route/firewall push
- Per-team NFN-02 byte-volume threshold setting
- Dashboard UI for browsing asymmetries (read API only in this phase)
- Diff-based snapshot storage for `computed_paths`
- Auto-recovery / self-healing suggestions
- Cause precedence override per-team
- Cross-pair correlation rollups
- Pinning a specific NetFlow rollup table vs raw flow records
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PTH-01 | Forward-path computation from route + policy data | "Standard Stack" pins `pytricia` for LPM next-hop resolution; "Architecture Patterns" §Path Compute Pipeline lays out router-by-router hop expansion; D-15 `computed_paths` table is the persistence target |
| PTH-02 | Return-path computation | Same pipeline run with src/dst swapped; "Pattern 2: Bidirectional path pair" documents the canonical pairing logic. `NetworkPath.direction = 'return'` already exists in `cli/infracanvas/graph/models.py:147` |
| PTH-03 | NetFlow correlation validating computed paths against observed flows | D-05 endpoint+edge-hop matcher; D-06 1h window; "Architecture Patterns" §NetFlow Correlation defines the match predicate and emits `path_divergence_findings` per D-07 |
| ASY-01 | Asymmetric routing detector — compares forward vs return paths | "Architecture Patterns" §Asymmetry Detection — symmetric-difference of hop-sets is the canonical detector; "Common Pitfalls" §ECMP false-positive surfaces the per-flow-key bucketing requirement |
| ASY-02 | Root-cause classifier (BGP_LOCAL_PREF / ROUTE_LEAK / NAT_ASYMMETRY) | "Code Examples" §Per-cause evidence scoring documents each evidence rule; D-08 evidence-scored with NAT > LEAK > LOCAL_PREF tiebreaker; D-09 UNKNOWN bucket |
| ASY-03 | Impact scoring — flows affected, firewalls that see asymmetric state | D-10: two scalars `impact_bytes_per_sec` + `impact_firewall_count`; "Architecture Patterns" §Impact Scoring defines computation; firewall list joined from `FirewallRulesetSnapshot` latest-per-`firewall_id` |
| NET-010 | Stateful-firewall asymmetry rule (reserved in v1.0, activated in 3b) | D-11: Python detector under `cli/infracanvas/security/network/net_010.py`, NOT a YAML rule. "Common Pitfalls" §NET-010 reservation test flip — change to *positive* assertion; rules-catalog count moves 51 → 52 (`cli/tests/test_security.py:64`) |
| FMV-02 | Path divergence marker in FlowMap viewer | D-12: extend `viewer/src/components/flowmap/edges/PathEdge.tsx` (77 lines today) with red-dashed asymmetric segment; extend `PathDetailPanel.tsx` (289 lines today) with side-by-side hop table; tests live under `viewer/src/__tests__/flowmap/` |
| NFN-02 | Route-change alerting on DC-agent-detected route churn | D-13: reuse `teams.slack_webhook_url` + the Phase 8 dispatcher in `backend/app/queue/tasks/scan_repo.py:299-341`; planner extracts the dispatcher into a shared helper (see "Architecture Patterns" §Alert Reuse) |
</phase_requirements>

## Summary

Phase 12 is a **backend compute + viewer rendering** phase that sits on top of two upstream contracts: Phase 10 site-token agent push (`backend/app/routes/agent.py`) and Phase 11 firewall snapshot tables (`firewall_ruleset_snapshots` / `firewall_rules` / `firewall_nat_rules` / `firewall_objects`). The work breaks into seven concrete deliverables: (1) two new agent ingest persistence layers (routes + flows — see Blocker 1 below); (2) three new backend tables (`computed_paths` + `asymmetry_findings` + `path_divergence_findings`) with RLS mirroring Phase 11 D-08; (3) a scheduled + on-demand taskiq path-compute job; (4) an evidence-scored root-cause classifier with deterministic NAT > LEAK > LOCAL_PREF tiebreaker; (5) one minimal read API (3 endpoints, Clerk JWT, mirroring Phase 11 D-11); (6) a Python NET-010 detector under `cli/infracanvas/security/network/`; (7) FMV-02 dual-strand `PathEdge` + side-by-side `PathDetailPanel` extensions plus NFN-02 Slack alert reuse extracted from `scan_repo.py`.

**The single largest hidden-scope item: Phase 10 routes and flows are NOT persisted today.** `backend/app/routes/agent.py:113` and `:129` log "agent_routes_received" / "agent_flows_received" and discard the body. The handler docstrings carry a stale comment "Phase 10 logs only — Phase 11 persists" but Phase 11 only added firewall tables. There is NO `routes` or `flows` table in any migration through `20260510_011_firewall_tables.py`. **Phase 12 cannot compute paths without first persisting routes + flows.** This must land as the first Wave-1 task (`route_records` + `netflow_records` tables + ingest handler updates) before any path-compute work begins. See "Open Questions" Q1 and "Common Pitfalls" §Routes/Flows persistence gap.

The path-compute algorithm itself is a well-trodden hybrid-network problem: longest-prefix-match next-hop resolution against per-router RIB snapshots, hop expansion until reaching a destination CIDR (or hitting a loop / max-hop limit), then firewall + NAT rule evaluation per-hop using the already-locked Phase 11 column contract (D-15). For LPM, the recommendation is `pytricia 1.3.0` (Patricia/radix trie, Python 3.12 compatible per PyPI Sept 2025 release) — Python's stdlib `ipaddress` lacks LPM and the alternative `py-radix` is in maintenance-only mode. For NetFlow correlation, run against raw `netflow_records` (the new table) with a `(src_ip, dst_ip, src_port, dst_port, protocol)` 5-tuple composite index and a `WHERE collected_at > NOW() - INTERVAL '1 hour'` predicate. A rollup table is not justified at v1.1 volumes.

Classifier evidence rules are domain-specific but defensible: **BGP_LOCAL_PREF** fires when forward and return next-hops resolve through routers with mismatched LOCAL_PREF values on the same prefix or when `as_path` arrays differ between legs (Phase 10 `RouteRecord.as_path` already carries this — `backend/app/schemas/agent.py:40`); **ROUTE_LEAK** fires on either a more-specific prefix advertised by an unexpected peer or an `as_path` containing an upstream that shouldn't originate the prefix; **NAT_ASYMMETRY** fires when the forward path transits a NAT rule whose return-side translation pinhole doesn't exist in `firewall_nat_rules` (matched via `src_translation` / `dst_translation` / `interface_in` / `interface_out`). These match the published vendor-neutral guidance from Cisco, Palo Alto, pfSense and Checkpoint troubleshooting docs.

**Primary recommendation:** Decompose Phase 12 into 5 waves: **Wave 0** failing-test scaffold + Nyquist fixtures; **Wave 1** routes/flows persistence (the unblocker) + new path/asymmetry tables + Pydantic schemas + 14-day prune job mirroring `firewall_prune.py`; **Wave 2** (parallel) backend read API + Slack dispatcher extraction; **Wave 3** path-compute job + classifier + impact scoring + NET-010 detector; **Wave 4** viewer FMV-02 + NFN-02 wiring + 15-min taskiq schedule registration; **Wave 5** governance (CAB packet update if security posture changes) + final smoke.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Agent push of routes/flows | API / Backend (FastAPI ingest) | DC Agent (already shipped) | Phase 10 ingest endpoints exist but currently log-only; Phase 12 adds persistence. Agent unchanged. |
| Route/flow storage | Database / Storage (Postgres) | — | New `route_records` + `netflow_records` tables with RLS via `team_id` (Pattern C). |
| Path computation | API / Backend (taskiq worker) | — | Locked by D-01. NOT in CLI/scan. NOT push-triggered (D-04). |
| LPM next-hop resolution | API / Backend (in-memory per job) | — | `pytricia` trie built per recompute from the latest route snapshot — no separate service. |
| NetFlow correlation | API / Backend (taskiq worker) | Database / Storage (rolling 1h SELECT) | Runs in the same job as path compute; reads from `netflow_records`. |
| Root-cause classification | API / Backend (pure Python module) | — | Pure function: takes `(forward, return, firewall_rules, nat_rules, route_snapshot) → (cause, confidence, evidence)`. Easy to unit-test. |
| Impact scoring | API / Backend (same job) | Database / Storage (JOIN against `firewall_ruleset_snapshots`) | Bytes/sec from NetFlow window; firewall count from latest firewall snapshot per device. |
| Findings persistence + reconciliation | Database / Storage | API / Backend (worker reconciles) | D-16: full-replace `computed_paths`; reconcile findings with `first_seen_at` / `last_seen_at` / `resolved_at`. |
| Read API for paths/asymmetries | API / Backend (FastAPI Clerk-authed) | — | Mirrors Phase 11 D-11 read API verbatim (Pattern B). |
| FlowMap dual-strand rendering | Browser / Client (React + @xyflow/react 12) | Frontend Server (none — single HTML bundle) | Extends existing `PathEdge.tsx` (already dual-color). |
| Side-by-side hop table | Browser / Client (React) | — | New tab/section in `PathDetailPanel.tsx`. |
| Slack alert delivery | API / Backend (httpx POST) | External: Slack incoming webhook | Reuses Phase 8 dispatcher pattern; planner extracts it from `scan_repo.py` to `app/notifications/slack.py`. |
| Alert evaluation (threshold + transition detection) | API / Backend (same compute job) | — | Decides whether to fire based on D-13 thresholds + reconciliation delta. |

## Standard Stack

### Core (Backend Python)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.115.x (existing) | Read API endpoints | Phase 6+ standard; mirrors `backend/app/routes/firewalls.py` |
| SQLAlchemy + asyncpg | 2.0.36 / 0.30.0 (existing) | ORM + async Postgres driver | Existing posture; Pattern B (Clerk JWT + RLS GUC) is the read-side template |
| taskiq + taskiq-redis | 0.11.x / 1.0.x (existing) | Scheduled + on-demand worker jobs | Already running for `scan_repo`, `firewall_prune`, `indexing`. `@broker.task(schedule=[{"cron": "*/15 * * * *"}])` is the documented Taskiq scheduler API [CITED: taskiq-python.github.io/guide/scheduling-tasks.html] |
| pytricia | 1.3.0 | Patricia/radix trie for IP longest-prefix-match | Patricia tree is the canonical RIB lookup data structure [CITED: github.com/jsommers/pytricia]; Python 3.12 wheels published Sept 2025 [VERIFIED: pypi.org/project/pytricia/1.3.0]; pure Python alternative `py-radix` is in maintenance-only |
| ipaddress (stdlib) | 3.12 builtin | CIDR parsing + IP-in-network membership | Used by `pytricia` and for src/dst CIDR validation; no LPM in stdlib |
| Pydantic | 2.7.1 (existing) | Schemas + path/finding models | Already used backend-side; reuse `NetworkPath` / `PathHop` from `cli/infracanvas/graph/models.py:125-150` |
| structlog | 24.4.x (existing) | Structured logging | Mirrors Phase 11 `_log = structlog.get_logger("app.firewalls")` |
| httpx | 0.27.x (existing) | Slack webhook POST (NFN-02) | Already used by Phase 8 Slack dispatcher in `scan_repo.py:324-336` |
| Alembic | 1.14.x (existing) | New migrations (`012_path_compute_tables`, `013_route_flow_tables` — planner picks numbering) | Mirrors migration `20260510_011_firewall_tables.py` structure |

### Core (Viewer)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| @xyflow/react | 12.6.0 (existing) | Edge + node rendering | `PathEdge.tsx` already uses `BaseEdge` + `getSmoothStepPath`; extension is additive |
| React | 18.3.1 (existing) | UI framework | Existing |
| Zustand | 5.0.5 (existing) | Store for selected path + asymmetry findings | `viewer/src/store.ts` already singleton |
| Vitest | 4.1.4 (existing) | Unit tests for PathEdge / PathDetailPanel | Existing test patterns under `viewer/src/__tests__/flowmap/` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest-asyncio | 0.24.x (existing) | Async-aware test fixtures for taskiq jobs | All path-compute job tests |
| hypothesis | n/a (planner picks) | Property-based path-compute tests | OPTIONAL — research suggests adding for path-compute correctness over fuzzed topologies (see "Code Examples" §Property test pattern). Skipped if planner prefers golden-file only. |
| pytest-httpx / respx | 0.21.x (existing) | Mock Slack webhook for NFN-02 tests | Reuse existing pattern; `respx` already in `backend/pyproject.toml` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `pytricia` | `py-radix` | py-radix maintenance-only; pytricia has recent 2025 releases. Both work; pytricia is the safer pick. |
| `pytricia` | Hand-rolled trie | Building a Patricia trie is a 200-line project with subtle off-by-one bugs around prefix-length collisions. Don't. |
| `pytricia` | Pure `ipaddress.ip_network(...).supernet_of(...)` linear scan | O(n) per lookup × hundreds of routes × thousands of flows = too slow for the 15-min compute cadence. Trie is O(log n). |
| Multi-label classifier (D-08 alternative) | Strict precedence only | D-08 picks evidence-scored to preserve diagnostic richness in `evidence` JSONB. Strict precedence loses the non-winning scores. |
| New ingest endpoints for routes/flows | Extend `POST /v1/agent/routes` + `POST /v1/agent/flows` (already exist) | Existing endpoints just need persistence wired up. No new routes — see Blocker 1. |
| Postgres-side scheduled `DELETE` for snapshot prune | taskiq periodic | Phase 11 already chose taskiq for `firewall_prune` (precedent). Mirror it for `computed_paths` and `*_findings` TTL. |

**Installation:**

```bash
# Backend
cd backend && pip install pytricia==1.3.0
# pytricia adds compiled C extension; ensure Docker base image has build-essential
# (CLI Python 3.12-slim base already includes gcc per CLAUDE.md)

# No new viewer deps — all extensions land in existing @xyflow/react surface
```

**Version verification:**

```bash
$ python -c "import pytricia; print(pytricia.__version__)"  # expect 1.3.0
# PyPI release Sept 2025 [VERIFIED via web search 2026-05-17]
```

## Architecture Patterns

### System Architecture Diagram

```
                ┌────────────────────────────────────────────────────────────┐
                │                  DC Agent (existing, Phase 10/11)          │
                │  NETCONF/SSH routes  •  NetFlow v9/IPFIX UDP  •  Firewalls │
                └─────────────────────┬──────────────────────────────────────┘
                                      │ Bearer site_token (Pattern A)
                                      │ POST /v1/agent/routes
                                      │ POST /v1/agent/flows
                                      │ POST /v1/agent/firewall-{rules,nat,objects}  (Phase 11 — DONE)
                                      ▼
                ┌────────────────────────────────────────────────────────────┐
                │                      FastAPI Ingest                         │
                │  ╭──────────────────────────────────────────────────────╮   │
                │  │ NEW: persist routes → route_records                  │   │
                │  │ NEW: persist flows  → netflow_records                │   │  ← Phase 12 Wave 1
                │  ╰──────────────────────────────────────────────────────╯   │
                │  Existing: firewall_ruleset_snapshots + children            │
                └─────────────────────┬──────────────────────────────────────┘
                                      │ INSERT (RLS-scoped via site_token.team_id)
                                      ▼
                ┌────────────────────────────────────────────────────────────┐
                │                  Postgres (Neon, team-RLS)                  │
                │  route_records  •  netflow_records  •  firewall_*           │
                │  computed_paths • asymmetry_findings • path_divergence      │ ← Phase 12 D-15
                │           (all FORCE ROW LEVEL SECURITY)                    │
                └──────┬────────────────────────────────────┬─────────────────┘
                       │ SELECT latest per (site,firewall)  │ INSERT/UPDATE on reconcile
                       │ SELECT route snapshot per site     │
                       │ SELECT flows WHERE collected_at>−1h│
                       ▼                                    ▼
        ┌─────────────────────────────────────────────────────────────────┐
        │   taskiq worker:  recompute_paths_for_site (every 15 min + on-demand)
        │   ┌──────────────────┐   ┌──────────────────┐   ┌────────────────┐
        │   │ Build pytricia   │──▶│ Hop-by-hop       │──▶│ NetFlow        │
        │   │ trie per router  │   │ forward + return │   │ correlator     │
        │   │ (LPM)            │   │ path expansion   │   │ (1h window)    │
        │   └──────────────────┘   └────────┬─────────┘   └───────┬────────┘
        │                                    │                     │
        │   ┌────────────────────────────────┴─────────────────────┘
        │   ▼
        │   ┌──────────────────────────┐     ┌──────────────────────────┐
        │   │ Asymmetry detector       │────▶│ Root-cause classifier    │
        │   │ (hop-set symmetric diff) │     │ NAT > LEAK > LOCAL_PREF  │
        │   └──────────────────────────┘     └──────────┬───────────────┘
        │                                                │
        │   ┌────────────────────────────────────────────┴─────────────┐
        │   ▼                                                          ▼
        │   ┌──────────────────────┐     ┌──────────────────────────────┐
        │   │ Impact scoring       │     │ NET-010 Python detector       │
        │   │ (bytes/s + fw count) │     │ → NetworkFinding rule_id=...  │
        │   └──────────┬───────────┘     └──────────────────────────────┘
        │              │
        │              ▼
        │   ┌──────────────────────────────────────────────────────┐
        │   │ Findings reconciliation                              │
        │   │ - INSERT new                                         │
        │   │ - UPDATE last_seen_at on still-present               │
        │   │ - SET resolved_at on no-longer-present               │
        │   └────────┬─────────────────────────────────────────────┘
        │            │ if (new OR cause-changed)
        │            ▼
        │   ┌──────────────────────────────────────────────────────┐
        │   │ Slack dispatcher (NFN-02; reused Phase 8 helper)     │
        │   │ POST teams.slack_webhook_url                         │
        │   └──────────────────────────────────────────────────────┘
        └──────────────────────────────────────────────────────────────┘
                       │
                       │ GET /v1/sites/{site_id}/paths        (Clerk JWT)
                       │ GET /v1/sites/{site_id}/asymmetries  (Clerk JWT)
                       │ POST /v1/sites/{site_id}/paths/recompute (owner role)
                       ▼
                ┌──────────────────────────────────────┐
                │       FastAPI Read API               │
                │  Pattern B — RLS GUC set per tx      │
                │  Site-membership probe FIRST → 404   │
                └─────────────┬────────────────────────┘
                              │ JSON
                              ▼
                ┌──────────────────────────────────────────────────────────┐
                │              Dashboard / Viewer (Next.js + React)         │
                │  Zustand store hydrates network_paths from API           │
                │  PathEdge.tsx → dual-strand (asymmetric leg: dashed red) │
                │  PathDetailPanel.tsx → side-by-side hop table            │
                └──────────────────────────────────────────────────────────┘
```

### Recommended Project Structure

```
backend/
├── migrations/versions/
│   ├── 20260518_012_route_flow_tables.py        # NEW — Blocker 1 fix
│   └── 20260518_013_path_compute_tables.py      # NEW — D-15 tables
├── app/
│   ├── db/models.py                              # +RouteRecordORM, +NetFlowRecordORM,
│   │                                             # +ComputedPathORM, +AsymmetryFindingORM,
│   │                                             # +PathDivergenceFindingORM
│   ├── schemas/
│   │   ├── agent.py                              # existing; no shape change (or extend if
│   │   │                                         # planner adds collected_at_ns precision)
│   │   └── paths.py                              # NEW — read API response models
│   ├── routes/
│   │   ├── agent.py                              # EXTEND push_routes + push_flows to persist
│   │   └── paths.py                              # NEW — read API + POST /paths/recompute
│   ├── notifications/
│   │   └── slack.py                              # NEW — extracted from scan_repo.py:299-341
│   ├── security/
│   │   ├── pathcompute/                          # NEW — pure compute, no I/O
│   │   │   ├── __init__.py
│   │   │   ├── lpm.py                            # pytricia wrapper
│   │   │   ├── forward.py                        # hop expansion
│   │   │   ├── pair.py                           # bidirectional pair builder
│   │   │   ├── correlate.py                      # NetFlow correlation (D-05/06)
│   │   │   ├── asymmetry.py                      # hop-set symmetric diff (ASY-01)
│   │   │   ├── classify.py                       # evidence-scored classifier (ASY-02, D-08/09)
│   │   │   └── impact.py                         # bytes/s + firewall count (ASY-03, D-10)
│   └── queue/tasks/
│       ├── path_compute.py                       # NEW — scheduled + on-demand job
│       └── path_compute_prune.py                 # NEW — TTL prune mirroring firewall_prune.py

cli/
├── infracanvas/security/network/                 # NEW package — Python network detectors
│   ├── __init__.py
│   └── net_010.py                                # NET-010 detector (D-11)
└── tests/
    ├── test_flowmap_network_rules.py             # UPDATE test_net_010_reserved_for_phase_3b
    │                                              # → assert NET-010 IS now active
    └── test_security.py                          # UPDATE catalog count 51 → 52

viewer/
├── src/components/flowmap/
│   ├── edges/PathEdge.tsx                        # EXTEND — red dashed asymmetric segments
│   └── PathDetailPanel.tsx                       # EXTEND — side-by-side hop table tab
└── src/__tests__/flowmap/
    ├── PathEdge.test.tsx                         # EXTEND — asymmetric render assertion
    └── PathDetailPanel.test.tsx                  # EXTEND — side-by-side table assertion
```

### Pattern 1: Backend-side compute job (mirroring `firewall_prune.py`)

**What:** A taskiq `@broker.task` that runs both on a schedule and on-demand.
**When to use:** Every Phase 12 backend computation (path compute, prune).
**Example:**

```python
# backend/app/queue/tasks/path_compute.py
from __future__ import annotations

import os
from uuid import UUID

import structlog
from sqlalchemy import text
from app.db.session import get_sessionmaker
from app.queue.broker import broker

_log = structlog.get_logger("app.tasks.path_compute")
_K_DEFAULT = int(os.environ.get("PATH_COMPUTE_TOP_K", "200"))


@broker.task(
    task_name="recompute_paths_all_sites",
    schedule=[{"cron": "*/15 * * * *"}],   # D-04 — every 15 min
)
async def recompute_paths_all_sites() -> dict[str, int]:
    """Fan out to one job per active DC site (Pattern B RLS-set per team)."""
    sm = get_sessionmaker()
    enqueued = 0
    async with sm() as session:
        team_rows = (await session.execute(text("SELECT id FROM teams"))).all()
        for (team_id,) in team_rows:
            # Walk each team's sites under that team's RLS context
            async with session.begin():
                await session.execute(
                    text("SELECT set_config('app.current_team_id', :t, true)"),
                    {"t": str(team_id)},
                )
                site_rows = (
                    await session.execute(text("SELECT id FROM dc_sites"))
                ).all()
            for (site_id,) in site_rows:
                await recompute_paths_for_site.kiq(site_id=site_id)
                enqueued += 1
    _log.info("path_recompute_fanout", sites=enqueued)
    return {"enqueued": enqueued}


@broker.task(task_name="recompute_paths_for_site")
async def recompute_paths_for_site(
    site_id: UUID, *, on_demand: bool = False
) -> dict[str, int]:
    """Compute forward+return for top-K NetFlow pairs in this site."""
    ...
```

**Why:** Pattern matches `firewall_prune.py` task shape, including team-walk + RLS GUC set + structured logging. Taskiq cron scheduling is documented and stable [CITED: taskiq-python.github.io/guide/scheduling-tasks.html].

### Pattern 2: Bidirectional path pair

**What:** Always compute forward and return in lockstep; persist as two `computed_paths` rows linked via `(pair_src_cidr, pair_dst_cidr, computed_at)`.
**Why:** Asymmetry detection compares two paths — there is no "asymmetry of one." Always pair, then diff.

```python
def compute_pair(src: str, dst: str, snapshot) -> tuple[NetworkPath, NetworkPath]:
    forward = compute_forward(src, dst, snapshot)
    ret = compute_forward(dst, src, snapshot)  # same compute, swapped args
    ret.direction = "return"
    return forward, ret
```

### Pattern 3: NetFlow correlation (D-05 endpoint + edge-hop)

**What:** A flow F matches a path P iff:
1. `ip_in_cidr(F.src_ip, P.src_cidr)` AND `ip_in_cidr(F.dst_ip, P.dst_cidr)`
2. `F.exporter_interface == P.hops[0].interface_in` (first-hop edge match)
3. `F.exit_interface == P.hops[-1].interface_out` (last-hop edge match)

Mid-path hops are trusted from routing data — NetFlow exporter coverage is sparse in hybrid environments [VERIFIED: vendor troubleshooting docs — pfSense, Palo Alto, Checkpoint].

```python
def matches(flow: FlowRecord, path: NetworkPath) -> bool:
    if not _in_cidr(flow.src_ip, path.evidence.get("src_cidr", "0.0.0.0/0")):
        return False
    if not _in_cidr(flow.dst_ip, path.evidence.get("dst_cidr", "0.0.0.0/0")):
        return False
    first, last = path.hops[0], path.hops[-1]
    return (
        flow.exporter_interface == first.interface_in
        and flow.exit_interface == last.interface_out
    )
```

> **Note:** The current `FlowRecord` Pydantic schema (`backend/app/schemas/agent.py:56-65`) does NOT include `exporter_interface` or `exit_interface`. Planner must extend the schema AND the agent push payload (Phase 10 contract) to carry these. See "Open Questions" Q2.

### Pattern 4: Asymmetry detection (hop-set symmetric difference)

**What:** Given forward and return paths over a pair, compute the set of routers/firewalls each leg traverses; symmetric difference > 0 → asymmetric.
**When:** Per pair, per recompute.

```python
def is_asymmetric(forward: NetworkPath, ret: NetworkPath) -> bool:
    fwd_nodes = {h.node_id for h in forward.hops}
    ret_nodes = {h.node_id for h in ret.hops}
    return (fwd_nodes ^ ret_nodes) != set()  # symmetric difference
```

> **ECMP caveat:** Per-packet or per-flow ECMP load balancing can yield naturally asymmetric paths that operators don't care about. The path-compute should resolve ECMP next-hops deterministically (pick the lexicographically lowest next-hop, mirroring `vty show ip route` first-line behavior) so a flapping ECMP hash doesn't generate spurious asymmetries [VERIFIED: Cisco/Noction asymmetric-routing guidance].

### Pattern 5: Evidence-scored classifier (D-08)

**What:** Each cause computes its own 0–1 confidence from a fixed set of signals; highest wins; on tie, fixed precedence `NAT > LEAK > LOCAL_PREF`; on no cause >= threshold, emit `UNKNOWN`.

```python
def classify(
    forward: NetworkPath, ret: NetworkPath,
    forward_routes: list[RouteRecord], ret_routes: list[RouteRecord],
    nat_rules: list[FirewallNATRule],
) -> tuple[str, float, dict]:
    scores = {
        "NAT_ASYMMETRY":  score_nat(forward, ret, nat_rules),
        "ROUTE_LEAK":     score_leak(forward_routes, ret_routes),
        "BGP_LOCAL_PREF": score_local_pref(forward_routes, ret_routes),
    }
    threshold = 0.4  # planner-tunable
    candidates = {k: v for k, v in scores.items() if v >= threshold}
    if not candidates:
        return ("UNKNOWN", 0.0, {"scores": scores})
    # tiebreaker: NAT > LEAK > LOCAL_PREF
    precedence = {"NAT_ASYMMETRY": 0, "ROUTE_LEAK": 1, "BGP_LOCAL_PREF": 2}
    winner = sorted(
        candidates.items(),
        key=lambda kv: (-kv[1], precedence[kv[0]]),
    )[0]
    return (winner[0], winner[1], {"scores": scores})
```

### Pattern 6: NFN-02 alert reuse — extract Slack dispatcher

**Where the Slack dispatcher lives today:** Inline at `backend/app/queue/tasks/scan_repo.py:299-341` — fetches `teams.slack_webhook_url`, builds a static message, POSTs with httpx, swallows exceptions, captures to Sentry.
**Why extract it:** Phase 12 fires alerts from a DIFFERENT task (`path_compute.py`) with a DIFFERENT message template. Two callers with one helper > two inline copies. Planner ships:

```python
# backend/app/notifications/slack.py — NEW MODULE
import httpx
import sentry_sdk
import structlog
from sqlalchemy import text
from app.db.session import get_sessionmaker

_log = structlog.get_logger("app.notifications.slack")

async def send_team_slack(*, team_id: str, message: str, log_ctx_key: str) -> None:
    """Look up team's slack_webhook_url, POST message; swallow + Sentry-capture."""
    sm = get_sessionmaker()
    async with sm() as session, session.begin():
        await session.execute(
            text("SELECT set_config('app.current_team_id', :t, true)"),
            {"t": team_id},
        )
        row = (await session.execute(
            text("SELECT slack_webhook_url FROM teams WHERE id = :id"),
            {"id": team_id},
        )).one_or_none()
    if row is None or row.slack_webhook_url is None:
        return
    try:
        async with httpx.AsyncClient() as client:
            await client.post(row.slack_webhook_url, json={"text": message}, timeout=5.0)
        _log.info(f"{log_ctx_key}.slack_alert_sent")
    except Exception as exc:
        _log.warning(f"{log_ctx_key}.slack_alert_failed", error=repr(exc))
        sentry_sdk.capture_exception(exc)
```

Then `scan_repo.py:299-341` collapses to a one-liner call; `path_compute.py` calls the same helper.

### Pattern 7: Site-membership probe FIRST in read API (Phase 11 D-11 mirror)

For every Phase 12 read endpoint, probe `DCSite` existence under RLS BEFORE doing the real query — cross-team site_id → 404, not 403, to avoid leaking site existence. This is verbatim from `firewalls.py:109-119`.

### Anti-Patterns to Avoid

- **Building a hand-rolled trie.** `pytricia` is 80kb of C, fast, and correct. Don't reimplement.
- **Per-route ON CONFLICT chasing.** `route_records` should be **snapshot-per-pull, full-replace per `(site_id, device_host, collected_at)`** — same pattern as Phase 11 D-10. Trying to incrementally diff routes is a rabbit hole.
- **Persisting raw NetFlow forever.** TTL the `netflow_records` table aggressively (suggest 24h or 48h, NOT 14 days like firewall snapshots — flow volume is orders of magnitude larger). Planner picks; document the rationale.
- **Triggering recompute on every agent push.** D-04 explicitly forbids this — would thrash the worker during BGP flaps. Stay on 15-min cadence.
- **Storing a single `cause` column without `evidence` JSONB.** D-08 says all non-winning scores live in `evidence` for the diagnostic panel. Don't drop them.
- **Embedding the Slack message format inline in `path_compute.py`.** Use the extracted helper (Pattern 6); pass a pre-built message string.
- **Conflating `asymmetry_findings` and `path_divergence_findings`.** D-07 explicitly separates them. They render differently and the classifier treats them as different evidence inputs.
- **Per-collector retry logic.** Pattern F (Phase 11 PATTERNS.md line 846) — don't reinvent.
- **Re-implementing site_token validation.** Pattern A — `require_site_token` already exists in `backend/app/auth/site_token.py`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Longest-prefix-match | Linear `for net in routes: if ip in net` | `pytricia` Patricia trie | O(log n) vs O(n); n grows with RIB size (potentially 100k+ prefixes per router) |
| Route persistence | Diff-and-merge logic | Snapshot-per-pull (Phase 11 D-10 pattern) | Already proven; storage cost manageable with TTL prune |
| TTL prune | New cron container | `taskiq` periodic task mirroring `firewall_prune.py` | Same broker, same logger, same Pattern B RLS walk |
| RLS team isolation | Bespoke filter clauses | Pattern C `ENABLE + FORCE + policy on team_id` | Phase 10/11 verified; FORCE catches future BYPASSRLS regressions |
| Slack delivery | New webhook client | Phase 8 dispatcher pattern, extracted to `app/notifications/slack.py` | One source of truth; same error handling + Sentry capture |
| Pydantic models | Re-declare from scratch | Re-export or import `NetworkPath` / `PathHop` from `cli/infracanvas/graph/models.py:125-150` | Already shaped for this phase; `direction` field already exists |
| Bearer site-token auth | Re-implement | Pattern A `require_site_token` from `backend/app/auth/site_token.py` | Already tested + RLS-aware |
| Cron scheduling | External cron container | `@broker.task(schedule=[{"cron": ...}])` | Native taskiq feature [CITED: taskiq-python.github.io] |
| Path-aware YAML rule operators | New rule engine ops | NET-010 as Python detector (D-11) | One rule does not justify path-pattern operators in the engine |
| Dual-edge React component | New edge type | Extend existing `PathEdge.tsx` | Already supports `direction: 'forward' \| 'return' \| 'both'` |

**Key insight:** Phase 12 is a "compose existing primitives" phase, not a greenfield one. The risk is in coupling correctness (right column names from Phase 11 D-15, right auth pattern, right RLS GUC sequencing), not in building new abstractions.

## Common Pitfalls

### Pitfall 1: Routes/flows persistence gap (BLOCKER 1)

**What goes wrong:** Phase 12 plan assumes Phase 10 routes/flows are persisted in `route_records` / `netflow_records` tables. They are NOT.
**Root cause:** `backend/app/routes/agent.py:113,129` carries the comment "Phase 10 logs only — Phase 11 persists" but Phase 11 only added firewall tables. There is no `routes` or `flows` create_table in any migration through `011_firewall_tables`.
**Evidence:**
```bash
$ grep -rn "create_table" backend/migrations/versions/*.py | grep -iE "route|flow"
# (no output — confirms tables don't exist)
$ grep -n "class.*Route\|class.*Flow" backend/app/db/models.py
# (no Route/Flow ORM classes)
```
**How to avoid:** First Wave-1 task MUST be a migration adding `route_records` + `netflow_records` tables + ORM models + updates to `push_routes` / `push_flows` handlers to actually persist. Without this, the path-compute job has no inputs.
**Suggested table shape (planner refines):**
```sql
CREATE TABLE route_records (
  record_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  team_id       UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
  site_id       UUID NOT NULL REFERENCES dc_sites(id) ON DELETE CASCADE,
  device_host   TEXT NOT NULL,
  collected_at  TIMESTAMPTZ NOT NULL,
  prefix        TEXT NOT NULL,        -- "10.0.0.0/24"
  next_hop      TEXT NOT NULL,
  protocol      TEXT NOT NULL,        -- "bgp" | "static" | ...
  metric        INTEGER NOT NULL DEFAULT 0,
  as_path       TEXT NOT NULL DEFAULT ''
);
CREATE INDEX ix_route_records_latest
  ON route_records (site_id, device_host, collected_at DESC);

CREATE TABLE netflow_records (
  record_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  team_id       UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
  site_id       UUID NOT NULL REFERENCES dc_sites(id) ON DELETE CASCADE,
  collected_at  TIMESTAMPTZ NOT NULL,
  src_ip        INET NOT NULL,
  dst_ip        INET NOT NULL,
  src_port      INTEGER NOT NULL,
  dst_port      INTEGER NOT NULL,
  protocol      SMALLINT NOT NULL,
  bytes         BIGINT NOT NULL,
  packets       BIGINT NOT NULL
  -- planner: add exporter_interface + exit_interface for D-05 (see Q2)
);
CREATE INDEX ix_netflow_records_window
  ON netflow_records (site_id, collected_at DESC);
CREATE INDEX ix_netflow_records_flow_key
  ON netflow_records (src_ip, dst_ip, src_port, dst_port, protocol);
```
Both tables: `ENABLE ROW LEVEL SECURITY` + `FORCE ROW LEVEL SECURITY` + team-isolation policy on `team_id` (Pattern C).

### Pitfall 2: Stale comment in `agent.py:113`

**What goes wrong:** Both `push_routes` and `push_flows` say "Phase 11 persists" in their docstring. Planner reading the file may assume persistence exists.
**How to avoid:** Wave 1 task explicitly updates both docstrings: "Phase 12 persists; payload validated via Pydantic, INSERT under RLS GUC."

### Pitfall 3: ECMP false-positive asymmetries

**What goes wrong:** Per-packet ECMP load balancing on a multi-link router can yield naturally different forward/return next-hops without an actual asymmetry problem.
**How to avoid:** Resolve ECMP next-hops deterministically in the trie (pick lexicographically lowest, mirroring `vty show ip route` line-order behavior) so the same pair always picks the same path. Document in `pathcompute/lpm.py` docstring.

### Pitfall 4: BGP flap-storm causes recompute thrashing

**What goes wrong:** During a BGP withdraw/announce flap, a push-triggered recompute would churn continuously. Even on the 15-min cadence, a transient flap during the compute window could yield asymmetric findings that "resolve" before the operator sees them.
**How to avoid:** Two mitigations: (a) the 15-min schedule already debounces — flaps shorter than 15 min are invisible; (b) for findings reconciliation, require the asymmetry to be seen in 2 consecutive recomputes before alerting via NFN-02 (planner picks). Document as "flap suppression."

### Pitfall 5: NetFlow window over the prune boundary

**What goes wrong:** TTL prune runs while a path-compute job is mid-flight; flow rows the job has SELECTed get deleted out from under it.
**How to avoid:** Run path-compute and `netflow_prune` jobs on DIFFERENT cron offsets (e.g., compute on `*/15 * * * *`, prune on `7,22,37,52 * * * *`). taskiq's `cron_offset` parameter handles this [CITED: taskiq-python.github.io].

### Pitfall 6: NET-010 reservation test flip (BLOCKER 2 for plan correctness)

**What goes wrong:** `cli/tests/test_flowmap_network_rules.py:71` `test_net_010_reserved_for_phase_3b` currently asserts `"NET-010" not in ids`. Phase 12 adds NET-010 → that test goes RED on first import of the Python detector.
**Evidence:**
```python
# cli/tests/test_flowmap_network_rules.py:71
def test_net_010_reserved_for_phase_3b(self):
    rules = load_rules()
    ids = {r.id for r in rules}
    assert "NET-010" not in ids, (
        "NET-010 is reserved for Phase 3b ..."
    )
```
**How to avoid:** Plan must include explicit task: rename `test_net_010_reserved_for_phase_3b` to `test_net_010_active_in_phase_12` and flip assertion. Note: `load_rules()` is the YAML rule loader — Phase 12 NET-010 is a Python detector NOT in the YAML rules. So the assertion may stay `not in ids` for the YAML catalog (D-11 says NET-010 is NOT a YAML rule). Planner must write a SEPARATE test asserting the Python detector emits findings with `rule_id="NET-010"`. **Both tests should coexist** — one locks "not in the YAML catalog," one locks "emitted by the Python network-detector pipeline."

### Pitfall 7: Rules-catalog count regression

**What goes wrong:** `cli/tests/test_security.py:64` asserts `assert len(rules) >= 51`. D-11 says count rises to 52. If NET-010 stays a Python detector outside the YAML catalog, the count stays 51 and this test does NOT trip. Planner must clarify (see Q3).

### Pitfall 8: `firewall_rules.src_cidr` is TEXT not INET

**What goes wrong:** Phase 11 D-08 / migration 011 defined `src_cidr` and `dst_cidr` as `TEXT`. Pydantic-side validation lives in the push schema. Path compute that does CIDR math must explicitly parse via `ipaddress.ip_network(row.src_cidr)`; an invalid stored value will raise mid-compute.
**How to avoid:** Wrap the parse in a per-rule try/except inside `pathcompute/correlate.py`; log + skip the malformed rule; do not crash the whole site's compute. (Same pattern as Phase 11 collectors' per-device error handling.)

### Pitfall 9: Pydantic model duplication drift between CLI and backend

**What goes wrong:** CONTEXT.md "Claude's Discretion" notes the planner picks whether to import `NetworkPath` from `cli/infracanvas/graph/models.py` or re-declare in `backend/app/schemas/`. If re-declared, they will drift.
**How to avoid:** **Recommendation: import.** `cli` is already a backend dependency (`infracanvas @ file:../cli` in `backend/pyproject.toml`). Re-export from `app.schemas.paths` so route handlers can use a single import path: `from app.schemas.paths import NetworkPath`. This costs nothing and prevents drift.

### Pitfall 10: Snapshot-per-recompute vs append-only `computed_paths` confusion

**What goes wrong:** D-16 says snapshot-per-pull / full-replace. A naive INSERT every compute will balloon storage AND blow the read API's "latest paths" query.
**How to avoid:** Two options — (a) DELETE-then-INSERT inside the compute transaction; (b) compute new `computed_at`, INSERT, then prune older rows for the same `(site_id, pair_src_cidr, pair_dst_cidr, direction)` keeping only the latest. Planner picks; option (b) preserves history briefly which helps debugging.

## Runtime State Inventory

> This section is required for rename/refactor/migration phases. Phase 12 is a feature-add phase (no string renames, no schema migrations of existing data), so most categories are not applicable. Included for completeness per the workflow doc.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — Phase 12 creates new tables; does not migrate existing data | None |
| Live service config | Slack webhook URL already in `teams.slack_webhook_url` (migration 009); reused as-is | None — no schema change |
| OS-registered state | None — taskiq worker process already running per Phase 6+ | None — new tasks register via import on worker startup |
| Secrets/env vars | NEW: `PATH_COMPUTE_TOP_K` (default 200), `NETFLOW_RECORD_TTL_HOURS` (default 24, planner picks), `NFN_02_ALERT_BYTES_PER_SEC_THRESHOLD` (planner picks) — add to env example + Railway/Fly secrets | Planner adds to `backend/.env.example` if it exists |
| Build artifacts | New pytricia compiled wheel — verify Docker base image has gcc (Python 3.12-slim does) | Confirm in CI |

**Nothing found in category:** Stored data — verified (this is a feature-add phase). OS-registered state — verified (the taskiq worker is already cron-aware).

## Common Pitfalls (continued — viewer-side)

### Pitfall 11: `PathEdge` test relies on direct render (bypasses ReactFlow)

**Context:** `viewer/src/__tests__/flowmap/PathEdge.test.tsx:5-14` documents that jsdom can't measure nodes, so the test renders `<PathEdge>` directly with synthetic `EdgeProps`. Phase 12 asymmetric-segment tests must follow the same pattern — don't try to render `<ReactFlow>`.

### Pitfall 12: `PathDetailPanel` is a generic node-detail panel today

**Context:** `viewer/src/components/flowmap/PathDetailPanel.tsx` is misnamed — it actually shows details for a *selected node* (selectedNode from store), with tabs for overview/findings/attributes/routes/cost. Phase 12 needs to add a path-aware mode. Two options:
- (a) Extend the existing panel with a new "Asymmetry" tab visible when a `PathEdge` is selected
- (b) Create a separate `AsymmetryDetailPanel.tsx` that renders on edge-selection

Recommendation: (a) — keep the single panel; add tab via the existing `tabs` array with a `hasAsymmetry` gate (mirroring `hasRoutes` / `hasCost` lines 65-66). Store needs a `selectedEdge` Zustand slice if it doesn't have one (planner verifies).

## Code Examples

### Per-cause evidence scoring

```python
# backend/app/security/pathcompute/classify.py

def score_nat(
    forward: NetworkPath, ret: NetworkPath,
    nat_rules: list[FirewallNATRule],
) -> float:
    """NAT_ASYMMETRY: forward path transits a NAT rule whose return-side
    translation pinhole doesn't exist or is mapped via a different interface
    pair.

    Signals (each adds 0.4 cap 1.0):
    - Forward path interface_out matches a NAT rule's interface_in, but no
      matching reverse NAT rule exists for the return path's interface_in.
    - Forward has a `src_translation` that's absent from the return rules.
    """
    score = 0.0
    fwd_egress = {h.interface_out for h in forward.hops if h.interface_out}
    ret_ingress = {h.interface_in for h in ret.hops if h.interface_in}
    nat_iface_pairs = {(n.interface_in, n.interface_out) for n in nat_rules}
    # A NAT in (fwd_egress → X) with no reverse (X → ret_ingress) is asymmetric
    for egress in fwd_egress:
        forward_nat = [n for n in nat_rules if n.interface_in == egress]
        if not forward_nat:
            continue
        for fn in forward_nat:
            reverse_exists = any(
                n.interface_in == fn.interface_out and n.interface_out in ret_ingress
                for n in nat_rules
            )
            if not reverse_exists:
                score += 0.5
    return min(score, 1.0)


def score_leak(
    forward_routes: list[RouteRecord], ret_routes: list[RouteRecord]
) -> float:
    """ROUTE_LEAK: more-specific prefix advertised by an unexpected peer or
    an as_path containing an upstream that shouldn't originate the prefix.

    Signals:
    - More-specific (longer prefix-length) route exists on one leg only
    - as_path on return leg contains an AS not in forward leg's as_path
    """
    score = 0.0
    fwd_prefixes = {r.prefix for r in forward_routes}
    ret_prefixes = {r.prefix for r in ret_routes}
    only_one_side = fwd_prefixes ^ ret_prefixes
    if only_one_side:
        score += 0.3 * min(len(only_one_side) / 5.0, 1.0)
    fwd_ases = {a for r in forward_routes for a in r.as_path.split()}
    ret_ases = {a for r in ret_routes for a in r.as_path.split()}
    if (ret_ases - fwd_ases):
        score += 0.4
    return min(score, 1.0)


def score_local_pref(
    forward_routes: list[RouteRecord], ret_routes: list[RouteRecord]
) -> float:
    """BGP_LOCAL_PREF: forward + return next_hops resolve through routers
    with mismatched LOCAL_PREF values on the same prefix, or as_path differs
    on the return leg.

    Note: Phase 10 RouteRecord does NOT carry LOCAL_PREF today. This score
    falls back to as_path-divergence + metric-divergence signals. Adding
    LOCAL_PREF to the schema is a planner discretion (see Q4).
    """
    score = 0.0
    fwd_paths = {r.as_path for r in forward_routes}
    ret_paths = {r.as_path for r in ret_routes}
    if fwd_paths != ret_paths:
        score += 0.3
    fwd_metrics = {r.metric for r in forward_routes}
    ret_metrics = {r.metric for r in ret_routes}
    if fwd_metrics != ret_metrics:
        score += 0.2
    return min(score, 1.0)
```

### LPM trie build pattern

```python
# backend/app/security/pathcompute/lpm.py
import pytricia
from app.schemas.agent import RouteRecord


def build_trie(routes: list[RouteRecord]) -> pytricia.PyTricia:
    """Build a Patricia trie keyed on CIDR prefix → (next_hop, metric, as_path).

    On collision (same prefix from multiple sources), keep the lowest-metric
    entry; on metric tie, lexicographically lowest next_hop (deterministic
    ECMP resolution per Pitfall 3).
    """
    trie = pytricia.PyTricia(32)  # 32-bit; IPv6 deferred
    for r in routes:
        existing = trie.get(r.prefix)
        if existing is None:
            trie[r.prefix] = (r.next_hop, r.metric, r.as_path)
            continue
        ex_next, ex_metric, _ = existing
        if (r.metric, r.next_hop) < (ex_metric, ex_next):
            trie[r.prefix] = (r.next_hop, r.metric, r.as_path)
    return trie


def lookup(trie: pytricia.PyTricia, ip: str) -> tuple[str, int, str] | None:
    """LPM lookup. Returns (next_hop, metric, as_path) or None if no match."""
    if ip not in trie:
        return None
    return trie[ip]
```

### Property test pattern (optional)

```python
# backend/tests/security/test_pathcompute_property.py — OPTIONAL hypothesis-based
import pytest
from hypothesis import given, strategies as st
from app.security.pathcompute.lpm import build_trie, lookup
from app.schemas.agent import RouteRecord


@given(
    routes=st.lists(
        st.builds(
            RouteRecord,
            prefix=st.from_regex(r"10\.\d{1,3}\.\d{1,3}\.0/24", fullmatch=True),
            next_hop=st.from_regex(r"10\.0\.0\.\d{1,3}", fullmatch=True),
            protocol=st.just("bgp"),
            metric=st.integers(0, 1000),
        ),
        min_size=1, max_size=50,
    ),
    target_ip=st.from_regex(r"10\.\d{1,3}\.\d{1,3}\.\d{1,3}", fullmatch=True),
)
def test_lpm_is_deterministic(routes, target_ip):
    trie1 = build_trie(routes)
    trie2 = build_trie(list(reversed(routes)))   # order-independence
    assert lookup(trie1, target_ip) == lookup(trie2, target_ip)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Push-triggered recompute on every route/firewall change | Scheduled 15-min taskiq cron + on-demand admin endpoint | D-04 lock | Prevents thrash during BGP flaps |
| Multi-label classifier emitting "asymmetric because [N reasons]" | Evidence-scored single-label with NAT > LEAK > LOCAL_PREF tiebreaker; non-winning scores in `evidence` JSONB | D-08 lock | Single alert wording; rich diagnostic when operator drills in |
| Strict hop-by-hop NetFlow correlation | Endpoint + edge-hop match | D-05 lock | NetFlow exporter coverage is sparse in hybrid; strict matching overstates failures |
| Path-pattern YAML rule operators | Python detector module for path-aware rules | D-11 lock | One rule (NET-010) doesn't justify engine surface expansion |
| Append-only `computed_paths` | Snapshot-per-compute, full-replace, reconcile findings | D-16 lock | Bounded storage; matches Phase 11 D-10 mental model |

**Deprecated/outdated:**
- Linear LPM via `for net in routes: if ip in net`: too slow for production RIBs; use pytricia.
- Phase 10's "logs only" routes/flows ingest: Phase 12 must complete the persistence work (Blocker 1).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | NetFlow exporter+exit interface metadata can be added to `FlowRecord` schema | Pattern 3, Q2 | If Phase 10 NetFlow listener (`agent/internal/netflow/listener.go`) doesn't expose these fields from goflow2/v2, D-05's edge-hop match degrades to endpoint-only matching. [ASSUMED] |
| A2 | `pytricia` 1.3.0 builds cleanly inside the Railway/Fly Docker base image | Standard Stack | If gcc/build-essential is missing, plan must add to Dockerfile. Mitigation: Python 3.12-slim ships with build deps per CLAUDE.md. [VERIFIED: PyPI release Sept 2025] |
| A3 | The chosen 0.4 evidence threshold for `UNKNOWN` is correct | Pattern 5 | Too high → many UNKNOWN; too low → many false-positive classifications. Default is illustrative; planner / first ops review tunes. [ASSUMED] |
| A4 | Phase 10 `RouteRecord` carries `as_path` populated by NETCONF collector | Code Examples §score_leak | Confirmed by reading `backend/app/schemas/agent.py:40` `as_path: str = ""` — the field exists but defaults to empty if NETCONF response didn't include it. Risk: empty as_path neuters the LEAK classifier signal. [VERIFIED: schemas/agent.py] |
| A5 | The Phase 8 Slack dispatcher can be extracted without breaking the existing scan_repo call | Pattern 6 | Pattern 6 keeps the inline call shape compatible (same args, same swallow-and-log behavior). Risk: low; planner verifies the extracted helper passes the Phase 8 regression tests under `backend/tests/jobs/test_scan_repo.py`. [VERIFIED: file exists at `/Users/bhushan/Documents/Projects/Infracanvas/backend/tests/jobs/test_scan_repo.py`] |
| A6 | NET-010 stays out of the YAML rule catalog (`rules/` dir) but emits findings with `rule_id="NET-010"` through the same pipeline | Pitfall 6 | If aggregation pipeline filters by YAML-loaded rule IDs only, the Python detector findings won't surface. Planner verifies the findings aggregator accepts arbitrary `rule_id` strings (CONTEXT.md "Catalog integration" claims it does — Phase 2 D-09 / Phase 3 D-12). [ASSUMED based on CONTEXT.md claim — planner should validate the claim by reading the aggregator] |
| A7 | The 15-min taskiq cron syntax `*/15 * * * *` is supported by taskiq-redis broker | Pattern 1 | If taskiq 0.11 doesn't ship native cron, planner falls back to a sleep-loop pattern. Mitigation: taskiq docs explicitly document `cron` in schedule label [CITED]. [VERIFIED: taskiq-python.github.io] |
| A8 | `selectedEdge` exists in viewer Zustand store (or can be added) | Pitfall 12 | If not, FMV-02 PathDetailPanel can't reactively switch to asymmetry view. Planner reads `viewer/src/store.ts` and confirms before Wave 4. [ASSUMED] |
| A9 | TTL of 24h for `netflow_records` is sufficient | Pitfall 5 / Discretion | If shorter, may lose correlation samples for low-volume pairs. If longer, storage grows fast. Planner picks; 24h is the suggested starting point. [ASSUMED] |
| A10 | `firewall_rules.src_cidr` / `dst_cidr` are always valid CIDR strings | Pitfall 8 | Phase 11 push validates via Pydantic, but raw_blob bypass is possible. Mitigation: per-row try/except in compute. [VERIFIED: Pydantic boundary at `app/schemas/firewall.py`] |

## Open Questions (RESOLVED)

1. **RESOLVED — Q1: Phase 12 owns routes/flows persistence.**
   - Resolution: Plan 12-02 (Wave 1) ships migration `012_route_flow_tables` adding `route_records` + `netflow_records` plus updates to `backend/app/routes/agent.py` push handlers (replacing the log-and-discard stubs).
   - Closes BLOCKER 1. All downstream compute plans depend on 12-02.

2. **RESOLVED — Q2: Exporter/exit interface fields deferred to v1.2; v1.1 ships endpoint-only correlation.**
   - Resolution: `agent/internal/netflow/types.go` does NOT carry `exporter_interface` / `exit_interface`. Per planner inspection, adding them is a Go agent change with NetFlow template re-parsing scope. For v1.1, correlate.matches() uses the endpoint-only fallback (Pitfall 11 path). D-05's "endpoint + edge-hop" requirement is partially honored — endpoint correlation is live, edge-hop deferred to a v1.2 follow-up (tracked in CONTEXT.md `<deferred>`).
   - Plan impact: 12-02 schema extension dropped; 12-05 correlate.py uses endpoint-only matching with an explicit `# TODO(v1.2): add edge-hop comparison once agent emits exporter_interface` marker.

3. **RESOLVED — Q3: YAML rules-catalog count stays at 51.**
   - Resolution: NET-010 is a Python detector outside the YAML catalog. Plan 12-01 Wave 0 adds `cli/tests/test_net_010_detector.py` asserting the Python detector emits findings with `rule_id="NET-010"` and `source="network"`. The existing `cli/tests/test_security.py:64` assertion (51 rules) remains unchanged.
   - CONTEXT.md D-11 "count 51→52" is reinterpreted as "detector count (YAML + Python) effectively rises by 1," with the YAML count preserved.

4. **RESOLVED — Q4: Ship classifier with as_path/metric fallback; defer LOCAL_PREF field to v1.2.**
   - Resolution: `RouteRecord` keeps current fields (`prefix`, `next_hop`, `protocol`, `metric`, `as_path`). `score_local_pref()` uses the as_path/metric fallback. Naming retained as `BGP_LOCAL_PREF` for stability; the documented semantics are "BGP path-attribute mismatch (as_path/metric)" until v1.2 adds true LOCAL_PREF.

5. **RESOLVED — Q5: Zustand store already exposes `selectedPath` (not `selectedEdge`).**
   - Resolution: PATTERNS.md verified `selectedPath` slice exists in `viewer/src/store.ts` (line 42). CONTEXT.md reference to `selectedEdge` was a naming slip. Plan 12-07 uses `selectedPath` and adds the optional `asymmetry?: AsymmetryPayload` field on the path object; a viewer hydration task fetches `/v1/sites/{id}/asymmetries` and attaches the payload before the store sets `selectedPath`.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | Backend (path compute, classifier) | ✓ (verified — pyproject.toml requires-python >= 3.12) | 3.12 | — |
| pytricia | LPM trie | ✗ (not in `backend/pyproject.toml` today) | — install 1.3.0 | py-radix (maintenance-only) |
| FastAPI 0.115 | Read API | ✓ | 0.115.x | — |
| taskiq 0.11 + taskiq-redis 1.0 | Scheduled + on-demand jobs | ✓ | 0.11.x | — |
| Postgres / Neon | Storage | ✓ | — | — |
| Redis | Taskiq broker | ✓ | 5.2.x client | — |
| `gen_random_uuid()` (Postgres) | New table PK defaults | ✓ (used by Phase 11 migrations) | — | uuid.uuid4 in Python |
| @xyflow/react 12.6.0 | PathEdge extensions | ✓ | 12.6.0 | — |
| React 18.3.1 | UI | ✓ | 18.3.1 | — |
| Vitest 4.1.4 | Viewer tests | ✓ | 4.1.4 | — |
| Existing `teams.slack_webhook_url` column | NFN-02 reuse | ✓ | migration 009 | — |
| Existing `require_site_token` dep | Wave 1 push handler updates | ✓ | `backend/app/auth/site_token.py` | — |
| Existing `Pattern B` RLS-GUC-set | All Wave 2+ DB ops | ✓ | `firewalls.py:103-107` template | — |

**Missing dependencies with no fallback:**
- `route_records` + `netflow_records` tables — Blocker 1 (Phase 12 must create)

**Missing dependencies with fallback:**
- `pytricia` — easy install; fallback is `py-radix` (older but works)

## Validation Architecture

> Required per `.planning/config.json` `workflow.nyquist_validation: true`.

### Test Framework

| Property | Value |
|----------|-------|
| Backend framework | pytest 8.3 + pytest-asyncio 0.24 (existing) |
| Backend config file | `backend/pyproject.toml` `[tool.pytest.ini_options]` (existing) |
| Backend quick run | `cd backend && pytest tests/security/pathcompute/ -x --tb=short` |
| Backend full suite | `cd backend && pytest -x --cov=app --cov-report=term-missing` |
| CLI framework | pytest (existing under `cli/tests/`) |
| CLI quick run | `cd cli && pytest tests/test_net_010_detector.py -x` |
| CLI full suite | `cd cli && pytest -x` |
| Viewer framework | Vitest 4.1.4 (existing) |
| Viewer quick run | `cd viewer && npx vitest run src/__tests__/flowmap/PathEdge.test.tsx src/__tests__/flowmap/PathDetailPanel.test.tsx` |
| Viewer full suite | `cd viewer && npx vitest run` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PTH-01 | Forward path computed correctly for fixture topology | unit | `pytest backend/tests/security/pathcompute/test_forward.py -x` | ❌ Wave 0 |
| PTH-02 | Return path is forward with src/dst swapped | unit | `pytest backend/tests/security/pathcompute/test_pair.py -x` | ❌ Wave 0 |
| PTH-03 | NetFlow endpoint + edge-hop match against fixture flows | unit | `pytest backend/tests/security/pathcompute/test_correlate.py -x` | ❌ Wave 0 |
| PTH-03 | Path_divergence finding emitted when observed ≠ computed (D-07) | unit | `pytest backend/tests/security/pathcompute/test_correlate.py::test_divergence_emitted -x` | ❌ Wave 0 |
| ASY-01 | Symmetric pair → no finding; asymmetric pair → finding | unit | `pytest backend/tests/security/pathcompute/test_asymmetry.py -x` | ❌ Wave 0 |
| ASY-02 | NAT_ASYMMETRY scores higher than ROUTE_LEAK in NAT-only fixture | unit | `pytest backend/tests/security/pathcompute/test_classify.py::test_nat_wins -x` | ❌ Wave 0 |
| ASY-02 | UNKNOWN emitted when all scores below threshold (D-09) | unit | `pytest backend/tests/security/pathcompute/test_classify.py::test_unknown_fallback -x` | ❌ Wave 0 |
| ASY-02 | Deterministic NAT > LEAK > LOCAL_PREF tiebreaker on tied scores | unit | `pytest backend/tests/security/pathcompute/test_classify.py::test_tiebreaker -x` | ❌ Wave 0 |
| ASY-03 | Impact bytes_per_sec computed from fixture NetFlow window | unit | `pytest backend/tests/security/pathcompute/test_impact.py::test_bytes_per_sec -x` | ❌ Wave 0 |
| ASY-03 | Impact firewall_count counts distinct stateful firewalls on one leg | unit | `pytest backend/tests/security/pathcompute/test_impact.py::test_firewall_count -x` | ❌ Wave 0 |
| NET-010 | Python detector emits NetworkFinding with `rule_id="NET-010"` | unit | `pytest cli/tests/test_net_010_detector.py -x` | ❌ Wave 0 |
| NET-010 | YAML catalog still does NOT include NET-010 (reservation test stays green) | unit | `pytest cli/tests/test_flowmap_network_rules.py::test_net_010_reserved_for_phase_3b -x` | ✅ exists; semantics unchanged per Q3 recommendation |
| FMV-02 | PathEdge renders red dashed stroke when `data.asymmetric=true` | unit | `npx vitest run viewer/src/__tests__/flowmap/PathEdge.test.tsx -t "asymmetric"` | ❌ Wave 0 |
| FMV-02 | PathDetailPanel renders side-by-side hop table when edge selected and asymmetric | unit | `npx vitest run viewer/src/__tests__/flowmap/PathDetailPanel.test.tsx -t "asymmetry"` | ❌ Wave 0 |
| NFN-02 | Slack dispatcher fires when new asymmetry has impact_firewall_count ≥ 1 | integration | `pytest backend/tests/jobs/test_path_compute_alerts.py::test_fires_on_new -x` | ❌ Wave 0 |
| NFN-02 | Slack dispatcher does NOT fire when finding unchanged across recomputes | integration | `pytest backend/tests/jobs/test_path_compute_alerts.py::test_no_fire_when_unchanged -x` | ❌ Wave 0 |
| NFN-02 | Slack failure swallowed + Sentry-captured (does not abort job) | integration | `pytest backend/tests/jobs/test_path_compute_alerts.py::test_slack_failure_swallowed -x` | ❌ Wave 0 |
| D-04 | Scheduled cron registers at `*/15 * * * *` | unit | `pytest backend/tests/queue/test_path_compute_schedule.py -x` | ❌ Wave 0 |
| D-04 | On-demand endpoint coalesces concurrent calls (idempotent) | integration | `pytest backend/tests/routes/test_paths_recompute.py::test_coalesces -x` | ❌ Wave 0 |
| D-14 | `GET /v1/sites/{id}/paths` returns 200 happy path, 404 cross-team site_id, 401 missing JWT | integration | `pytest backend/tests/routes/test_paths_read.py -x` | ❌ Wave 0 |
| D-14 | `GET /v1/sites/{id}/asymmetries` filters by cause + min impact | integration | `pytest backend/tests/routes/test_paths_read.py::test_asymmetries_filter -x` | ❌ Wave 0 |
| D-15 | All three new tables have RLS ENABLE + FORCE + policy | integration | `pytest backend/tests/migrations/test_path_compute_rls.py -x` | ❌ Wave 0 |
| D-16 | Findings reconciliation: still-present updates last_seen_at; missing sets resolved_at | unit | `pytest backend/tests/security/pathcompute/test_reconcile.py -x` | ❌ Wave 0 |
| Blocker 1 | Routes/flows actually persist after push (regression test on existing push handlers) | integration | `pytest backend/tests/routes/test_agent_routes_persist.py -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** scope-relevant quick run (e.g., `pytest backend/tests/security/pathcompute/ -x` for a compute task; `npx vitest run viewer/src/__tests__/flowmap/` for a viewer task)
- **Per wave merge:** full backend + viewer suite
- **Phase gate:** Full backend (`pytest -x --cov=app`) + full CLI + full viewer suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `backend/tests/security/pathcompute/__init__.py` + `conftest.py` — shared fixtures (`mk_route_record`, `mk_flow`, `mk_path`, `mk_nat_rule`)
- [ ] `backend/tests/security/pathcompute/test_forward.py` — covers PTH-01
- [ ] `backend/tests/security/pathcompute/test_pair.py` — covers PTH-02
- [ ] `backend/tests/security/pathcompute/test_correlate.py` — covers PTH-03 (match + divergence)
- [ ] `backend/tests/security/pathcompute/test_asymmetry.py` — covers ASY-01
- [ ] `backend/tests/security/pathcompute/test_classify.py` — covers ASY-02 (3 cause-specific cases + UNKNOWN + tiebreaker)
- [ ] `backend/tests/security/pathcompute/test_impact.py` — covers ASY-03
- [ ] `backend/tests/security/pathcompute/test_reconcile.py` — covers D-16
- [ ] `backend/tests/jobs/test_path_compute_alerts.py` — covers NFN-02
- [ ] `backend/tests/queue/test_path_compute_schedule.py` — covers D-04 cron registration
- [ ] `backend/tests/routes/test_paths_read.py` — covers D-14 read API
- [ ] `backend/tests/routes/test_paths_recompute.py` — covers D-14 on-demand
- [ ] `backend/tests/routes/test_agent_routes_persist.py` — covers Blocker 1 regression
- [ ] `backend/tests/migrations/test_path_compute_rls.py` — covers D-15 RLS posture
- [ ] `cli/tests/test_net_010_detector.py` — covers NET-010 Python detector emission
- [ ] `viewer/src/__tests__/flowmap/PathEdge.test.tsx` — EXTEND with asymmetric-stroke assertion (file exists)
- [ ] `viewer/src/__tests__/flowmap/PathDetailPanel.test.tsx` — EXTEND with side-by-side table assertion (file exists)
- [ ] Framework install: `cd backend && pip install pytricia==1.3.0 && pip install -e .[dev]` (pytricia is new)
- [ ] Hypothesis (optional, planner picks): `pip install hypothesis~=6.118.0` for property tests

## Security Domain

> Phase 12 inherits Phase 10/11 security posture (site-token Bearer auth for ingest, Clerk JWT for read, RLS team_isolation on every table). No new auth surface.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | Reused: Clerk JWT (read API) + site-token Bearer (ingest extensions). No new auth code. |
| V3 Session Management | no | No sessions — JWT + bearer only |
| V4 Access Control | yes | Pattern C RLS on all 5 new tables (`route_records`, `netflow_records`, `computed_paths`, `asymmetry_findings`, `path_divergence_findings`) + `require_role("owner")` on `POST /paths/recompute` |
| V5 Input Validation | yes | Pydantic at every API boundary (push schema bounds, read query param validation, CIDR parsing in compute); per-rule try/except for stored CIDR strings (Pitfall 8) |
| V6 Cryptography | no | Reuses existing site-token SHA-256 hashing + Clerk JWT verification; no new crypto |
| V7 Error Handling | yes | Slack dispatcher swallow+Sentry pattern; per-rule + per-site error containment in path-compute job |
| V8 Data Protection | yes | NetFlow contains src/dst IPs — PII-adjacent. TTL of 24h (planner picks) limits exposure window. RLS prevents cross-team leakage. |
| V9 Communications | yes | All inbound HTTPS (FastAPI on Fly/Railway); outbound to Slack over HTTPS — already enforced by Phase 8 |
| V10 Malicious Code | no | No code execution surface added |
| V11 Business Logic | yes | Asymmetry classifier is business logic; evidence-scored with explicit thresholds prevents silent misclassification |
| V12 Files and Resources | no | No file upload/download added |
| V13 API and Web Service | yes | All 3 read endpoints follow Phase 11 D-11 pattern (Clerk JWT, RLS, 404-not-403 cross-team) |
| V14 Configuration | yes | New env vars: `PATH_COMPUTE_TOP_K`, `NETFLOW_RECORD_TTL_HOURS`, `NFN_02_ALERT_BYTES_PER_SEC_THRESHOLD`. Document defaults; never log values that would expose customer infrastructure shape |

### Known Threat Patterns for {Phase 12 stack}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Cross-team data leakage via path/finding API | Information Disclosure | RLS FORCE + Pattern B RLS GUC set in every read tx; site-membership 404-not-403 probe FIRST |
| DoS via unbounded push payload (routes/flows) | Denial of Service | Pattern D — `Field(..., max_length=N)` on `RoutesPushBody.routes` (already 10000) and `FlowsPushBody.flows` (already 10000) |
| DoS via repeated on-demand recompute spam | Denial of Service | Per-site lock OR queue dedup (planner picks per CONTEXT.md discretion); idempotent endpoint shape returns 202 + existing job_id |
| SQL injection via stored CIDR strings | Tampering | All SQL parameterized; CIDR strings stored as TEXT but parsed via `ipaddress.ip_network(...)` before any comparison (Pitfall 8) |
| Slack URL exfiltration via log | Information Disclosure | Existing Phase 8 pattern logs `slack_alert_sent` event without URL; reuse helper preserves this |
| NetFlow data leak via shared compute output | Information Disclosure | `computed_paths.match_evidence` JSONB scoped by team via RLS; no shared cache |
| Compute job exhausts worker CPU during BGP flap | Denial of Service | 15-min schedule cap + per-site lock + ECMP determinism (Pitfall 3) |
| Path-detail panel leaks internal AS numbers to share-link viewers | Information Disclosure | Phase 12 read API requires Clerk JWT — share-link surface is OUT OF SCOPE for Phase 12 (deferred per CONTEXT.md). Confirm share-link viewer does NOT fetch from Phase 12 endpoints. |
| Stored XSS via raw route prefix or as_path string in dashboard | XSS | React auto-escapes; `JSON.stringify` in `AttributesTab` already proven safe in `PathDetailPanel.tsx:172-188`; new hop tables follow same pattern |

## Sources

### Primary (HIGH confidence)
- `/Users/bhushan/Documents/Projects/Infracanvas/.planning/phases/12-path-asymmetric-routing/12-CONTEXT.md` — D-01..D-16 lock
- `/Users/bhushan/Documents/Projects/Infracanvas/.planning/phases/11-firewall-integration/11-CONTEXT.md` — D-15 column contract, D-08/D-10 schema posture
- `/Users/bhushan/Documents/Projects/Infracanvas/.planning/phases/11-firewall-integration/11-PATTERNS.md` — Patterns A–H (site-token, Clerk JWT + RLS, RLS policy, push-bound, idempotent snapshot_id, retry, redaction, primitive-args)
- `/Users/bhushan/Documents/Projects/Infracanvas/backend/migrations/versions/20260510_011_firewall_tables.py` — D-15 column contract verified
- `/Users/bhushan/Documents/Projects/Infracanvas/backend/app/db/models.py:195-316` — `FirewallRulesetSnapshot` / `FirewallRuleORM` / `FirewallNATRuleORM` / `FirewallObjectORM` ORM classes
- `/Users/bhushan/Documents/Projects/Infracanvas/backend/app/routes/firewalls.py` — Read API template (Pattern B)
- `/Users/bhushan/Documents/Projects/Infracanvas/backend/app/routes/agent.py` — Ingest pattern + Blocker 1 evidence (`push_routes:113`, `push_flows:129` log-only)
- `/Users/bhushan/Documents/Projects/Infracanvas/backend/app/queue/tasks/firewall_prune.py` — Prune job template
- `/Users/bhushan/Documents/Projects/Infracanvas/backend/app/queue/broker.py` — Taskiq broker setup; SmartRetry middleware
- `/Users/bhushan/Documents/Projects/Infracanvas/backend/app/queue/tasks/scan_repo.py:299-341` — Phase 8 Slack dispatcher to extract
- `/Users/bhushan/Documents/Projects/Infracanvas/backend/app/schemas/agent.py:33-77` — RouteRecord + FlowRecord shapes
- `/Users/bhushan/Documents/Projects/Infracanvas/cli/infracanvas/graph/models.py:99-150` — NetworkPath / PathHop / NetworkFinding Pydantic models
- `/Users/bhushan/Documents/Projects/Infracanvas/cli/tests/test_flowmap_network_rules.py:71` — NET-010 reservation test to update
- `/Users/bhushan/Documents/Projects/Infracanvas/cli/tests/test_security.py:64` — Rules catalog count assertion
- `/Users/bhushan/Documents/Projects/Infracanvas/viewer/src/components/flowmap/edges/PathEdge.tsx` — Dual-lane edge to extend
- `/Users/bhushan/Documents/Projects/Infracanvas/viewer/src/components/flowmap/PathDetailPanel.tsx` — Detail panel to extend
- `/Users/bhushan/Documents/Projects/Infracanvas/viewer/src/__tests__/flowmap/PathEdge.test.tsx` — Test pattern (direct render, bypasses ReactFlow)
- [taskiq scheduling docs](https://taskiq-python.github.io/guide/scheduling-tasks.html) — cron schedule label format
- [pytricia PyPI](https://pypi.org/project/pytricia/) — version 1.3.0, Python 3.12 support, Sept 2025 release
- [pytricia GitHub](https://github.com/jsommers/pytricia) — Patricia trie API

### Secondary (MEDIUM confidence — cross-verified vendor guidance)
- [Cisco asymmetric routing troubleshooting (Noction summary)](https://www.noction.com/blog/bgp-and-asymmetric-routing)
- [pfSense asymmetric routing docs](https://docs.netgate.com/pfsense/en/latest/troubleshooting/asymmetric-routing.html)
- [Palo Alto asymmetric routing KB](https://knowledgebase.paloaltonetworks.com/KCSArticleDetail?id=kA10g000000ClSHCA0)
- [Checkpoint asymmetry community thread](https://community.checkpoint.com/t5/General-Topics/Eliminating-Routing-Asymmetry-between-Two-Different-Physical/td-p/10673)
- [Azure ExpressRoute asymmetric routing](https://learn.microsoft.com/en-us/azure/expressroute/expressroute-asymmetric-routing)
- [Avoiding asymmetric routing with AWS Network Firewall](https://docs.aws.amazon.com/network-firewall/latest/developerguide/asymmetric-routing.html)
- [Kentik BGP NetFlow analysis](https://www.kentik.com/kentipedia/bgp-netflow-analysis/)

### Tertiary (informational)
- [Inter-AS routing anomaly classification (CCDCOE)](https://ccdcoe.org/uploads/2018/10/d2r2s5_wybbeling.pdf) — academic taxonomy supporting evidence-scored approach

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — pytricia + Python 3.12 verified on PyPI; taskiq cron syntax verified in docs; all existing backend deps already in pyproject.toml
- Architecture: HIGH — Phase 11 patterns A–H verified by reading firewalls.py + firewall_prune.py + migration 011 directly
- Path compute correctness: MEDIUM — algorithm well-trodden but evidence thresholds in classifier are illustrative and will need first-customer tuning
- NetFlow correlation: MEDIUM — depends on Q2 (agent exposing exporter/exit interface metadata); edge-hop match may degrade to endpoint-only if not
- Routes/flows persistence (Blocker 1): HIGH — verified absence by grep across all migrations; verified handler is log-only by reading agent.py
- NET-010 detector wiring: MEDIUM — Q3 ambiguity on whether catalog count test changes; resolution path documented
- FMV-02 viewer: HIGH — PathEdge already supports `direction` prop + dual lanes; minimal additive change
- NFN-02 alert: HIGH — Slack dispatcher pattern proven in Phase 8 scan_repo.py; extraction is mechanical
- Pitfalls: HIGH — verified against actual code (file paths + line numbers) and vendor docs

**Research date:** 2026-05-17
**Valid until:** 2026-06-17 (30 days — stable phase domain; pytricia release cadence is slow)
