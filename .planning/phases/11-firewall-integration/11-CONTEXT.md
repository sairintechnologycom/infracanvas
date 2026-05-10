# Phase 11: Firewall Integration - Context

**Gathered:** 2026-05-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Pull rule bases, NAT tables, and policies from Cisco ASA (REST + SSH fallback), Cisco FMC (REST), and Checkpoint Management API into the cloud backend, scoped per-team and per-site. Firewall rule data is the missing input that Phase 12's path computation needs to reason about NAT asymmetry and policy mismatches.

**In scope:**
- New collector packages in the existing Go DC agent: `agent/internal/{asa,fmc,checkpoint}/` (alongside Phase 10's `netconf`, `ssh`, `netflow`, `push`, `config`)
- New `agent.yaml` device protocols (`asa-rest`, `asa-ssh`, `fmc`, `checkpoint`, `checkpoint-import`) reusing the existing `devices[]` array (Phase 10 D-06)
- New 4th interval in the agent loop (`Firewall: 1*time.Hour`) extending Phase 10's DCA-06 timing contract (`Routes: 5m`, `BGP: 1m`, `Flow: 30s`)
- Backend ingest endpoints: `POST /v1/agent/firewall-rules`, `POST /v1/agent/firewall-nat`, `POST /v1/agent/firewall-objects` (snapshot-per-pull, per-device)
- Backend tables: `firewall_rules`, `firewall_nat_rules`, `firewall_objects`, `firewall_ruleset_snapshots` — RLS-scoped to team via existing `dc_sites` site-token middleware
- Backend read API: `GET /v1/sites/{site_id}/firewall-rules` returning latest snapshot per device (Clerk JWT auth) — minimal Phase 12-feeding read path
- ASA REST + SSH protocol-declared per-device (operator picks `asa-rest` or `asa-ssh` explicitly; no auto-fallback)
- Checkpoint Management API session lifecycle: login-per-pull → fetch all data → logout (no long-lived SID)
- Shared Checkpoint policy parser used by both CKP-01 (live API responses) and CKP-02 (offline `mgmt_cli show ... --format json` import via `checkpoint-import` protocol — mirrors Phase 10 `config-import` pattern)
- Update CAB packet (`agent/docs/cab/threat-model.md` from Phase 10 DCA-09) to extend the credential-storage section to firewall mgmt accounts

**Out of scope:**
- Dashboard UI for browsing firewall rules — deferred to a dedicated dashboard hardening phase (still satisfies ROADMAP success criterion 4 via the read API)
- Path computation, NAT asymmetry classification, policy-mismatch detection — Phase 12
- Palo Alto, Fortinet, Juniper SRX firewalls — out of v1.1 scope
- Threat-prevention layers, application control, identity awareness, URL filtering — not on the path-asymmetry path
- Rule simulation, what-if analysis, compliance scoring of rules — v1.2+
- OS-keychain-backed credential storage — defer; Phase 10 plaintext-with-chmod-600 precedent applies (see deferred)
- Long-lived Checkpoint SID with refresh — defer; login-per-pull is sufficient

</domain>

<decisions>
## Implementation Decisions

### Collection topology (ASA-01..03, CKP-01..02)
- **D-01:** Firewall collectors extend the existing Go DC agent (`agent/internal/{asa,fmc,checkpoint}/` packages), they do NOT run cloud-side. Inherits Phase 10's site-token Bearer auth, LAN-only credential storage (chmod 600 `agent.yaml`, Phase 10 D-05), and retry-twice-then-drop push (Phase 10 D-07). Customers already trust the agent for routing data — no new firewall holes punched in their security perimeter, no new credential-storage problem on the SaaS side.
- **D-02:** Polling cadence is **1 hour**, fixed. Firewall rule bases change at change-window cadence, not minute-by-minute. Distinct from DCA-06 timing — extends `Intervals` struct (`agent/cmd/infracanvas-agent/main.go` ~line 47) with `Firewall: 1*time.Hour`. Tests assert all four intervals (Routes/BGP/Flow/Firewall).
- **D-03:** Firewall pulls run on a dedicated 4th goroutine in `run()` (alongside Routes/BGP/Flow tickers), with the same shutdown drain pattern.

### Per-device protocol selection (ASA-01, ASA-03)
- **D-04:** ASA REST vs SSH fallback is **declared per-device** in `agent.yaml` — operator chooses `asa-rest` or `asa-ssh` explicitly. No auto-fallback at runtime. Rationale: deterministic, auditable (CAB-friendly), matches Phase 10's protocol-field model. SSH credentials may differ from REST credentials in practice, so requiring explicit declaration is operationally honest.
- **D-05:** ASA-03 ("SSH fallback") is satisfied by the `asa-ssh` protocol path (parsed `show running-config` → access-lists + NAT). It is a sibling collector, not a try/catch wrapper around `asa-rest`.

### Site mapping (Phase 10 inheritance)
- **D-06:** Firewall pushes use the agent's site_token by default. Per-device `site_id` override (already present in Phase 10 Device struct, `agent/internal/config/config.go:37`) handles the rare case where one agent host fronts multiple physical sites. **Zero new schema** — reuses Phase 10's site mapping.

### NAT data shape (ASA-01 success criterion 1, ASY-02 forward-feed)
- **D-07:** NAT table data lives in a **separate** `firewall_nat_rules` table behind a separate push endpoint (`POST /v1/agent/firewall-nat`). NAT rules are structurally different from access rules (src translation + dst translation + interface mapping vs match/action). Phase 12's NAT_ASYMMETRY classifier (REQUIREMENTS §ASY-02) consumes NAT as a distinct input.

### Backend rule data model (ROADMAP success criterion 4)
- **D-08:** **Hybrid schema** — one `firewall_rules` table with normalized columns (`src_zone`, `dst_zone`, `src_cidr`, `dst_cidr`, `action`, `protocol`, `ports`, `vendor`, `position`) PLUS a `raw_blob` JSONB column preserving the vendor-native rule. Phase 12 path computation queries normalized columns; vendor-specific UI/audit reads `raw_blob`. One schema, no information loss. Same hybrid pattern applies to `firewall_nat_rules`.
- **D-09:** Address objects, service objects, and object-groups are **stored in a separate `firewall_objects` table** with FK references from rule fields. Mirrors how ASA / FMC / Checkpoint actually model rules. Updating an object propagates correctly. Aligns with CKP-01 success criterion 3 ("rule base + objects").
- **D-10:** Versioning model is **snapshot-per-pull (full replace)** — each hourly pull writes a new `firewall_ruleset_snapshots` row keyed by `(site_id, firewall_id, snapshot_ts)` with the full rule list under it. Old snapshots retained ~30 days (TTL TBD by planner). Matches how ASA/FMC/Checkpoint actually deploy rules (atomic units replaced wholesale on push). Phase 12 always queries "latest snapshot per `firewall_id`."
- **D-11:** Phase 11 ships **ingest + minimal read API**. `GET /v1/sites/{site_id}/firewall-rules` returns latest snapshot per device, scoped by team via Clerk JWT. Demonstrates ROADMAP success criterion 4 ("All rule sets visible in cloud backend, tied to team + site"). Dashboard UI is deferred.

### CKP-02 — Checkpoint rule-base export parser
- **D-12:** **Single shared parser** for both live API responses (CKP-01) and offline export imports (CKP-02). Parser is a pure function over Checkpoint policy JSON. CKP-01 feeds it live response JSON; CKP-02 adds a `checkpoint-import` protocol where the customer dumps `mgmt_cli show access-rulebase --format json` (and equivalents for objects + NAT) to a file path declared in `agent.yaml` (mirrors Phase 10 D-06 `config-import`). Air-gapped Checkpoint customers are covered by the same parser the API path uses.
- **D-13:** Phase 11 covers **access rulebase + NAT rulebase + objects (host/network/group/service)** for Checkpoint. Skip threat-prevention layers, application control, identity awareness — they are not on the path-asymmetry path.
- **D-14:** Checkpoint Management API session lifecycle is **login-per-pull, logout-when-done**. Each hourly pull does login → fetch all data → logout. SID lives only for the pull duration. Stateless between pulls, no on-disk token storage problem, matches how Checkpoint operators use `mgmt_cli` scripts. Login is cheap and not a hot path.

### FMC × direct ASA precedence
- **D-15:** FMC and direct ASA REST are **independent sources**. Backend stores rules per-device keyed by serial/UUID. If FMC reports rules for a managed ASA AND we also pull that ASA directly, both writes hit the same `firewall_id` and the most recent pull wins under D-10's snapshot-per-pull model. Operators choose what to configure. Rule-base drift between FMC and ASA (a real diagnostic signal) remains visible in the snapshot history.

### agent.yaml shape and credential storage
- **D-16:** Firewalls extend the existing `devices[]` array via new protocol values: `asa-rest`, `asa-ssh`, `fmc`, `checkpoint`, `checkpoint-import`. Reuses the existing `Device` struct (`agent/internal/config/config.go:30`) — same `host`/`port`/`username`/`password`/`site_id` fields. Validation extends the protocol switch (`config.go:65`). **Zero new schema**, smallest diff, operators see firewalls and routers in one place.
- **D-17:** Firewall mgmt credentials use the **same storage model as Phase 10 device credentials** — plaintext in `agent.yaml`, chmod 600. CAB packet (DCA-09 `agent/docs/cab/threat-model.md`) extends the credential-storage section to firewall mgmt accounts with the same rationale: credentials never leave the agent host, filesystem permissions are the trust boundary, ops uses read-only mgmt accounts. Consistency with Phase 10 D-05 over extra mechanism.

### Push endpoint shape
- **D-18:** Three push endpoints, one per data type — `POST /v1/agent/firewall-rules`, `POST /v1/agent/firewall-nat`, `POST /v1/agent/firewall-objects`. Each payload is a snapshot for one device. Mirrors Phase 10 D-08 per-data-type endpoint pattern (`POST /v1/agent/routes`, `POST /v1/agent/flows`). Aligns with the separate-NAT-table (D-07) and separate-objects-table (D-09) decisions.
- **D-19:** Push payloads are JSON-over-HTTPS with `Authorization: Bearer <site_token>` (Phase 10 D-04). Retry-twice-then-drop on failure (Phase 10 D-07).

### Claude's Discretion
- Snapshot retention TTL specifics (default ~30 days suggested) — planner picks exact value with rationale; configurable via env or migration default.
- Internal package layout within `agent/internal/asa/` (e.g., separate `rest.go` + `ssh.go` files vs separate sub-packages) — planner picks idiomatic Go.
- ASA REST API version targeting and FMC API version pinning — planner researches current stable versions and picks defaults; documents in collector package README.
- Specific FastAPI route handler structure — follow `backend/app/routes/github.py` precedent (Clerk JWT for read API, site-token middleware for ingest endpoints).
- Pydantic model shapes for the three push payloads — planner derives from D-08/09 schema.
- Alembic migration naming and column-level details (indexes on `(site_id, firewall_id, snapshot_ts)`, JSONB indexes on `raw_blob` if needed) — planner decides per existing migration conventions.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements + roadmap
- `.planning/REQUIREMENTS.md` §"Category 11 — Firewall / Security Device Integration" (lines 98-104) — ASA-01..03, CKP-01..02 full requirement text
- `.planning/ROADMAP.md` §"Phase 11: Firewall Integration" (lines 339-348) — goal, success criteria, dependency on Phase 10
- `.planning/PROJECT.md` lines 79-80 — Cisco ASA + Checkpoint integrations as part of FlowMap 3b scope

### Phase 10 inheritance (foundation for Phase 11)
- `.planning/phases/10-dc-agent-core/10-CONTEXT.md` — site-token auth (D-03/04), agent.yaml protocol model (D-06), retry-twice-then-drop push (D-07), JSON-over-HTTPS endpoint pattern (D-08), shared semver tag releases (D-02), credential storage model (D-05). **MUST read before planning.**
- `agent/cmd/infracanvas-agent/main.go` — existing agent entry point with `Intervals` struct, ticker-based goroutines, shutdown drain (Phase 11 4th ticker hooks in here)
- `agent/internal/config/config.go:30` — `Device` struct that Phase 11 extends with new protocol values (lines 17-19 list current protocols)
- `agent/internal/config/config.go:65` — protocol validation switch that Phase 11 extends
- `agent/internal/push/` — Bearer-token push client with retry-twice-then-drop; Phase 11 firewall pushes reuse this client

### Backend (push targets + read API host)
- `backend/app/main.py` — FastAPI app entrypoint; new `/v1/agent/firewall-*` and `/v1/sites/{id}/firewall-rules` routes register here
- `backend/app/routes/github.py` — Clerk JWT + RLS pattern; the new read API follows the same skeleton
- `backend/app/routes/` — existing route handler pattern (`scans.py`, `github.py`); new agent push routes follow the same structure with site-token middleware instead of Clerk JWT
- `backend/alembic/versions/` — migration naming pattern; new `firewall_rules`, `firewall_nat_rules`, `firewall_objects`, `firewall_ruleset_snapshots` migrations follow prior conventions
- Phase 10 site-token validation middleware (added in Phase 10 plans 10-02/10-03) — reused verbatim for the three firewall ingest endpoints

### CAB packet
- `agent/docs/cab/threat-model.md` (Phase 10 DCA-09 deliverable) — Phase 11 must EXTEND this with firewall mgmt credential rationale; do NOT create a new packet
- `agent/docs/cab/architecture.md` (Phase 10) — extend with firewall data flow
- `agent/docs/cab/data-flow.md` (Phase 10) — extend with firewall pull → push pipeline
- `.planning/REQUIREMENTS.md` §DCA-09 — original CAB deliverable scope

### GHA release workflow (no Phase 11 change expected, but verify)
- `.github/workflows/` — Phase 10 cross-compiled agent binaries via D-02 shared semver tag; Phase 11 adds source files but no new artifacts

### Vendor API references (planner researches; planner adds specific URLs to RESEARCH.md)
- Cisco ASA REST API documentation (current stable; ASA 9.x+) — for ASA-01
- Cisco FMC REST API + token lifecycle docs — for ASA-02
- Cisco ASA SSH `show running-config` parsing approach — for ASA-03 (note: SSH-extracted access-lists, no separate NAT command)
- Checkpoint Management API (`mgmt_cli` JSON over HTTPS), session lifecycle, `show access-rulebase` / `show nat-rulebase` / `show objects` shapes — for CKP-01/CKP-02
- Existing Phase 10 `nemith.io/netconf` precedent for vendoring — Phase 11 picks Go libraries with similar maturity bar

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `agent/internal/push/Client` (Phase 10 plan 10-07) — Bearer-token JSON push client with retry-twice-then-drop. Phase 11 firewall pushes get **three new methods** (`PushFirewallRules`, `PushFirewallNAT`, `PushFirewallObjects`) following the existing `PushRoutes` / `PushFlows` shape.
- `agent/internal/config/Config` + `Device` (Phase 10 plan 10-03) — the YAML-loading + validation layer that Phase 11 extends with new protocol values. No new top-level field.
- `agent/internal/config/import.go` (Phase 10 plan 10-05) — `config-import` precedent that the `checkpoint-import` protocol mirrors verbatim. Read this before implementing CKP-02.
- `backend/app/storage/r2.py` `put_bytes` (Phase 10 D-08 reuse) — available if planner decides to also archive raw rule-base snapshots to R2 (not required by Phase 11 success criteria, but cheap to add).

### Established Patterns
- **Per-data-type push endpoints**: Phase 10 split routes and flows into separate endpoints; Phase 11 follows the same pattern (rules / nat / objects).
- **Snapshot-per-pull replace**: Phase 10's route push already follows full-replace semantics; Phase 11 firewall snapshots use the same model with explicit `firewall_ruleset_snapshots` parent rows.
- **Bearer-token + RLS**: Site-token auth + team-scoped RLS established in Phase 8 (webhooks) and Phase 10 (DC agent ingest); Phase 11 reuses the same middleware verbatim.
- **TDD discipline**: All Phase 10 collectors landed via RED→GREEN with `-race` clean. Phase 11 collectors follow the same pattern (Go `testing` + `testify` for the agent, pytest for backend).
- **Hermetic test wiring**: Phase 10 main.go uses `config-import` for hermetic tests because it's a pure file read. Phase 11 should make `checkpoint-import` similarly hermetic for main-loop tests.

### Integration Points
- **agent.yaml protocol switch** (`agent/internal/config/config.go:65`) — Phase 11 extends the case statement with new protocol values. No new struct fields.
- **agent ticker loop** (`agent/cmd/infracanvas-agent/main.go` `run()` function) — Phase 11 adds a 4th ticker + 4th goroutine + corresponding `Intervals.Firewall` field. Same shutdown drain.
- **Backend ingest middleware** — Phase 10's site-token middleware (added in 10-02/10-03) wraps the three new firewall endpoints; planner does NOT re-implement.
- **Backend Clerk JWT middleware** — used unchanged for the read API (`GET /v1/sites/{site_id}/firewall-rules`).
- **Phase 12 forward-feed** — `firewall_rules.normalized columns` + `firewall_nat_rules.normalized columns` are the contract Phase 12 path computation reads. Planner should keep these column names stable; downstream changes are expensive.

</code_context>

<specifics>
## Specific Ideas

- Suggested `agent.yaml` shape (planner refines):
  ```yaml
  devices:
    - host: "asa-edge-01.dc1"
      port: 443
      protocol: asa-rest
      username: "infracanvas-ro"
      password: "REPLACE_ME"

    - host: "asa-edge-02.dc1"
      port: 22
      protocol: asa-ssh           # ASA-03 fallback path
      username: "infracanvas-ro"
      password: "REPLACE_ME"

    - host: "fmc.corp.example"
      port: 443
      protocol: fmc
      username: "infracanvas-ro"
      password: "REPLACE_ME"

    - host: "cp-mgmt.corp.example"
      port: 443
      protocol: checkpoint
      username: "infracanvas-ro"
      password: "REPLACE_ME"

    - host: "cp-mgmt-airgap"
      protocol: checkpoint-import   # CKP-02 offline path
      config_file: "/etc/infracanvas/cp-mgmt-airgap-policy.json"
  ```

- `Intervals` struct extension (planner refines):
  ```go
  type Intervals struct {
      Routes   time.Duration  // 5*time.Minute   (DCA-06)
      BGP      time.Duration  // 1*time.Minute   (DCA-06)
      Flow     time.Duration  // 30*time.Second  (DCA-06)
      Firewall time.Duration  // 1*time.Hour     (Phase 11 D-02)
  }
  ```

- Suggested backend table outline (planner refines column types, indexes, RLS policies):
  ```
  firewall_ruleset_snapshots (snapshot_id PK, site_id, firewall_id, vendor, snapshot_ts, source — 'asa-rest'|'asa-ssh'|'fmc'|'checkpoint'|'checkpoint-import', team_id)
  firewall_rules (rule_id PK, snapshot_id FK, position, src_zone, dst_zone, src_cidr, dst_cidr, action, protocol, ports, raw_blob JSONB)
  firewall_nat_rules (nat_id PK, snapshot_id FK, position, src_translation, dst_translation, interface_in, interface_out, raw_blob JSONB)
  firewall_objects (object_id PK, snapshot_id FK, kind — 'host'|'network'|'group'|'service', name, value JSONB, raw_blob JSONB)
  ```

- CAB packet extension must explicitly call out:
  1. Firewall mgmt credentials never leave the agent host (same as device credentials, Phase 10 D-05)
  2. Only rule-base + NAT + object metadata is transmitted to SaaS — never live traffic, never password material
  3. Transmission is TLS-encrypted via the existing push client
  4. Site token is revocable per-site, which kills firewall ingest along with route/flow ingest
  5. Login-per-pull for Checkpoint means no SID at rest

- "Login-per-pull" for Checkpoint should log SID acquisition + logout at INFO; failure to logout (e.g., timeout after successful pull) should WARN but not fail the pull, since the SID will expire on its own.

- Planner should decide whether each protocol gets its own collector type (`asa.RESTCollector`, `asa.SSHCollector`, `fmc.Collector`, `checkpoint.Collector`) or a single vendor collector with internal protocol switching. The Phase 10 precedent leans toward separate collector types per transport.

</specifics>

<deferred>
## Deferred Ideas

- **Dashboard UI for firewall rule browsing** — `/sites/{site_id}/firewalls` page for ops to inspect rule bases and snapshot history. Phase 11 ships only the read API; UI belongs in a dedicated dashboard hardening phase.
- **Long-lived Checkpoint SID with refresh** — More efficient than login-per-pull, but adds SID lifecycle error surface (forced logouts, version upgrades, HA failovers). Revisit if rate limits or login latency become a real bottleneck.
- **OS keychain credential storage** — Linux libsecret / macOS Keychain integration for `agent.yaml` credentials. Stronger at-rest protection but new OS-specific deps and headless-server compatibility issues. CAB precedent for plaintext-with-chmod-600 is already accepted (Phase 10 D-05).
- **Encrypted credentials with site_token-derived key** — Marginal gain (compromised site_token = compromised creds anyway). Adds key-rotation complexity. Skip.
- **Per-site configurable firewall poll interval** — More knobs in `agent.yaml`. Default 1h is sufficient for v1.1; revisit if customers ask.
- **FMC takes precedence over direct ASA when both configured** — Cleaner config, but rule-base drift between FMC and ASA (a real diagnostic signal) becomes invisible. Phase 11 keeps both as independent sources (D-15); revisit if customers complain about duplicate-ingest cost.
- **Checkpoint threat-prevention layers, application control, identity awareness, URL filtering** — Not on the path-asymmetry path. Could land in a Compliance phase (v1.2).
- **Palo Alto, Fortinet, Juniper SRX firewall integrations** — Out of v1.1 scope. New requirement category in REQUIREMENTS.md when prioritized.
- **Rule simulation / what-if analysis / compliance scoring** — v1.2 Compliance phase.
- **Diff-based snapshot storage** — Storage-efficient alternative to D-10's full-replace snapshots. Reconstruction queries become complex; skip until storage cost is a real concern.
- **Auto-fallback ASA REST → SSH at runtime** — Operator-declared protocol (D-04) keeps the threat model auditable. Auto-fallback obscures which channel produced which rule and complicates the CAB packet.
- **Dashboard UI for site token management** (carried forward from Phase 10 deferred list) — `/settings/sites` page for team owners. Still deferred; Phase 11 doesn't need it because site tokens are reused.
- **mTLS per-site certificates** (carried forward from Phase 10 deferred list) — v1.2 enterprise.
- **Disk-backed NetFlow / firewall pull queue** (analogous to Phase 10 deferred) — Persistent storage that survives agent restarts and longer backend outages. Snapshot-per-pull on a 1h cadence can tolerate single missed pulls; defer.
- **Protobuf push encoding** (carried forward) — Worth revisiting if rule-base payloads become a measurable bandwidth concern.

</deferred>

---

*Phase: 11-Firewall Integration*
*Context gathered: 2026-05-10*
