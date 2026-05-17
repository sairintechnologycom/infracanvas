# Phase 12: Path Computation + Asymmetric Routing - Context

**Gathered:** 2026-05-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Compute forward + return network paths between data-centre subnets and cloud subnets using the route, NAT, and firewall-rule data already landing in the backend (Phase 10 routes/flows, Phase 11 firewall ingest). Correlate the computed paths against observed NetFlow, flag asymmetric pairs, classify root cause (BGP_LOCAL_PREF / ROUTE_LEAK / NAT_ASYMMETRY / UNKNOWN), score impact, surface in the FlowMap viewer (FMV-02), and alert on churn (NFN-02). Activate NET-010.

**In scope:**
- Backend taskiq job that computes paths every 15 min per active site, plus an on-demand "recompute now" admin endpoint
- New backend tables for computed paths, path hops, asymmetry findings, and path-divergence findings (RLS-scoped to team, like Phase 10/11)
- Backend read API: `GET /v1/sites/{site_id}/paths`, `GET /v1/sites/{site_id}/asymmetries` (Clerk JWT, team-scoped)
- NetFlow correlation logic (endpoint + edge-hop match against rolling 1h flow window)
- Asymmetry detector comparing forward vs return paths
- Evidence-scored root-cause classifier with deterministic NAT > LEAK > LOCAL_PREF tiebreaker; `UNKNOWN` bucket when nothing fires
- Impact scoring: flow-byte volume (from NetFlow) + affected stateful-firewall count
- NET-010 as a Python detector module under `cli/infracanvas/security/network/` (path-aware, NOT a YAML rule)
- FMV-02: extend existing `PathEdge` to render forward + return as dual strands, mark asymmetric leg with red dashed stroke; `PathDetailPanel` adds side-by-side hop comparison
- NFN-02: route-change/asymmetry alerts reuse the Phase 8 Slack dispatcher (`slack_webhook_url` on team) with a Phase-12-specific severity threshold

**Out of scope:**
- Cloud↔Cloud paths (TGW peering, ExpressRoute cross-cloud) — deferred; v1.1 scope is DC↔Cloud hybrid edge only
- DC↔DC intra-site paths — defer (mostly L2/MPLS opacity)
- Cartesian path computation over all declared subnet pairs — only NetFlow-observed top-K pairs in v1.1
- Embedding computed paths into the scan JSON `ResourceGraph.network_paths` field — defer (compute is backend-only; viewer fetches via new API). CLI offline scans continue to render empty `network_paths` until/unless a later phase wires this in.
- Multi-label classification (one cause per asymmetry, by design)
- Email or in-app inbox alert channels — Slack-only reuse in v1.1
- Path-pattern operators in the YAML rule engine — NET-010 is a Python detector instead
- Real-time recomputation on every route/firewall push (scheduler-driven, not push-driven)
- Cloud-only paths re-using NetFlow when there is no DC agent — out of scope; this phase requires DC agent data
- Dashboard UI for browsing asymmetries (read API only in this phase; UI lands in a later dashboard phase, parallel to Phase 11 D-11)

</domain>

<decisions>
## Implementation Decisions

### Compute location (PTH-01..03, ASY-01..03)
- **D-01:** Path computation runs **backend-side as a taskiq worker job**. Job reads the latest `firewall_ruleset_snapshots` per device (Phase 11 D-15 contract), the latest route push per site (Phase 10), and the most recent NetFlow window from the existing flow tables. CLI/dashboard read paths via the new backend API; no path computation in `infracanvas scan`.
  - **Why:** NetFlow already lives backend-side (Phase 10 D-08); firewall rules + NAT already live backend-side (Phase 11 D-10); putting compute next to the data avoids round-tripping bulk snapshots to the CLI. Aligns with SaaS-tier billing — path/asymmetry analysis is a paid feature.

### Asymmetry scope (PTH-01..03)
- **D-02:** Phase 12 only computes **DC ↔ Cloud** paths (hybrid edge). Cloud↔Cloud (TGW/ER cross-cloud) and DC↔DC are deferred.
  - **Why:** Hybrid edge is the documented asymmetry pain point; smallest scope that hits the v1.1 ROADMAP success criteria. Cloud↔Cloud and DC↔DC add quadratic surface area without proven customer demand.

### Pair selection (PTH-03 driver)
- **D-03:** Pairs are selected from **observed NetFlow, top-K by byte volume** over the last 1h window. K is planner-tunable (suggest K=200 default, env-overridable).
  - **Why:** Cartesian path computation over all declared subnet pairs explodes (500 subnets → 250k pairs). Top-K by volume is what operators actually care about. Pairs with zero observed traffic don't matter to "are flows asymmetric in production."

### Recompute trigger
- **D-04:** A **scheduled taskiq job runs every 15 minutes** per active DC site, plus an on-demand `POST /v1/sites/{site_id}/paths/recompute` endpoint (Clerk JWT, owner role, idempotent — coalesces concurrent calls). Route-push and firewall-push events do NOT directly trigger recomputation.
  - **Why:** Push-triggered would thrash the worker during BGP flaps and would waste cycles on no-op pushes. 15 min is responsive enough for ops; on-demand covers "I just fixed it, recompute now."

### NetFlow correlation (PTH-03)
- **D-05:** Correlation is **endpoint + edge-hop match**: an observed flow matches a computed path iff (a) the flow's src/dst IPs fall inside the path's src/dst CIDRs, AND (b) the first hop's ingress interface and the last hop's egress interface match the observed flow's exporter/interface metadata. Mid-path hops are trusted from routing data.
  - **Why:** Strict hop-by-hop overstates what NetFlow actually sees in hybrid environments (sparse exporter coverage). Endpoint-only loses interface-level signal that ASY-02 NAT_ASYMMETRY classification needs. Endpoint + edge-hop balances precision and recall.
- **D-06:** Correlation uses a **rolling 1-hour NetFlow window**. Flow samples older than 1h are not considered.
  - **Why:** 1h is long enough that bursty/quiet pairs still have samples; short enough that stale flows from a previous topology don't poison the match.
- **D-07:** When observed flow ≠ computed path, emit a **`path_divergence`** finding (a distinct kind from `asymmetry_finding`). Both kinds surface in the FlowMap viewer, with different colors and copy.
  - **Why:** Divergence ("NetFlow shows a path our routing model didn't predict") and asymmetry ("forward and return paths disagree") are diagnostically different. Conflating them poisons the root-cause classifier's evidence inputs.

### Root cause classifier (ASY-02)
- **D-08:** Classifier is **evidence-scored with a deterministic tiebreaker**. Each cause (BGP_LOCAL_PREF, ROUTE_LEAK, NAT_ASYMMETRY) gets a 0–1 confidence from its own evidence rules. Highest confidence wins. On tie, fixed precedence **NAT > LEAK > LOCAL_PREF** (most specific first). All non-winning scores are persisted in `evidence` JSONB for the diagnostic detail panel.
  - **Why:** Multi-label classification breaks the alert wording ("asymmetric because [N things]") and conflicts with ASY-02's singular "classifier assigns" requirement. Strict deterministic precedence loses the diagnostic richness when more than one cause genuinely fires. Evidence-scored gives operators the full picture while still emitting a single winning label.
- **D-09:** When no cause clears its evidence threshold, the finding is emitted with cause = **`UNKNOWN`** and the full evidence dump in `evidence`. UI surfaces "asymmetric — cause unknown, see evidence."
  - **Why:** Suppressing un-classified asymmetries hides real customer problems. Defaulting to BGP_LOCAL_PREF is wrong-by-default. UNKNOWN is honest and lets the customer investigate without us guessing.

### Impact scoring (ASY-03)
- **D-10:** Impact is **two scalars**: (a) flow-byte volume of affected flows over the last 1h (from NetFlow), and (b) count of distinct stateful firewalls that see only one leg of the asymmetric pair. Both surface in the viewer; viewer sorts asymmetries by `firewall_count DESC, byte_volume DESC`.
  - **Why:** Operators prioritise by what's actually hurting (volume) AND what's actually exposed to stateful inspection (firewall count). Severity tier alone (critical/high/medium) is too coarse for sorting. Affected-firewall count alone misses huge low-firewall flows.

### NET-010 activation
- **D-11:** NET-010 ships as a **Python detector module** under `cli/infracanvas/security/network/` (path-aware), not as a YAML rule. The module reads the computed forward + return paths and the stateful-firewall list, fires when a stateful firewall sees only one direction. The reservation test `test_net_010_reserved_for_phase_3b` is updated to assert the detector exists and emits `NET-010` findings under the rule-id contract.
  - **Why:** YAML rule operators can express attribute matches and path-cost expressions but not "compare two path objects." Building `path.forward.hops` / `path.return.hops` matchers materially expands the rule engine for one rule. Python detector keeps the rule-engine surface stable and uses idiomatic code for path-pair logic.
  - **Catalog integration:** The detector emits findings with `rule_id="NET-010"` and `source="network"` so they aggregate through the existing findings pipeline (Phase 2 D-09 / Phase 3 D-12). The rules catalog count rises from 51 → 52.

### FMV-02 — Path divergence marker in viewer
- **D-12:** FMV-02 is implemented as **dual-edge rendering in the existing `PathEdge` component**: forward leg as a solid stroke (existing color), return leg as a parallel stroke offset slightly. Asymmetric segments get a **red dashed** style on the affected leg. `PathDetailPanel` adds a side-by-side forward/return hop table when an asymmetric path is selected.
  - **Why:** `PathEdge` already supports dual-color rendering (Phase 3); extending to dual-strand keeps the diff small. Asymmetry is an edge property (between two hops), not a node property — node badges would misplace the signal. Toggle-style forward-vs-return loses the at-a-glance "these don't match" view. Side-by-side hop table is the standard ops diagnostic pattern.

### NFN-02 — Route change / asymmetry alerting
- **D-13:** NFN-02 alerts reuse the **Phase 8 Slack dispatcher** (`teams.slack_webhook_url` + the Phase 8 alert job). Phase 12 adds a new severity threshold: fire when **(impact byte-volume > planner-tunable bytes/s threshold)** OR **(affected stateful-firewall count ≥ 1)**. New asymmetries and asymmetries whose root cause changes between recomputes both trigger alerts; flapping is debounced by the 15-min scheduler cadence.
  - **Why:** Same delivery surface as the existing Critical-finding alerts, no new ops mechanism, no new SES/SMTP. Email + in-app inbox are deferred to a future ops phase. Severity threshold matches the "what actually hurts" lens of D-10.

### Read API
- **D-14:** Phase 12 ships a **minimal read API** scoped per-site, Clerk JWT + team-scoped RLS, mirroring Phase 11 D-11:
  - `GET /v1/sites/{site_id}/paths` — latest computed paths per pair (filter by pair, by NetFlow window)
  - `GET /v1/sites/{site_id}/asymmetries` — current asymmetry findings (filter by cause, by min impact)
  - `POST /v1/sites/{site_id}/paths/recompute` — on-demand recompute (owner role)
  - Dashboard UI for browsing asymmetries is deferred (see "Out of scope").

### Storage model
- **D-15:** New backend tables (planner picks final column lists):
  - `computed_paths` — `path_id` PK, `site_id` FK, `pair_src_cidr`, `pair_dst_cidr`, `direction` ('forward'|'return'), `computed_at`, `team_id`, `hops` JSONB (full hop list), `match_evidence` JSONB (NetFlow correlation result)
  - `asymmetry_findings` — `finding_id` PK, `site_id` FK, `team_id`, `forward_path_id` FK, `return_path_id` FK, `cause` ('BGP_LOCAL_PREF'|'ROUTE_LEAK'|'NAT_ASYMMETRY'|'UNKNOWN'), `cause_confidence` numeric, `evidence` JSONB, `impact_bytes_per_sec` numeric, `impact_firewall_count` integer, `first_seen_at`, `last_seen_at`
  - `path_divergence_findings` — `finding_id` PK, `site_id` FK, `team_id`, `expected_path_id` FK, `observed_path` JSONB (synthesized from NetFlow), `evidence` JSONB, `first_seen_at`, `last_seen_at`
  - All three tables: RLS via `team_id = current_setting('app.current_team_id', true)::uuid`, GRANT to `infracanvas_app`, mirrors Phase 11 D-08/D-15 pattern.
- **D-16:** **Snapshot-per-pull semantics, not append-only**: each scheduled recompute fully replaces the `computed_paths` for that site and reconciles `asymmetry_findings` / `path_divergence_findings` (insert new, update `last_seen_at` on still-present, mark closed on no-longer-present via a `resolved_at` column).
  - **Why:** Matches Phase 11 D-10 model for `firewall_ruleset_snapshots`. Append-only paths would balloon storage and never reflect "is the asymmetry still happening." Findings keep first/last/resolved timestamps so NFN-02 can fire on state transitions.

### Claude's Discretion
- Top-K value for NetFlow pair selection (suggest K=200, env-overridable)
- Snapshot retention TTL for `computed_paths` (suggest 14 days, mirror Phase 11 firewall snapshots)
- Per-cause evidence-rule details (which BGP attrs map to LOCAL_PREF, what counts as a ROUTE_LEAK, what NAT mismatch shapes trigger NAT_ASYMMETRY) — planner researches and proposes in RESEARCH.md
- NFN-02 byte-volume threshold default + override surface (env var vs per-team setting) — planner picks env var to start, per-team in a later phase
- Internal Python module layout under `cli/infracanvas/security/network/` for NET-010 — planner picks (one module vs split detector/engine)
- Exact dual-strand edge offset / red dashed stroke styling in `PathEdge` — planner picks per visual review
- Whether NetFlow window math runs against raw flow records or a pre-aggregated rollup table — planner researches existing Phase 10 flow storage shape
- Backoff/jitter on the 15-min scheduler tick to avoid thundering-herd across many sites — planner picks
- Whether `POST /v1/sites/{site_id}/paths/recompute` returns 202 + job_id or 200 + result — planner picks per existing taskiq pattern
- Coalescing strategy for concurrent on-demand recomputes (per-site lock vs queue dedup) — planner picks

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements + roadmap
- `.planning/REQUIREMENTS.md` §"Category 12 — Path Computation + Asymmetric Routing (PTH / ASY)" (lines 106-114) — PTH-01..03, ASY-01..03, NET-010 full requirement text
- `.planning/REQUIREMENTS.md` §"Category 13 — FlowMap Viewer Additions" (lines 116-119) — FMV-02, NFN-02
- `.planning/ROADMAP.md` §"Phase 12: Path Computation + Asymmetric Routing" — goal, success criteria, dependency on Phase 10 + Phase 11
- `.planning/PROJECT.md` lines 82-83 — Path computation + asymmetric routing as part of FlowMap 3b scope

### Phase 11 contract (firewall data — primary input)
- `.planning/phases/11-firewall-integration/11-CONTEXT.md` — D-08 hybrid `firewall_rules` schema (normalized + raw_blob), D-10 snapshot-per-pull, D-15 "Phase 12 forward-feed contract — DO NOT RENAME columns". **MUST read before planning.**
- `backend/migrations/versions/20260510_011_firewall_tables.py` — `firewall_ruleset_snapshots`, `firewall_rules`, `firewall_nat_rules`, `firewall_objects` schemas. Phase 12 queries these (latest snapshot per `firewall_id`).
- `backend/app/db/models.py` — `FirewallRulesetSnapshot`, `FirewallRuleORM`, `FirewallNATRuleORM`, `FirewallObjectORM` (lines 195-320)
- `backend/app/routes/firewalls.py` — Clerk-JWT read pattern Phase 12 read API mirrors

### Phase 10 contract (DC agent data — primary input)
- `.planning/phases/10-dc-agent-core/10-CONTEXT.md` — D-04 site-token Bearer auth, D-07 in-memory NetFlow ring buffer + retry-twice-then-drop, D-08 JSON-over-HTTPS push to `POST /v1/agent/routes` and `POST /v1/agent/flows`. **MUST read before planning.**
- `backend/migrations/versions/20260507_010_dc_sites.py` — `dc_sites` table (RLS-scoped)
- `backend/app/routes/agent.py` — site-token-authed ingest routes; Phase 12 does NOT add new ingest, only consumes
- `agent/internal/netconf/types.go` — `RouteRecord` shape (prefix, next_hop, protocol, metric, as_path) — the input Phase 12 path computation reads server-side after agent push

### Existing Pydantic data model (computation output target)
- `cli/infracanvas/graph/models.py` — `NetworkPath` (line 141), `PathHop` (line 125), `NetworkFinding` (line 100), `ResourceGraph.network_paths` field (line 179). Phase 12 backend uses these shapes (planner decides whether to re-declare them in `backend/app/schemas/` or import — favour re-declaring to keep CLI ↔ backend decoupled).
- `cli/infracanvas/graph/models.py` line 153-170 — `DCSite`, `DCCollectorReading` for site-level grouping

### FlowMap viewer (FMV-02 integration point)
- `viewer/src/components/flowmap/edges/PathEdge.tsx` — existing dual-color edge component Phase 12 extends to dual-strand + dashed-red
- `viewer/src/components/flowmap/PathDetailPanel.tsx` — existing detail panel Phase 12 extends with side-by-side forward/return hop table
- `viewer/src/components/flowmap/FlowMapCanvas.tsx` — existing canvas; no schema change expected, only edge style updates
- `viewer/src/__tests__/flowmap/PathEdge.test.tsx` and `PathDetailPanel.test.tsx` — test patterns to extend

### NET-010 reservation site
- `cli/tests/test_flowmap_network_rules.py:71` — `test_net_010_reserved_for_phase_3b` (this test trips when NET-010 lands; Phase 12 plan updates the assertion intentionally)
- `cli/tests/test_security.py:64` — additional NET-010 reservation comment
- `cli/infracanvas/security/` — engine + rules root; Phase 12 creates `network/` subpackage for path-aware Python detectors

### Phase 8 alerting reuse (NFN-02)
- `.planning/phases/08-github-webhook-autoscan/` — Slack alert dispatcher pattern Phase 12 reuses; planner reads the SUMMARY/CONTEXT/PLAN files there
- `backend/migrations/versions/20260505_009_slack_webhook_url.py` — `teams.slack_webhook_url` column (already in place)
- `backend/app/routes/firewalls.py` and `backend/app/queue/tasks/firewall_prune.py` — existing taskiq job patterns Phase 12 mirrors

### Existing scan worker / queue patterns
- `backend/app/queue/tasks/` — directory containing taskiq job definitions (firewall_prune, GitHub auto-scan); Phase 12 adds `path_compute.py` here
- Phase 11 D-19 — taskiq scheduler registration (planner reads existing scheduler config)

### Vendor-neutral routing references (planner researches)
- BGP best-path selection (LOCAL_PREF / AS_PATH / MED / origin) — classifier evidence for BGP_LOCAL_PREF cause
- Route-leak fingerprint (more-specific prefix from a peer it shouldn't originate, AS path anomalies) — classifier evidence for ROUTE_LEAK
- Symmetric vs asymmetric NAT pinholes through stateful firewalls — classifier evidence for NAT_ASYMMETRY

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `cli/infracanvas/graph/models.py` `NetworkPath`, `PathHop`, `NetworkFinding`, `DCSite` — Pydantic v2 models already shaped for this phase. `NetworkPath.direction` is already `"forward"|"return"`; `PathHop.bgp_as_path` and `next_hop` are already present.
- `backend/app/db/models.py` Phase 11 firewall ORMs — Phase 12 queries `FirewallRulesetSnapshot` for latest snapshot per firewall, joins `FirewallRuleORM` + `FirewallNATRuleORM` for path-policy + NAT evaluation.
- `backend/app/queue/tasks/firewall_prune.py` — taskiq scheduled-job precedent; Phase 12 path-compute job follows the same shape (scheduler decorator, RLS GUC set, structured logging).
- `viewer/src/components/flowmap/edges/PathEdge.tsx` — dual-color edge already in place from Phase 3; Phase 12 extends to dual-strand with dashed-red asymmetric leg.
- `viewer/src/components/flowmap/PathDetailPanel.tsx` — existing panel + test suite Phase 12 extends.
- Phase 8 Slack alert dispatcher (under `backend/app/queue/tasks/` or equivalent — planner confirms) — Phase 12 reuses for NFN-02.

### Established Patterns
- **Backend-side compute over agent-pushed data** — Phase 9 CostLens precedent (idle detector, egress estimator) runs server-side over scan data; Phase 12 follows the same model over agent data.
- **Snapshot-per-pull / snapshot-per-compute, full-replace** — Phase 10 routes + Phase 11 firewall rules already use this; Phase 12 `computed_paths` extends it.
- **Findings reconciliation with `first_seen_at` / `last_seen_at` / `resolved_at`** — planner picks the exact column set; the principle is "transitions trigger alerts, not every recompute."
- **RLS-scoped reads via `current_setting('app.current_team_id', true)::uuid`** — established Phase 6+, used by Phase 10 (`dc_sites`) and Phase 11 (`firewall_*`). Phase 12 mirrors verbatim.
- **Clerk JWT for dashboard reads, site-token for agent ingest** — Phase 12 read API is Clerk-only (no new ingest).
- **TDD discipline** — Phase 10/11 backend additions landed via RED→GREEN pytest with RLS coverage. Phase 12 follows the same pattern; Go viewer changes follow Vitest TDD.

### Integration Points
- **Backend ingest** — Phase 12 does NOT add new agent ingest endpoints. All inputs come from Phase 10 routes/flows and Phase 11 firewall data already in the DB.
- **Backend read API** — `GET /v1/sites/{site_id}/paths`, `GET /v1/sites/{site_id}/asymmetries`, `POST /v1/sites/{site_id}/paths/recompute` register in `backend/app/main.py` alongside the Phase 11 firewall read routes.
- **NET-010 reservation test** — `cli/tests/test_flowmap_network_rules.py:71` (`test_net_010_reserved_for_phase_3b`) updates intentionally when Phase 12 detector lands; Phase 12 plan must change the assertion.
- **Rules catalog count** — `cli/tests/test_security.py:64` and related catalog tests expect 51 rules today; Phase 12 raises the floor to 52. Update the count assertion.
- **FlowMap viewer schema** — `ResourceGraph.network_paths` stays empty for CLI offline scans (no agent data). Dashboard renders paths via a new fetch from the read API; planner picks the exact viewer-prop wiring (likely a store action that hydrates `network_paths` after dashboard fetch).
- **Slack alert dispatcher** — NFN-02 alerts route through the existing Phase 8 dispatcher; planner adds a new alert type/template, not a new transport.
- **Scan JSON contract** — Phase 12 does NOT modify the v2.1 ResourceGraph schema. `network_paths` field stays in the schema (already present from Phase 1) but is populated only by the dashboard fetcher, not by `infracanvas scan`.

</code_context>

<specifics>
## Specific Ideas

- New backend taskiq job sketch (planner refines):
  ```python
  # backend/app/queue/tasks/path_compute.py
  @broker.task(schedule=[{"cron": "*/15 * * * *"}])
  async def recompute_paths_all_sites() -> None:
      """Phase 12 D-04: scheduled path recomputation per active DC site."""
      ...

  @broker.task
  async def recompute_paths_for_site(site_id: UUID, *, on_demand: bool = False) -> None:
      """Phase 12 D-04 on-demand path + asymmetry compute for one site."""
      ...
  ```

- Suggested table outlines (planner picks final columns + indexes):
  ```
  computed_paths (
    path_id UUID PK,
    site_id UUID FK -> dc_sites,
    team_id UUID FK -> teams,
    pair_src_cidr TEXT, pair_dst_cidr TEXT,
    direction TEXT CHECK (direction IN ('forward','return')),
    hops JSONB,                  -- list[PathHop]
    match_evidence JSONB,        -- NetFlow correlation result
    computed_at TIMESTAMPTZ,
    UNIQUE (site_id, pair_src_cidr, pair_dst_cidr, direction, computed_at)
  )

  asymmetry_findings (
    finding_id UUID PK,
    site_id UUID FK, team_id UUID FK,
    forward_path_id UUID, return_path_id UUID,
    cause TEXT CHECK (cause IN ('BGP_LOCAL_PREF','ROUTE_LEAK','NAT_ASYMMETRY','UNKNOWN')),
    cause_confidence NUMERIC,
    evidence JSONB,              -- non-winning scores + raw signal
    impact_bytes_per_sec NUMERIC,
    impact_firewall_count INTEGER,
    first_seen_at TIMESTAMPTZ,
    last_seen_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ NULL
  )

  path_divergence_findings (
    finding_id UUID PK,
    site_id UUID FK, team_id UUID FK,
    expected_path_id UUID,
    observed_path JSONB,         -- synthesized from NetFlow
    evidence JSONB,
    first_seen_at TIMESTAMPTZ,
    last_seen_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ NULL
  )
  ```
  All three: RLS ENABLE + FORCE + policy on `team_id`, GRANT to `infracanvas_app`, mirroring Phase 11 D-08.

- NET-010 Python detector sketch (planner refines):
  ```python
  # cli/infracanvas/security/network/net_010.py
  def detect_stateful_firewall_asymmetry(
      forward: NetworkPath,
      ret: NetworkPath,
      stateful_firewalls: set[str],
  ) -> list[NetworkFinding]:
      """NET-010 / ASY-03: stateful firewall sees only one leg of an asymmetric pair."""
      ...
  ```

- Classifier evidence rules (planner researches and pins specific signals):
  - **BGP_LOCAL_PREF:** forward + return next_hops resolve through routers with mismatched LOCAL_PREF values on the same prefix; bgp_as_path differs on the return leg
  - **ROUTE_LEAK:** more-specific prefix advertised by an unexpected peer; AS path contains an upstream that shouldn't originate the prefix
  - **NAT_ASYMMETRY:** forward path transits a NAT rule whose return-side translation pinhole doesn't exist (firewall_nat_rules) or is mapped via a different interface pair

- FMV-02 styling sketch:
  - Forward strand: existing solid color (zone-based)
  - Return strand: same color, parallel offset of ~6px, solid for symmetric, **dashed red `#DC2626`** for asymmetric segments
  - Hover: highlight both strands; PathDetailPanel shows side-by-side hop table with mismatched-row highlight

- NFN-02 alert template (planner refines):
  ```
  🔴 Asymmetric path detected — site {site_name}
  Pair: {src_cidr} → {dst_cidr}
  Cause: {cause}  (confidence {confidence:.0%})
  Impact: {bytes_per_sec_human} / {firewall_count} stateful firewall(s)
  View: {dashboard_url}/sites/{site_id}/asymmetries/{finding_id}
  ```

- Read API auth model:
  - All three Phase 12 endpoints use Clerk JWT + `resolve_team_from_clerk_org` (Phase 6/7 precedent)
  - `POST .../paths/recompute` adds `require_role("owner")` (matches Phase 10 D-03 site creation gate)
  - RLS GUC set per-request via existing middleware; no new auth code

- Tests checklist for planner (RED→GREEN per task):
  - Path compute job correctness over fixture route + firewall + NAT data
  - NetFlow correlation: endpoint+edge-hop matcher behaviour on partial NetFlow data
  - Classifier evidence-score + tiebreaker + UNKNOWN fallback
  - Impact scoring against fixture NetFlow window
  - Findings reconciliation: new / still-present / resolved transitions
  - NFN-02 alert fires on transitions, debounces flapping
  - NET-010 detector emits findings with `rule_id="NET-010"`
  - Reservation test update intentionally trips and is fixed in the same plan
  - PathEdge dual-strand renders; dashed-red on asymmetric leg
  - PathDetailPanel side-by-side hop table renders
  - Read API endpoints: 200 happy path, 403 cross-team, 404 missing site
  - On-demand recompute coalesces concurrent calls

</specifics>

<deferred>
## Deferred Ideas

- **Cloud↔Cloud paths (TGW peering, ExpressRoute cross-cloud)** — Hybrid edge is the v1.1 pain point; cross-cloud paths add scope without proven demand. Revisit when multi-cloud customers ask.
- **DC↔DC intra-site paths** — Mostly L2/MPLS opacity; computed paths would be low-quality. Defer until ops collectors can see intra-DC topology.
- **Cartesian path computation over all declared subnet pairs** — Top-K by NetFlow volume covers what actually matters. Re-evaluate when a customer needs zero-traffic compliance evidence.
- **Embedding computed paths into the scan JSON `ResourceGraph.network_paths` field** — Offline CLI scans continue to render empty `network_paths`. Wire dashboard fetcher → store hydration only. Revisit if customers ask for "share link includes paths."
- **Multi-label root cause classification** — One cause per finding is what the alert wording supports. Revisit if false-attribution incidents accumulate.
- **Email or in-app inbox alert channels for NFN-02** — Slack-only reuse in v1.1. Email/inbox land in a future ops phase.
- **Path-pattern operators in the YAML rule engine** — Materially expands the engine for one rule. NET-010 ships as Python detector; revisit if more path-aware rules accumulate.
- **Real-time recomputation on every route/firewall push** — Push-triggered would thrash the worker. 15 min + on-demand is sufficient. Revisit if customers ask for sub-minute reactivity.
- **Per-team NFN-02 byte-volume threshold setting** — Env-var default first. Per-team override lands when product/Settings UI catches up.
- **Dashboard UI for browsing asymmetries** — Read API only in this phase. UI lands in a later dashboard hardening phase, parallel to Phase 11 D-11.
- **Diff-based snapshot storage for `computed_paths`** — Snapshot-per-compute is simpler; revisit if storage cost becomes a real concern.
- **Auto-recovery / self-healing suggestions** — "Asymmetric — try flipping LOCAL_PREF to 200" is a v1.2+ feature.
- **Cause precedence override per-team** — Some shops genuinely want LOCAL_PREF first. Defer until a customer asks.
- **Cross-pair correlation** — "These 5 asymmetries share a common upstream router" rollups. Defer; per-pair findings cover the v1.1 promise.
- **Pinning a specific NetFlow rollup table vs raw flow records** — Planner researches existing Phase 10 flow storage; chosen approach captured in PLAN.md, not pre-decided here.

</deferred>

---

*Phase: 12-Path Computation + Asymmetric Routing*
*Context gathered: 2026-05-17*
