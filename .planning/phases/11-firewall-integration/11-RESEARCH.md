# Phase 11: Firewall Integration - Research

**Researched:** 2026-05-10
**Domain:** Multi-vendor firewall rule-base extraction (Cisco ASA REST/SSH, Cisco FMC, Checkpoint Mgmt API) + Go DC agent collector framework + FastAPI ingest/read endpoints + RLS-scoped Postgres schema
**Confidence:** HIGH overall (vendor APIs verified against official Cisco/Checkpoint docs and CheckMates community; Phase 10 inheritance verified by reading the actual code)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Collection topology (ASA-01..03, CKP-01..02)**
- **D-01:** Firewall collectors extend the existing Go DC agent (`agent/internal/{asa,fmc,checkpoint}/`); they do NOT run cloud-side. Inherits Phase 10's site-token Bearer auth, LAN-only credential storage (chmod 600 `agent.yaml`), and retry-twice-then-drop push.
- **D-02:** Polling cadence is **1 hour, fixed**. Extends `Intervals` struct (`agent/cmd/infracanvas-agent/main.go` line 44) with `Firewall: 1*time.Hour`. Tests assert all four intervals.
- **D-03:** Firewall pulls run on a dedicated 4th goroutine in `runDaemonWithIntervals()` alongside Routes/BGP/Flow tickers, with the same shutdown drain pattern.

**Per-device protocol selection (ASA-01, ASA-03)**
- **D-04:** ASA REST vs SSH is **declared per-device** in `agent.yaml` — operator picks `asa-rest` or `asa-ssh` explicitly. No auto-fallback at runtime.
- **D-05:** ASA-03 ("SSH fallback") is satisfied by the `asa-ssh` protocol path (parsed `show running-config` → access-lists + NAT). Sibling collector, not a try/catch wrapper.

**Site mapping (Phase 10 inheritance)**
- **D-06:** Firewall pushes use the agent's site_token by default. Per-device `site_id` override (already present in Phase 10 Device struct, `agent/internal/config/config.go:37`). **Zero new schema** — reuses Phase 10's site mapping.

**NAT data shape (ASA-01 success criterion 1, ASY-02 forward-feed)**
- **D-07:** NAT lives in a **separate** `firewall_nat_rules` table behind a separate push endpoint (`POST /v1/agent/firewall-nat`).

**Backend rule data model (ROADMAP success criterion 4)**
- **D-08:** **Hybrid schema** — one `firewall_rules` table with normalized columns (`src_zone`, `dst_zone`, `src_cidr`, `dst_cidr`, `action`, `protocol`, `ports`, `vendor`, `position`) + a `raw_blob` JSONB column preserving the vendor-native rule. Same hybrid pattern for `firewall_nat_rules`.
- **D-09:** Address objects, service objects, and object-groups stored in a separate `firewall_objects` table with FK references from rule fields.
- **D-10:** Versioning is **snapshot-per-pull (full replace)** — each hourly pull writes a new `firewall_ruleset_snapshots` row keyed by `(site_id, firewall_id, snapshot_ts)`. Old snapshots retained ~30 days (TTL planner picks).
- **D-11:** Phase 11 ships **ingest + minimal read API**. `GET /v1/sites/{site_id}/firewall-rules` returns latest snapshot per device, scoped by team via Clerk JWT. Dashboard UI deferred.

**CKP-02 — Checkpoint rule-base export parser**
- **D-12:** **Single shared parser** for both live API responses (CKP-01) and offline export imports (CKP-02). CKP-02 uses a `checkpoint-import` protocol mirroring Phase 10 `config-import`.
- **D-13:** Phase 11 covers **access rulebase + NAT rulebase + objects (host/network/group/service)** for Checkpoint. Skip threat-prevention layers, application control, identity awareness.
- **D-14:** Checkpoint Management API session lifecycle is **login-per-pull, logout-when-done**. SID lives only for the pull duration.

**FMC × direct ASA precedence**
- **D-15:** FMC and direct ASA REST are **independent sources**. Most recent pull wins under D-10's snapshot-per-pull model. Drift between FMC and ASA remains visible in snapshot history.

**agent.yaml shape and credential storage**
- **D-16:** Firewalls extend the existing `devices[]` array via new protocol values: `asa-rest`, `asa-ssh`, `fmc`, `checkpoint`, `checkpoint-import`. Reuses the existing `Device` struct. Validation extends the protocol switch (`config.go:65`). **Zero new schema**.
- **D-17:** Firewall mgmt credentials use the **same storage model as Phase 10** — plaintext in `agent.yaml`, chmod 600. CAB packet (DCA-09 `agent/docs/cab/threat-model.md`) **EXTENDS** the credential-storage section (do NOT create a new packet).

**Push endpoint shape**
- **D-18:** Three push endpoints — `POST /v1/agent/firewall-rules`, `POST /v1/agent/firewall-nat`, `POST /v1/agent/firewall-objects`. Mirrors Phase 10 D-08 per-data-type endpoint pattern.
- **D-19:** Push payloads are JSON-over-HTTPS with `Authorization: Bearer <site_token>`. Retry-twice-then-drop on failure.

### Claude's Discretion
- Snapshot retention TTL specifics (default ~30 days suggested) — planner picks exact value, configurable via env or migration default.
- Internal package layout within `agent/internal/asa/` (separate `rest.go` + `ssh.go` files vs sub-packages) — planner picks idiomatic Go.
- ASA REST API version targeting and FMC API version pinning — planner picks defaults; documents in collector package README.
- Specific FastAPI route handler structure — follow `backend/app/routes/agent.py` precedent.
- Pydantic model shapes for the three push payloads — planner derives from D-08/09 schema.
- Alembic migration naming and column-level details (indexes on `(site_id, firewall_id, snapshot_ts)`, JSONB indexes on `raw_blob` if needed) — planner decides per existing conventions.

### Deferred Ideas (OUT OF SCOPE)
- Dashboard UI for firewall rule browsing — dedicated dashboard hardening phase.
- Long-lived Checkpoint SID with refresh — login-per-pull is sufficient.
- OS keychain credential storage — plaintext-with-chmod-600 precedent stands.
- Encrypted credentials with site_token-derived key.
- Per-site configurable firewall poll interval.
- FMC takes precedence over direct ASA when both configured — keep both as independent sources.
- Checkpoint threat-prevention layers, application control, identity awareness, URL filtering — Compliance phase v1.2.
- Palo Alto, Fortinet, Juniper SRX firewall integrations — out of v1.1 scope.
- Rule simulation / what-if analysis / compliance scoring — v1.2.
- Diff-based snapshot storage.
- Auto-fallback ASA REST → SSH at runtime.
- Dashboard UI for site token management.
- mTLS per-site certificates.
- Disk-backed firewall pull queue.
- Protobuf push encoding.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ASA-01 | Cisco ASA REST API client | "Standard Stack" specifies token-based auth via `POST /api/tokenservices` (X-Auth-Token); endpoints `/api/objects/networkobjects`, `/api/objects/networkobjectgroups`, `/api/access/in/{ifc_name}/rules`, `/api/nat`. **HARD CONSTRAINT: REST API is end-of-life at ASA 9.16** — see Risk landmines. |
| ASA-02 | Cisco FMC REST API client | Token lifecycle: `POST /api/fmc_platform/v1/auth/generatetoken` returns X-auth-access-token (30min TTL) + X-auth-refresh-token (refresh up to 3× → effective 90min lifetime). Endpoints under `/api/fmc_config/v1/domain/{DOMAIN_UUID}/policy/accesspolicies/...`. Library: `github.com/netascode/go-fmc` available; net/http suffices. |
| ASA-03 | Cisco ASA SSH fallback | `golang.org/x/crypto/ssh` (canonical); pty modes with `ECHO=0` (Phase 10 precedent in T-10-05-02); `terminal pager 0` (ASA syntax — note: NOT `terminal length 0` which is IOS) before `show running-config`. Parser extracts `access-list ...`, `nat (...) ...`, `object network ...`, `object-group ...` lines. **Becomes the primary path for ASA 9.18+** because REST is EOL. |
| CKP-01 | Checkpoint Management API integration | Login `POST /web_api/login` → returns `sid`; pass `X-chkp-sid` header on subsequent calls. `show-access-rulebase` (max limit=500, paginate via offset), `show-nat-rulebase`, `show-objects`. Layer name required — fetch via `show-access-layers` first. Logout `POST /web_api/logout`. Default session-timeout 600s (D-14 login-per-pull lives well within). |
| CKP-02 | Checkpoint rule-base export parser | `mgmt_cli show access-rulebase --format json -r true` produces same JSON shape as the API (rule UID, rule-number, source-ranges, destination-ranges, type:"access-rule"|"access-section"). Reuse Phase 10 `agent/internal/config/import.go` file-read pattern. Shared parser package consumed by both `live.go` and `import.go`. |

</phase_requirements>

## Summary

Phase 11 sits cleanly on Phase 10's foundation: site-token Bearer auth (`require_site_token` in `backend/app/routes/agent.py`), the `Device` + `Config` YAML loader (`agent/internal/config/config.go`), the retry-twice-then-drop push client (`agent/internal/push/Client`), and the ticker harness (`runDaemonWithIntervals` in `agent/cmd/infracanvas-agent/main.go`). The phase adds three new collector packages, three new backend ingest endpoints, one read endpoint, four new tables, a 4th ticker, and an extension to the Phase 10 CAB packet.

The single biggest risk landmine surfaced during research: **the Cisco ASA REST API is end-of-life at ASA software 9.16.** [VERIFIED: Cisco] For ASA 9.18+, customers are forced to the SSH path, which means ASA-03 ("SSH fallback") is mis-named — it is the *primary* path for any modern ASA deployment. The implementation does not change (CONTEXT.md D-04/D-05 already make `asa-ssh` a sibling collector, not a fallback wrapper), but planner messaging and CAB packet language should reflect that operators of ASA 9.18+ MUST configure `protocol: asa-ssh`.

Cisco FMC and Checkpoint Mgmt API are both stable, well-documented JSON-over-HTTPS APIs with bounded pagination (max-page 500 for Checkpoint, marker-style for FMC). Both have idiomatic Go HTTP usage — no exotic transports. The `mgmt_cli show access-rulebase --format json` output shape matches the live API response shape verbatim, validating CONTEXT.md D-12's "single shared parser" premise.

**Primary recommendation:** Decompose Phase 11 into 4 waves (Wave 1: backend schema + 3 push endpoints + read endpoint; Wave 2: shared agent push-client methods + protocol enum extension + 4th ticker scaffolding; Wave 3: per-vendor collectors in parallel; Wave 4: ticker wiring + CAB extension). Implement Checkpoint as a single `agent/internal/checkpoint/` package with `live.go`, `import.go`, and a shared `parser.go` consumed by both. Implement ASA as `agent/internal/asa/` with `rest.go` and `ssh.go` siblings (matches Phase 10 precedent of separate netconf/ssh packages but co-located here because they target the same vendor). FMC as its own `agent/internal/fmc/` package.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Firewall vendor API extraction | DC Agent (Go) | — | D-01: stays on the LAN; credentials never leave host. Same trust boundary Phase 10 establishes. |
| Snapshot transmission | DC Agent → API (HTTPS push) | — | Reuses Phase 10 push client; Bearer site-token auth at TB-2. |
| Snapshot persistence | API / Backend (FastAPI + Alembic) | Postgres (Neon) | RLS-scoped to team via existing `dc_sites` middleware. |
| Snapshot retention TTL | Database / Storage | Backend cron / job (planner picks) | D-10: 30-day default; choices below in §Don't Hand-Roll. |
| Read API for cloud consumers | API / Backend (FastAPI) | — | Clerk JWT, RLS-scoped — same pattern as `backend/app/routes/scans.py`. |
| Phase 12 forward-feed (path computation) | API / Backend (read API consumer) | — | Phase 12 reads `firewall_rules.normalized columns` + `firewall_nat_rules.normalized columns`. Column names are a hard contract. |
| Hermetic test substrate | DC Agent (test fixtures + httptest.Server) | — | Phase 10 precedent: file-read protocols (`config-import`, `checkpoint-import`) make main-loop tests deterministic without network. |
| CAB packet (governance artifact) | Repository documentation (`agent/docs/cab/`) | — | Six existing CAB docs at `agent/docs/cab/{architecture,dataflow,threat-model,known-limitations,operator-runbook,README}.md` totaling 918 lines; Phase 11 extends, does not replace. |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `golang.org/x/crypto/ssh` | latest (already vendored by Phase 10 plan 10-05) | ASA SSH transport (`asa-ssh`) | [VERIFIED: Phase 10 precedent — the existing `agent/internal/ssh/` package uses this; T-10-05-02 already locks ECHO=0 for password redaction.] [CITED: pkg.go.dev/golang.org/x/crypto/ssh] Canonical Go SSH client; same library Phase 10 SSH collector uses. |
| `net/http` (stdlib) | go1.22+ (existing toolchain) | ASA REST + FMC REST + Checkpoint Mgmt API HTTP transport | [ASSUMED] No vendor-specific transport quirks for any of the three APIs. All are JSON-over-HTTPS with header auth. The `agent/internal/push/Client` already establishes the in-house pattern (timeout, retry, bearer header) — collectors can follow the same shape. |
| `encoding/json` (stdlib) | go1.22+ | Vendor response parsing for ASA REST / FMC / Checkpoint | [ASSUMED] All three vendors return idiomatic JSON; no XML in scope (NETCONF stays in Phase 10). |
| `gopkg.in/yaml.v3` | already vendored | `checkpoint-import` config-file parsing (mirrors `agent/internal/config/import.go`) | [VERIFIED: Phase 10 precedent — already vendored; T-10-05-06 / T-10-03-02 lock alias-depth limits.] |
| `go.uber.org/zap` | already vendored | Structured logging (collectors must follow Phase 10's `host`+`protocol`-only field policy — no credential leakage) | [VERIFIED: Phase 10 precedent in `agent/internal/push/client.go` and `agent/internal/ssh/`] |
| FastAPI | already in `backend/` | Three push endpoints + one read endpoint | [VERIFIED: project CLAUDE.md] |
| Pydantic 2.7.1 | already in `backend/` | Push body schemas + read response schema | [VERIFIED: project CLAUDE.md + existing `backend/app/schemas/agent.py`] |
| Alembic | already in `backend/` | Four new migrations (`011_firewall_*`) | [VERIFIED: existing `backend/migrations/versions/` with 10 migrations following `YYYYMMDD_NNN_<name>.py` pattern] |
| SQLAlchemy async + asyncpg | already in `backend/` | DB models + insert/select | [VERIFIED: `backend/app/db/models.py` + `backend/app/db/session.py`] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `github.com/netascode/go-fmc` | latest commit on master (no tagged releases visible) | Optional — Cisco-blessed Go FMC client with GJSON/SJSON helpers | [VERIFIED: github.com/netascode/go-fmc] Use ONLY if pure `net/http` becomes painful for FMC's domain-UUID handling. Maturity bar: lower than Phase 10's `nemith.io/netconf` (which has tagged releases). Recommend rolling our own with stdlib for collector-package boundary cleanliness. |
| `github.com/stretchr/testify` | already vendored | Test assertions (Phase 10 standard) | [VERIFIED: Phase 10 plans use testify/assert + testify/require] |
| `pytest` + `pytest-asyncio` | already in `backend/` | Backend tests with `httpx.AsyncClient` against the FastAPI app + asyncpg fixtures | [VERIFIED: project CLAUDE.md + Phase 6 plan 06-01] |
| `httptest` (Go stdlib `net/http/httptest`) | go1.22+ | Hermetic vendor-API mocks for unit tests of `asa.RESTCollector` / `fmc.Collector` / `checkpoint.LiveCollector` | [VERIFIED: Phase 10 push client uses httptest extensively] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Pure `net/http` for FMC | `github.com/netascode/go-fmc` | go-fmc handles refresh-token cycle and domain-UUID interpolation but adds an external dependency without tagged releases (lower maturity than Phase 10's `nemith.io/netconf`). **Recommended: stdlib unless FMC integration becomes painful**, then revisit. |
| Pure `net/http` for ASA REST | None worth using | No mature Go ASA REST library exists (the API itself is end-of-life at 9.16, so the ecosystem stopped investing). Stdlib is the only sane path. |
| Pure `net/http` for Checkpoint | `github.com/CheckPointSW/cp_mgmt_api_python_sdk` (Python only) | No Go SDK exists. Stdlib + JSON parsing is the path. |
| `github.com/scrapli/scrapligo` for ASA SSH | `golang.org/x/crypto/ssh` (Phase 10 precedent) | scrapligo is purpose-built for network-device CLI scraping (handles paging, prompts, modes) but adds a new dependency. Phase 10 already proved `x/crypto/ssh` + manual pty + `ECHO=0` works for IOS-XE — same approach for ASA. **Recommended: stay with Phase 10 precedent.** |

**Installation (Go):**
```bash
# All required Go deps already vendored by Phase 10. No new go.mod additions needed
# unless planner picks go-fmc (decision per discretion above).
cd agent && go mod tidy
```

**Installation (Python backend):**
```bash
# No new pip deps — uses existing FastAPI/Pydantic/SQLAlchemy/asyncpg/Alembic stack.
cd backend && pip install -e .
```

**Version verification (planner runs before plan write):**
```bash
# Verify Go versions of stdlib packages via active toolchain
cd agent && go version

# If go-fmc is selected, verify latest commit
go list -m -versions github.com/netascode/go-fmc

# Verify backend stack pinned versions
cd backend && pip show fastapi pydantic sqlalchemy asyncpg alembic
```

## Architecture Patterns

### System Architecture Diagram

```
+-----------------------------------------------------------------------------+
|                           Customer LAN / DC                                 |
|                                                                             |
|  +-------------------+       +------------------+       +------------------+|
|  | Cisco ASA (REST)  |<----- | infracanvas-agent|------>| Cisco FMC        ||
|  | (ASA <= 9.16 only)|  443  |   (Go binary)    |  443  | (any version)    ||
|  +-------------------+       |                  |       +------------------+|
|                              |                  |                            |
|  +-------------------+       |  +------------+  |       +------------------+|
|  | Cisco ASA (SSH)   |<----- |  | 4 tickers  |  |------>| Checkpoint Mgmt  ||
|  | (ASA 9.17+ MUST   |   22  |  | Routes 5m  |  |  443  | (R80+, R81+)     ||
|  |  use this path)   |       |  | BGP    1m  |  |       +------------------+|
|  +-------------------+       |  | Flow   30s |  |                            |
|                              |  | Firewall1h |<-- 4th ticker (Phase 11 D-02)|
|                              |  +------------+  |                            |
|                              |                  |       +------------------+|
|  +-------------------+       |                  |<----- | checkpoint-import||
|  | (air-gapped)      |       +--------+---------+       | (file read,      ||
|  | mgmt_cli export   |                |                 |  CKP-02)         ||
|  | .json on disk     |                | HTTPS           +------------------+|
|  +-------------------+                | Bearer site_token                   |
|                                       | (Phase 10 D-04)                     |
+---------------------------------------|-------------------------------------+
                                        |  retry-twice-then-drop (D-07)
                                        v
+-----------------------------------------------------------------------------+
|                         InfraCanvas SaaS Backend                            |
|                                                                             |
|   POST /v1/agent/firewall-rules    \                                        |
|   POST /v1/agent/firewall-nat       }-- require_site_token (Phase 10)       |
|   POST /v1/agent/firewall-objects  /                                        |
|                                       |                                     |
|                                       v                                     |
|   FastAPI handlers --> SQLAlchemy async session                             |
|                       SET LOCAL app.current_team_id = <site.team_id>        |
|                                       |                                     |
|                                       v                                     |
|   firewall_ruleset_snapshots          (parent)                              |
|   firewall_rules         FK--->       (children, cascade)                   |
|   firewall_nat_rules     FK--->                                             |
|   firewall_objects       FK--->                                             |
|       all RLS-scoped via team_id propagated from dc_sites lookup            |
|                                                                             |
|   GET /v1/sites/{site_id}/firewall-rules                                    |
|       |                                                                     |
|       v                                                                     |
|   require_principal (Clerk JWT) -> SET LOCAL app.current_team_id            |
|       -> SELECT latest snapshot per firewall_id WHERE site_id = ?           |
|       -> JSON: list[device with rules + nat + objects]                      |
|       -> Phase 12 path computation reads this                               |
+-----------------------------------------------------------------------------+
```

Data-flow trace for the primary use case (Cisco ASA via REST, hourly pull):
1. Firewall ticker fires inside `runDaemonWithIntervals` (4th case in select).
2. For each `Device` where `Protocol == "asa-rest"`, the agent dials the ASA, POSTs `/api/tokenservices` (Basic Auth → X-Auth-Token), then GETs the rule + NAT + object endpoints.
3. The collector returns three structured slices (`[]Rule`, `[]NATRule`, `[]Object`) with both normalized fields and the raw response preserved for `raw_blob`.
4. Push client wraps each slice in a payload with a shared `snapshot_id` (UUIDv4 minted by the agent — see §Backend ingest endpoints) and POSTs to the three endpoints in sequence.
5. Backend writes the parent `firewall_ruleset_snapshots` row on the first endpoint that arrives carrying the new `snapshot_id`, then writes children. Each insert sets `app.current_team_id` so RLS holds.
6. Phase 12 reads `GET /v1/sites/{site_id}/firewall-rules` to resolve the latest snapshot per firewall.

### Recommended Project Structure

```
agent/
├── cmd/infracanvas-agent/main.go        # +Intervals.Firewall; +4th case in select; +collector dispatch by new protocols
├── internal/
│   ├── config/
│   │   ├── config.go                    # +5 new protocol consts; +switch arms in validate()
│   │   ├── import.go                    # (unchanged — Phase 10 config-import)
│   │   └── checkpoint_import.go         # NEW — file-read for CKP-02 (mirrors import.go)
│   ├── push/
│   │   ├── client.go                    # +3 methods: PushFirewallRules, PushFirewallNAT, PushFirewallObjects
│   │   └── types.go                     # +3 payload structs (mirrors backend Pydantic models)
│   ├── asa/                             # NEW
│   │   ├── rest.go                      # ASA REST client + token cache + endpoint helpers
│   │   ├── rest_test.go                 # httptest-driven
│   │   ├── ssh.go                       # ASA SSH show running-config + parser
│   │   ├── ssh_test.go                  # fixture-driven
│   │   └── types.go                     # Rule, NATRule, Object structs (shared between rest/ssh paths — D-08 hybrid)
│   ├── fmc/                             # NEW
│   │   ├── client.go                    # FMC client; token + refresh-token cycle; domain UUID resolution
│   │   ├── client_test.go               # httptest-driven
│   │   └── types.go
│   └── checkpoint/                      # NEW
│       ├── live.go                      # CKP-01 — login / show-* / logout
│       ├── live_test.go                 # httptest-driven
│       ├── parser.go                    # CKP-12 SHARED PARSER — pure function over Checkpoint policy JSON
│       ├── parser_test.go               # fixture-driven, covers BOTH live and import shapes
│       ├── import.go                    # CKP-02 — file read; calls parser.go
│       ├── import_test.go               # fixture-driven
│       └── types.go

backend/
├── app/
│   ├── routes/
│   │   ├── agent.py                     # +3 push handlers (firewall-rules / firewall-nat / firewall-objects)
│   │   └── firewalls.py                 # NEW — GET /v1/sites/{site_id}/firewall-rules (Clerk JWT)
│   ├── schemas/
│   │   └── firewall.py                  # NEW — push body + read response Pydantic models
│   ├── db/
│   │   └── models.py                    # +4 ORM models: FirewallRulesetSnapshot, FirewallRule, FirewallNATRule, FirewallObject
│   └── main.py                          # +include_router(firewalls.router)
└── migrations/versions/
    └── 20260510_011_firewall_tables.py  # NEW — single migration, all 4 tables + RLS + indexes

agent/docs/cab/                          # EXTEND — do NOT replace
├── threat-model.md                      # +TB-1/TB-2/TB-3 firewall rows (T-11-NN-MM IDs)
├── architecture.md                      # +firewall data-flow paragraph
├── dataflow.md                          # +TB-1 row for ASA/FMC/Checkpoint
└── known-limitations.md                 # +ASA REST EOL note (L-N), Checkpoint SID note
```

### Pattern 1: Shared Parser for Live + Import Paths (CKP-01 + CKP-02)

**What:** A pure-function parser package (`agent/internal/checkpoint/parser.go`) consumes a Checkpoint policy JSON byte slice and returns `([]Rule, []NATRule, []Object)`. Both `live.go` (which fetches via HTTP) and `import.go` (which reads from disk) call this single parser.

**When to use:** Whenever an offline-export path mirrors a live-API path. Phase 10 established the precedent with `config-import`. The same hermetic-test benefit applies — `import.go` is a pure file read, so main-loop tests can use `protocol: checkpoint-import` to exercise the 4th ticker without network.

**Example:**
```go
// agent/internal/checkpoint/parser.go
// Source: extends Phase 10 agent/internal/config/import.go pattern
package checkpoint

// Parse takes a raw mgmt_cli show-access-rulebase / show-nat-rulebase / show-objects
// JSON byte slice and returns normalized slices. Pure function — no I/O.
func Parse(rulebaseJSON, natJSON, objectsJSON []byte) (Rules, NATs, Objects, error) {
    // ... unmarshal + normalize ...
}

// agent/internal/checkpoint/live.go
func (c *LiveCollector) Pull(ctx context.Context, dev config.Device) (Rules, NATs, Objects, error) {
    sid, err := c.login(ctx, dev)
    if err != nil { return nil, nil, nil, err }
    defer c.logout(ctx, sid)  // best-effort; WARN on failure (CONTEXT.md <specifics>)

    rb, err := c.showAccessRulebase(ctx, sid, dev)  // paginate via offset; max 500/page
    if err != nil { return nil, nil, nil, err }
    nb, err := c.showNATRulebase(ctx, sid, dev)
    objs, err := c.showObjects(ctx, sid, dev)
    return Parse(rb, nb, objs)
}

// agent/internal/checkpoint/import.go
func LoadImport(path string) (Rules, NATs, Objects, error) {
    // mirrors agent/internal/config/import.go file-read shape
    // Three files OR one combined file — planner decides
    rb, err := os.ReadFile(path + ".rulebase.json")
    nb, _ := os.ReadFile(path + ".nat.json")
    objs, _ := os.ReadFile(path + ".objects.json")
    return Parse(rb, nb, objs)
}
```

### Pattern 2: Snapshot ID Minted by Agent (3 endpoints, 1 snapshot)

**What:** The agent generates a `snapshot_id` (UUIDv4) per device-pull and stamps it on all three push payloads (rules, nat, objects). Backend uses `INSERT ... ON CONFLICT DO NOTHING` on `firewall_ruleset_snapshots(snapshot_id)` so whichever endpoint arrives first creates the parent row.

**When to use:** When one logical operation spans multiple HTTP endpoints (because of D-07's separate-tables decision). Avoids "first-endpoint-creates-parent" coupling between the three handlers — they all become idempotent on `snapshot_id`.

**Example:**
```go
// agent: push all three with the same snapshot_id
snap := uuid.NewString()
ts := time.Now().UTC().Format(time.RFC3339)
_ = pusher.PushFirewallRules(ctx, push.FirewallRulesPayload{
    SnapshotID: snap, FirewallID: dev.Host, Vendor: "cisco-asa",
    Source: "asa-rest", SnapshotTS: ts, SiteID: dev.SiteID, Rules: rules,
})
_ = pusher.PushFirewallNAT(ctx, push.FirewallNATPayload{SnapshotID: snap, /* ... */})
_ = pusher.PushFirewallObjects(ctx, push.FirewallObjectsPayload{SnapshotID: snap, /* ... */})
```

```python
# backend handler — same skeleton across all 3
async def push_firewall_rules(body: FirewallRulesPushBody, principal=Depends(require_site_token)):
    async with sm() as session, session.begin():
        await session.execute(text("SELECT set_config('app.current_team_id', :t, true)"), {"t": principal.team_id})
        # Idempotent parent insert — first endpoint to arrive wins
        await session.execute(insert(FirewallRulesetSnapshot).values(
            snapshot_id=body.snapshot_id, site_id=principal.site_id,
            firewall_id=body.firewall_id, vendor=body.vendor, source=body.source,
            snapshot_ts=body.snapshot_ts,
        ).on_conflict_do_nothing(index_elements=["snapshot_id"]))
        # Then bulk-insert children
        await session.execute(insert(FirewallRule), [...])
    return {"ok": True}
```

### Pattern 3: ASA REST Token Cache (Phase 11 collector-internal)

**What:** ASA's `POST /api/tokenservices` returns a token usable for ~24min. Caching it across endpoint calls within a single pull avoids burning a re-auth per resource type.

**Example:**
```go
type RESTCollector struct {
    http  *http.Client
    cache map[string]asaToken  // host -> token; cleared per-pull
}

func (c *RESTCollector) Pull(ctx context.Context, dev config.Device) (...) {
    tok, err := c.acquireToken(ctx, dev)  // POSTs /api/tokenservices, caches by dev.Host
    if err != nil { return nil, nil, nil, err }
    defer c.deleteToken(ctx, dev, tok)  // DELETE /api/tokenservices/{tok} — best-effort cleanup
    // GET /api/objects/networkobjects, /api/access/in/.../rules, /api/nat with X-Auth-Token: tok
}
```

### Anti-Patterns to Avoid

- **Auto-fallback ASA REST → SSH at runtime**: Explicitly forbidden by D-04. The threat model becomes auditable when each device's protocol is operator-declared. CAB packet language depends on this.
- **Long-lived Checkpoint SID stored on disk**: Forbidden by D-14. Login-per-pull keeps the secret-at-rest surface zero.
- **First-endpoint-creates-snapshot coupling**: Picking "rules endpoint owns the parent" creates a hidden ordering requirement. Use the Pattern 2 snapshot-id-from-client design instead.
- **Per-collector retry/backoff logic**: Forbidden — the push client (`agent/internal/push/Client`) already implements D-07's retry-twice-then-drop. Collectors should fail-and-return on vendor-API errors; the ticker's next tick is the retry.
- **Logging credentials**: Phase 10 mitigations T-10-04-02 / T-10-05-02 / T-10-07-02 must extend to firewall collectors. Log only `host` + `protocol` fields (and pull-id), never `username`/`password`/SID/token.
- **Treating the `raw_blob` JSONB column as queryable**: Phase 12 reads only the normalized columns. JSONB exists for vendor-specific UI/audit, not for path-computation joins. Adding GIN indexes is premature — defer until a real query pattern emerges.
- **Mixing FMC and direct-ASA results in one snapshot**: Two separate `firewall_id` rows. D-15 keeps the drift signal visible.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Bearer-token + retry HTTP push | A second push client for firewall payloads | Add 3 methods to `agent/internal/push/Client` | D-07 retry semantics + token-redaction posture (T-10-07-02/06) are already hard-won. Three methods following `PushRoutes`/`PushFlows` shape. |
| Site-token validation middleware | A new firewall-specific auth dep | Reuse `require_site_token` from `backend/app/auth/site_token.py` | Already exists from Phase 10 plan 10-02; SHA-256 lookup hash via `dc_site_by_token_hash` SQL function. |
| RLS team-isolation policy | Cross-team firewall query gates in handler code | Postgres RLS policy `firewall_*_team_isolation` via `current_setting('app.current_team_id')` | Mirrors `dc_sites_team_isolation` from migration 010 (lines 53-58). FORCE ROW LEVEL SECURITY catches future BYPASSRLS regressions. |
| Checkpoint policy JSON parsing | A custom recursive descent parser | `encoding/json` into typed structs in `agent/internal/checkpoint/parser.go` | Checkpoint JSON shape is regular and documented; stdlib unmarshal handles it. |
| ASA running-config ACL parsing | A general-purpose Cisco config parser | A small linear-time regex parser in `agent/internal/asa/ssh.go` (mirrors Phase 10 `agent/internal/ssh/` route parser) | Phase 10 T-10-05-03 mitigation already proves the linear-regex + skip-non-matching pattern. Do NOT pull in `scrapligo` or a full HCL-style grammar. |
| Snapshot retention TTL job | A bespoke cron container | Postgres-side scheduled `DELETE FROM firewall_ruleset_snapshots WHERE snapshot_ts < NOW() - INTERVAL '30 days'` invoked by an existing scheduler (taskiq periodic from Phase 6 plan 06-06) OR a single trigger-on-insert that prunes per write | Avoid adding new infrastructure. Recommendation: planner adds a `taskiq_periodic` task because `backend/` already runs taskiq workers (Phase 6) and that's the existing pattern. Cascade FK from children + a single `DELETE WHERE snapshot_ts < ...` is enough — no per-row trigger gymnastics. |
| Pagination loops | A custom paginator interface | A simple `for offset := 0; ; offset += 500` loop in `checkpoint.live` (with a hard safety cap of e.g. 200 pages = 100k rules) | Checkpoint API is offset/limit; FMC is `limit`/`offset` style. Both are simple — a 5-line loop is clearer than an interface. |

**Key insight:** Phase 11's "do not hand-roll" list is unusually short because Phase 10 already built the agent platform (push client, config loader, ticker harness, RLS scaffolding, CAB packet structure). Phase 11's job is to *plug new collectors into existing seams*, not to invent new infrastructure.

## Runtime State Inventory

> Phase 11 is greenfield in terms of runtime state — it adds new tables and new collectors but does not rename or migrate existing systems. The categories below are still answered explicitly per the protocol.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — Phase 11 introduces 4 new tables (`firewall_ruleset_snapshots`, `firewall_rules`, `firewall_nat_rules`, `firewall_objects`); no existing rows to migrate. The `dc_sites` table from Phase 10 plan 10-02 is reused unchanged. | None. |
| Live service config | None — Phase 11 reuses Phase 10's `agent.yaml` + site_token model. New `agent.yaml` `devices[]` entries are operator action, not a migration. | None — operators add devices when they roll out v1.1+ agent. |
| OS-registered state | None — agent is a single binary launched by the operator (systemd / launchd registration is operator concern, not Phase 11 deliverable). | None. |
| Secrets and env vars | New: per-device firewall mgmt credentials in `agent.yaml`. Phase 10 D-05 / D-17 model applies (plaintext, chmod 600). No backend env vars added — Phase 11 reuses `DATABASE_URL`, `CLERK_*` from Phase 6/10. | None — operator config. |
| Build artifacts / installed packages | New Go packages under `agent/internal/{asa,fmc,checkpoint}/`; existing release pipeline (Phase 10 plan 10-08) cross-compiles all `agent/...` paths so no GHA workflow change required (verify in plan-checker that `release.yml` does not use a `paths:` allowlist that would skip new packages). | Verify GHA workflow includes new packages (planner adds verification step). |

## Common Pitfalls

### Pitfall 1: ASA REST API End-of-Life at 9.16
**What goes wrong:** Operator configures `protocol: asa-rest` against an ASA running 9.18+. POST `/api/tokenservices` returns 404 or the endpoint simply isn't registered. Collector logs an error and the snapshot for that device is empty.
**Why it happens:** The ASA REST API is supported only on ASA 9.3(2) through 9.16. Cisco discontinued it in 9.17+. [VERIFIED: cisco.com/c/en/us/td/docs/security/asa/api/asa_rest_api.html]
**How to avoid:**
- CAB packet `known-limitations.md` MUST add an entry naming the ASA REST EOL boundary explicitly.
- ASA collector documentation in `agent/internal/asa/README.md` (planner adds) MUST direct ASA 9.18+ operators to `protocol: asa-ssh`.
- Operator runbook (`agent/docs/cab/operator-runbook.md`) Phase 11 extension MUST include an ASA-version check step.
**Warning signs:** 404 from `/api/tokenservices`, or 401 with body indicating "REST API disabled". Both are non-retryable per Phase 10 push-client semantics.

### Pitfall 2: Checkpoint SID Lifecycle on Long Pulls
**What goes wrong:** A pull against a Checkpoint mgmt server with many policy layers / many objects exceeds the default 600-second session timeout. The SID expires mid-pull, returning 401 on the last few `show-objects` paginated calls.
**Why it happens:** Default Checkpoint session-timeout is 600s. [VERIFIED: sc1.checkpoint.com R81 docs] D-14 mandates login-per-pull; a single pull can therefore span the timeout if the rule-base is large.
**How to avoid:** On `login`, pass `session-timeout: 3600` in the request body (the login API accepts a timeout up to 3600s per CheckMates discussion). Even with the larger window, log `pull_duration` so ops can see when pulls are approaching the limit.
**Warning signs:** 401 from `show-objects` after several successful pages; "session expired" in the response body.

### Pitfall 3: FMC Token Refresh Cycle
**What goes wrong:** A long pull spans the 30-minute access-token TTL. The collector hits 401 mid-pull and bails.
**Why it happens:** FMC access tokens are valid for 30 minutes; the refresh token gives 3 refreshes for an effective 120-minute window. [VERIFIED: cisco.com FMC REST API docs]
**How to avoid:** On 401, attempt one refresh via `/api/fmc_platform/v1/auth/refreshtoken` before bailing. Track refresh count; after 3, force re-login. Implement as a small `withAuth` wrapper inside `agent/internal/fmc/client.go` so all GET helpers benefit.
**Warning signs:** 401 mid-pull; "Access token has expired" in response body.

### Pitfall 4: ASA Pager Truncation in SSH Path
**What goes wrong:** `show running-config` is truncated by the device's terminal pager — the parser sees only the first ~24 lines.
**Why it happens:** Default ASA terminal pager is 24 lines. (Phase 10 T-10-05-07 already captured this for IOS-XE `show ip route`.)
**How to avoid:** Issue `terminal pager 0` BEFORE `show running-config`. Note: this is **ASA syntax**; IOS-XE uses `terminal length 0`. Phase 10 ssh collector targets IOS-XE — Phase 11 ASA collector cannot copy the command verbatim. Add a regression test that asserts the first command sent is `terminal pager 0`.
**Warning signs:** `--More--` substring in the SSH output buffer; parsed rule list suspiciously short relative to known device size.

### Pitfall 5: Checkpoint Layer Discovery
**What goes wrong:** Operator configures `protocol: checkpoint` and the collector calls `show-access-rulebase` without specifying a layer name. API returns 400.
**Why it happens:** Checkpoint policies are organized as packages → layers → rules. `show-access-rulebase` requires a `name` parameter. [VERIFIED: CheckMates discussion]
**How to avoid:** Pull `show-access-layers` first to enumerate layer names, then iterate `show-access-rulebase` per layer. Concatenate results with a `layer` field added to each rule for traceability.
**Warning signs:** 400 with body "Missing parameter: name" from `show-access-rulebase`.

### Pitfall 6: Domain UUID in FMC Endpoints
**What goes wrong:** Collector hardcodes `Global` as the domain UUID. Customer FMC has multiple domains (Global / Tenant1 / Tenant2). Pulls return only Global rules.
**Why it happens:** FMC is multi-domain by default. Endpoints are `/api/fmc_config/v1/domain/{DOMAIN_UUID}/...`. The DOMAIN_UUID is returned in the auth response headers (`DOMAIN_UUID` header).
**How to avoid:** On login, capture `DOMAIN_UUID` header. If multiple domains exist, the response includes a list — iterate them. For Phase 11, scope to the Global domain by default and document multi-domain as a follow-up; but **the collector must not hardcode** the UUID.
**Warning signs:** Smaller-than-expected rule count for known multi-domain customers.

### Pitfall 7: Snapshot Storage Math
**What goes wrong:** Customer with 100 firewalls and an aggressive operator who configures hourly pulls hits unexpected DB growth. 100 fw × 24 pulls × 30 days × ~500 rules avg + ~200 NAT + ~5000 objects per device = ~410M rows over 30d. JSONB `raw_blob` median size ~2KB → ~820GB raw data (excluding indexes).
**Why it happens:** D-10's full-replace snapshot is generous on storage by design.
**How to avoid:**
- Document the worst case in CAB known-limitations and operator runbook.
- TTL DELETE job (see "Don't Hand-Roll" row 6) prunes >30d snapshots.
- Indexes on `(site_id, firewall_id, snapshot_ts DESC)` ensure latest-snapshot reads stay sub-100ms.
- Recommend a smaller TTL default (e.g. 7 days) for v1.1 with documented escape hatch to bump.
**Warning signs:** Neon storage usage growing >5GB/day per large customer.

### Pitfall 8: `firewall_id` Identity Choice
**What goes wrong:** Phase 12 path computation needs a stable identifier per firewall, but the agent only knows `host` (FQDN/IP). If operator changes the FQDN, downstream Phase 12 sees it as a new firewall.
**Why it happens:** No vendor-side stable serial is exposed via the planned APIs uniformly.
**How to avoid:** Define `firewall_id` as `(site_id, vendor, host)` tuple — backend computes a deterministic UUID v5 from these. Document that hostname renames create a new logical firewall (and a snapshot history gap). This is acceptable v1.1 behavior; revisit with vendor-serial extraction in v1.2.
**Warning signs:** Phase 12 reports duplicate firewalls when operator changed DNS.

## Code Examples

### Extending `Intervals` and the ticker loop (4th case)
```go
// agent/cmd/infracanvas-agent/main.go — modifications visible in diff form
type Intervals struct {
    Routes   time.Duration
    BGP      time.Duration
    Flow     time.Duration
    Firewall time.Duration  // NEW (D-02)
}

func defaultIntervals() Intervals {
    return Intervals{
        Routes:   5 * time.Minute,
        BGP:      1 * time.Minute,
        Flow:     30 * time.Second,
        Firewall: 1 * time.Hour,        // NEW (D-02)
    }
}

// In runDaemonWithIntervals:
firewallT := time.NewTicker(iv.Firewall)
defer firewallT.Stop()
// ...
case <-firewallT.C:
    wg.Add(1)
    go func() { defer wg.Done(); collectAndPushFirewall(ctx, cfg, pusher, log) }()
```

### Extending the Pusher interface
```go
// Source: extends agent/cmd/infracanvas-agent/main.go:61
type Pusher interface {
    PushRoutes(ctx context.Context, p push.RoutesPayload) error
    PushFlows(ctx context.Context, p push.FlowsPayload) error
    PushFirewallRules(ctx context.Context, p push.FirewallRulesPayload) error    // NEW
    PushFirewallNAT(ctx context.Context, p push.FirewallNATPayload) error        // NEW
    PushFirewallObjects(ctx context.Context, p push.FirewallObjectsPayload) error // NEW
}
```

### Extending the protocol switch
```go
// Source: extends agent/internal/config/config.go:65
const (
    ProtocolNetconf      = "netconf"
    ProtocolSSH          = "ssh"
    ProtocolConfigImport = "config-import"
    ProtocolASARest      = "asa-rest"          // NEW (D-16)
    ProtocolASASSh       = "asa-ssh"           // NEW (D-16)
    ProtocolFMC          = "fmc"               // NEW (D-16)
    ProtocolCheckpoint   = "checkpoint"        // NEW (D-16)
    ProtocolCheckpointImport = "checkpoint-import"  // NEW (D-16)
)

func (c *Config) validate() error {
    // ...
    for i, d := range c.Devices {
        switch d.Protocol {
        case ProtocolNetconf, ProtocolSSH, ProtocolConfigImport,
             ProtocolASARest, ProtocolASASSh, ProtocolFMC,
             ProtocolCheckpoint, ProtocolCheckpointImport:
            // ok
        default:
            return fmt.Errorf("device[%d]: invalid protocol: %s", i, d.Protocol)
        }
        // import-style protocols require config_file (mirrors line 71-73)
        if (d.Protocol == ProtocolConfigImport || d.Protocol == ProtocolCheckpointImport) && d.ConfigFile == "" {
            return fmt.Errorf("device[%d]: config_file required when protocol=%s", i, d.Protocol)
        }
        if d.Protocol != ProtocolConfigImport && d.Protocol != ProtocolCheckpointImport && d.Host == "" {
            return fmt.Errorf("device[%d]: host required when protocol=%s", i, d.Protocol)
        }
    }
    return nil
}
```

### Cisco ASA REST authentication
```go
// Source: cisco.com/c/en/us/td/docs/security/asa/api/asa_rest_api.html
// POST /api/tokenservices with Basic auth header
req, _ := http.NewRequestWithContext(ctx, "POST", "https://"+host+"/api/tokenservices", nil)
req.SetBasicAuth(username, password)
resp, err := client.Do(req)
// Token is returned in the X-Auth-Token RESPONSE header
token := resp.Header.Get("X-Auth-Token")
// Subsequent calls send X-Auth-Token: <token>
// Cleanup: DELETE /api/tokenservices/<token> when done
```

### Cisco FMC token + refresh
```go
// Source: cisco.com FMC REST API guide
// POST /api/fmc_platform/v1/auth/generatetoken with Basic auth
// Returns headers: X-auth-access-token, X-auth-refresh-token, DOMAIN_UUID
// Access token TTL: 30 min; refresh up to 3x; effective max 120 min
// Endpoints: /api/fmc_config/v1/domain/{DOMAIN_UUID}/policy/accesspolicies
//                                                          /accesspolicies/{policy_id}/accessrules
//                                                          /natpolicies/...
//                                                          /object/networks
//                                                          /object/networkgroups
//                                                          /object/protocolportobjects
```

### Checkpoint Mgmt API login + show-access-rulebase
```go
// Source: sc1.checkpoint.com Management API reference + CheckMates community
// POST /web_api/login with JSON body {"user": ..., "password": ..., "session-timeout": 3600}
// Response: {"sid": "...", ...}
// Header for subsequent calls: X-chkp-sid: <sid>
//
// POST /web_api/show-access-layers     -> enumerate layers
// POST /web_api/show-access-rulebase   -> body {"name": "<layer>", "limit": 500, "offset": 0}
//                                          paginate until response.total < offset+limit
//                                          MAX limit = 500
// POST /web_api/show-nat-rulebase      -> body {"package": "<package>", "limit": 500, "offset": 0}
// POST /web_api/show-objects           -> body {"limit": 500, "offset": 0, "type": "host"|"network"|...}
// POST /web_api/logout                 -> body {} ; header X-chkp-sid: <sid>
```

### `mgmt_cli show access-rulebase --format json` shape
```json
// Source: CheckMates community example output
{
  "uid": "9d3a8a1f-...",
  "name": "Network",
  "rulebase": [
    {
      "uid": "...",
      "type": "access-rule",
      "rule-number": 1,
      "name": "Allow web in",
      "source": ["host-uid-1", "host-uid-2"],
      "source-negate": false,
      "destination": ["network-uid-3"],
      "destination-negate": false,
      "service": ["service-uid-tcp-443"],
      "action": "Accept",
      "track": {"type": "Log"},
      "install-on": ["..."]
    }
  ],
  "objects-dictionary": [
    {"uid": "host-uid-1", "type": "host", "ipv4-address": "10.1.1.1", "name": "web-1"}
  ],
  "from": 1,
  "to": 1,
  "total": 1
}
```

### Backend Pydantic push body skeleton
```python
# backend/app/schemas/firewall.py — NEW
from pydantic import BaseModel, Field

class FirewallRule(BaseModel):
    position: int
    src_zone: str | None = None
    dst_zone: str | None = None
    src_cidr: list[str] = []
    dst_cidr: list[str] = []
    action: str  # 'allow' | 'deny' | 'reject' (vendor-normalized)
    protocol: str | None = None
    ports: list[str] = []
    raw_blob: dict  # vendor-native rule preserved per D-08

class FirewallRulesPushBody(BaseModel):
    snapshot_id: str            # UUID minted by agent (Pattern 2)
    firewall_id: str            # stable per (site, vendor, host) — see Pitfall 8
    vendor: str                 # 'cisco-asa' | 'cisco-fmc' | 'checkpoint'
    source: str                 # 'asa-rest' | 'asa-ssh' | 'fmc' | 'checkpoint' | 'checkpoint-import'
    snapshot_ts: str            # ISO 8601
    site_id: str
    rules: list[FirewallRule] = Field(..., max_length=50000)  # T-10-02-06-style bound — bigger than route 10000 cap because rule sets can legitimately be larger
```

### Backend Alembic migration skeleton (one migration, four tables)
```python
# backend/migrations/versions/20260510_011_firewall_tables.py — NEW
def upgrade() -> None:
    op.create_table("firewall_ruleset_snapshots",
        sa.Column("snapshot_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("site_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("dc_sites.id", ondelete="CASCADE"), nullable=False),
        sa.Column("team_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("firewall_id", sa.Text(), nullable=False),
        sa.Column("vendor", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("snapshot_ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_firewall_snapshots_latest", "firewall_ruleset_snapshots",
                    ["site_id", "firewall_id", sa.text("snapshot_ts DESC")])
    op.execute("ALTER TABLE firewall_ruleset_snapshots ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE firewall_ruleset_snapshots FORCE ROW LEVEL SECURITY;")
    op.execute("""CREATE POLICY firewall_snapshots_team_isolation ON firewall_ruleset_snapshots
                  USING (team_id = current_setting('app.current_team_id', true)::uuid)
                  WITH CHECK (team_id = current_setting('app.current_team_id', true)::uuid);""")
    # ... same shape for firewall_rules, firewall_nat_rules, firewall_objects
    # all FK to firewall_ruleset_snapshots(snapshot_id) with ondelete=CASCADE
    # all RLS-enabled with team_isolation policy
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Cisco ASA REST API as the modern programmatic interface | SSH CLI + ASDM (REST API end-of-life) | ASA 9.17 (≈ 2022) | Phase 11 must position `asa-ssh` as the primary path for ASA 9.18+ deployments, NOT a legacy fallback |
| Long-lived Checkpoint SID with periodic refresh | Login-per-pull (D-14) | Phase 11 deliberate choice | Trades a small login-cost-per-pull for zero secret-at-rest |
| Checkpoint XML API (R77 era) | Web API (`/web_api/...`) JSON over HTTPS | R80 (2016) | All examples must use the R80+ web API; pre-R80 is out of scope |
| FMC long-lived API key | Token + refresh-token cycle | Always — but the 30min/3-refresh cap is the current published contract | Plan must implement refresh cycle |

**Deprecated/outdated:**
- Cisco ASA REST API (deprecated at 9.17). Documented in CAB known-limitations. [VERIFIED: cisco.com Compatibility matrix]
- Checkpoint pre-R80 XML API (out of scope; v1.1 targets R80+ only).
- FMC REST API v1 endpoints (use `fmc_config/v1` prefix; the deprecated old paths from FMC 6.0-era are gone).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | All three vendor APIs are pure JSON-over-HTTPS with no exotic transport (no XML, no proprietary binary). | Standard Stack / Pattern 1 | Low — verified for Checkpoint (web_api JSON) and FMC (JSON). ASA REST also JSON. If a vendor-specific edge requires XML, planner adds `encoding/xml` import. |
| A2 | Snapshot retention TTL of 7-30 days is acceptable to v1.1 customers. | Don't Hand-Roll / Pitfall 7 | Medium — large customers may want 90+ days for compliance. Discuss-phase confirmed "~30 days suggested" but planner picks. Easy to extend later. |
| A3 | `firewall_id` derived from `(site_id, vendor, host)` is stable enough for Phase 12. | Pitfall 8 | Medium — hostname renames cause apparent firewall identity change. Documented as known limitation, revisit in v1.2 with vendor-serial extraction. |
| A4 | A single push from the agent for all three data types within a snapshot will arrive within seconds (well under any TTL or backend timeout). | Pattern 2 | Low — push client has 15s timeout × 3 attempts = 45s worst case per endpoint, total < 3 minutes. Snapshot ts won't drift. |
| A5 | Pure `net/http` is sufficient for FMC; `go-fmc` library is not strictly required. | Standard Stack alternatives | Low — the library is convenience, not capability. Worst case planner reverses this in research-back during plan write. |
| A6 | Checkpoint policy JSON shape from `mgmt_cli show ... --format json` matches the live API response shape verbatim. | Pattern 1 (CKP-12 shared parser) | Medium — verified against CheckMates community examples and pcwiki R80 notes; very strong evidence but not a Cisco/Checkpoint-published guarantee. Recommend Wave 0 includes a fixture file pair (live + import) that the parser test runs against to lock the contract. |
| A7 | The `taskiq_periodic` from Phase 6 plan 06-06 is the right home for the snapshot TTL prune job. | Don't Hand-Roll row 6 | Low — taskiq broker exists; periodic tasks are a documented taskiq feature. If planner finds the periodic API less mature than expected, fall back to a Postgres-side `DELETE` triggered by an Alembic-managed function called from a Fly cron. |
| A8 | Checkpoint default `session-timeout` of 600s can be extended to 3600s via the login body parameter. | Pitfall 2 | Low — CheckMates discussion + R81 docs confirm range 10-3600s. |
| A9 | ASA `terminal pager 0` correctly disables paging across ASA 9.6 through 9.22 (all in-support versions). | Pitfall 4 | Low — well-documented ASA syntax. |

## Open Questions (RESOLVED)

1. **Snapshot retention TTL — exact value (7d, 14d, 30d, 90d)?**
   - What we know: D-10 suggests ~30 days; storage math (Pitfall 7) shows 30d × large customer = ~800GB raw data.
   - What's unclear: whether v1.1 customers need a configurable TTL or a hard global default.
   - **RESOLVED 2026-05-12:** Default to **14 days** in Plan 11-02, exposed via env var `FIREWALL_SNAPSHOT_TTL_DAYS`. Lower than the original 30d recommendation because Pitfall 7's worst-case storage math (~800GB) made 30d a non-starter for v1.1 cost budget; 14d still covers the standard "rule change two weeks ago, who changed it?" diagnostic window. Operators who want longer retention bump the env var (zero schema change). Revisit if v1.2 customers ask for ≥30d retention as a standard tier.

2. **`firewall_id` derivation — agent-side or backend-side?**
   - What we know: Pitfall 8 captures the design problem.
   - What's unclear: whether the agent computes the deterministic UUIDv5 (cleaner: backend treats it as opaque) or backend computes (cleaner: agent can stay simple).
   - **RESOLVED 2026-05-12:** **Agent-side UUIDv5** from namespace + `(site_id, vendor, host)`. Mirrors how scan_id is minted at Phase 7.5 plan 05. Backend treats `firewall_id` as opaque. Locked in Plan 11-08/09/10/11 (per-vendor collectors) and Plan 11-05 (Pusher contract).

3. **CKP-02 file layout — three files or one combined file?**
   - What we know: D-12 says "the customer dumps `mgmt_cli show ...` to a file path." `mgmt_cli` produces three separate JSON outputs (rulebase / nat / objects) by default.
   - What's unclear: should `agent.yaml` reference one path (combined JSON) or three (one per data type)?
   - **RESOLVED 2026-05-12:** **Three suffixed paths under a single base path.** `agent.yaml` declares one `config_file` field with a base path; the loader looks for `<base>.rulebase.json`, `<base>.nat.json`, `<base>.objects.json`. Mirrors Phase 10 `config-import` single-field shape while supporting Checkpoint's three-document reality. Locked in Plan 11-11.

4. **Bulk insert size for `firewall_rules` rows on backend?**
   - What we know: Pydantic bound is 50000; SQLAlchemy + asyncpg can multi-row INSERT but a single `executemany` of 50k rows can hit Postgres protocol limits.
   - What's unclear: ideal chunk size for asyncpg `INSERT ... VALUES (...), (...), ...` without exceeding statement length.
   - **RESOLVED 2026-05-12:** **500 rows per chunk** for asyncpg multi-row INSERT. Matches Checkpoint paginate-by-500 mental model. Plan 11-03 verifies via integration test on a synthetic 10k-rule snapshot.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Go toolchain | agent build + tests | ✓ (Phase 10 already in CI) | go1.22+ | — |
| `golang.org/x/crypto/ssh` | ASA SSH collector | ✓ (vendored Phase 10) | latest | — |
| `gopkg.in/yaml.v3` | checkpoint-import file read | ✓ (vendored Phase 10) | v3 | — |
| `go.uber.org/zap` | structured logging | ✓ (vendored Phase 10) | latest | — |
| Python 3.12 + FastAPI + Pydantic + SQLAlchemy + asyncpg + Alembic + structlog + taskiq | backend new endpoints + tables + TTL prune job | ✓ (Phase 6 + Phase 10) | per pyproject.toml | — |
| Postgres (Neon, dev: testcontainers) | new tables + RLS policies | ✓ (Phase 6 plan 06-03) | 15+ | — |
| `pytest`, `pytest-asyncio`, `httpx` (test client) | backend tests | ✓ (Phase 6 plan 06-01 conftest) | per pyproject.toml | — |
| `testify` | Go agent tests | ✓ (Phase 10) | latest | — |
| GHA workflow `release.yml` for cross-compile | Phase 11 binaries | ✓ (Phase 10 plan 10-08, paused at task 3 manual checkpoint) | — | — |
| `mgmt_cli` (Checkpoint side) | CKP-02 fixture generation by ops, NOT shipped by us | ✗ (operator side) | n/a | Hermetic test fixtures live in `agent/internal/checkpoint/testdata/` and are committed JSON files — no `mgmt_cli` runtime dependency in our test path |
| Real Cisco ASA / FMC / Checkpoint test devices | end-to-end smoke (manual checkpoint) | ✗ | — | Hermetic httptest.Server stubs cover unit tests; manual smoke is operator-deferred (analogous to Phase 10 plan 10-08 task 3 checkpoint pattern) |

**Missing dependencies with no fallback:** None — all build-time dependencies present.

**Missing dependencies with fallback:** Real vendor devices (manual smoke checkpoint). Plan a `checkpoint:human-verify` gate on the final wave (mirrors Phase 10 plan 10-08 task 3 + plan 10-09 patterns).

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework (Go agent) | `testing` + `testify` (Phase 10 standard) |
| Framework (backend) | `pytest` + `pytest-asyncio` + `httpx.AsyncClient` (Phase 6 standard) |
| Config file (Go) | `agent/go.mod` + per-package `_test.go` files |
| Config file (backend) | `backend/pyproject.toml` `[tool.pytest.ini_options]` + `backend/tests/conftest.py` (Phase 6 plan 06-01 fixtures: testcontainers Postgres, mock_clerk, in_memory_broker, bypass_role.sql) |
| Quick run command (Go) | `cd agent && go test ./internal/asa/... ./internal/fmc/... ./internal/checkpoint/... -race` |
| Full suite command (Go) | `cd agent && go test ./... -race` |
| Quick run command (backend) | `cd backend && pytest tests/test_routes_firewall.py tests/test_schemas_firewall.py -x` |
| Full suite command (backend) | `cd backend && pytest -x` |
| End-to-end (4th ticker) | `cd agent && go test ./cmd/infracanvas-agent/... -race -run TestRunDaemon` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ASA-01 | ASA REST collector pulls rules + NAT + objects via `X-Auth-Token` | unit | `cd agent && go test ./internal/asa/... -race -run TestRESTCollector_Pull` | ❌ Wave 0 |
| ASA-01 | ASA REST collector handles 401 on REST-disabled (9.17+) device with non-retryable error | unit | `cd agent && go test ./internal/asa/... -race -run TestRESTCollector_DisabledAPI` | ❌ Wave 0 |
| ASA-02 | FMC client acquires + refreshes token; survives 401-on-expired with one refresh | unit | `cd agent && go test ./internal/fmc/... -race -run TestClient_TokenRefresh` | ❌ Wave 0 |
| ASA-02 | FMC client paginates access-rules across multiple pages | unit | `cd agent && go test ./internal/fmc/... -race -run TestClient_PaginatedAccessRules` | ❌ Wave 0 |
| ASA-03 | ASA SSH collector issues `terminal pager 0` before `show running-config` | unit | `cd agent && go test ./internal/asa/... -race -run TestSSHCollector_DisablesPager` | ❌ Wave 0 |
| ASA-03 | ASA SSH parser extracts access-list, nat, object lines from a fixture | unit | `cd agent && go test ./internal/asa/... -race -run TestSSHParser_RealConfig` | ❌ Wave 0 |
| CKP-01 | Checkpoint live collector login → show-* → logout sequence; logs WARN on logout failure | unit | `cd agent && go test ./internal/checkpoint/... -race -run TestLiveCollector_LoginPullLogout` | ❌ Wave 0 |
| CKP-01 | Checkpoint live collector paginates show-access-rulebase past 500 rules | unit | `cd agent && go test ./internal/checkpoint/... -race -run TestLiveCollector_Paginates` | ❌ Wave 0 |
| CKP-02 | Checkpoint import collector reads three JSON files and produces same parser output as live path | unit | `cd agent && go test ./internal/checkpoint/... -race -run TestImport_MatchesLiveShape` | ❌ Wave 0 |
| CKP-12 (D-12) | Shared parser yields identical results for live JSON and `mgmt_cli --format json` fixture | unit | `cd agent && go test ./internal/checkpoint/... -race -run TestParser_LiveImportEquivalence` | ❌ Wave 0 |
| Phase 11 D-02 | All 4 ticker intervals lock to expected values | unit | `cd agent && go test ./cmd/infracanvas-agent/... -race -run TestDefaultIntervals` | ❌ Wave 0 (Phase 10 has 3-ticker version) |
| Phase 11 D-03 | 4th ticker fires firewall collection on the same shutdown drain | unit | `cd agent && go test ./cmd/infracanvas-agent/... -race -run TestRunDaemon_FirewallTick` | ❌ Wave 0 |
| D-08, D-18 | `POST /v1/agent/firewall-rules` writes parent + children with RLS | integration | `cd backend && pytest tests/test_routes_firewall.py::test_push_firewall_rules_writes_snapshot_and_rules` | ❌ Wave 0 |
| D-08, D-18 | Three endpoints idempotent on `snapshot_id` (parent insert is ON CONFLICT DO NOTHING) | integration | `cd backend && pytest tests/test_routes_firewall.py::test_idempotent_snapshot_id` | ❌ Wave 0 |
| D-09 | Push firewall-objects endpoint persists with kind enum + value JSONB | integration | `cd backend && pytest tests/test_routes_firewall.py::test_push_firewall_objects_persists` | ❌ Wave 0 |
| D-11 | `GET /v1/sites/{site_id}/firewall-rules` returns latest snapshot per device, RLS-scoped | integration | `cd backend && pytest tests/test_routes_firewall_read.py::test_returns_latest_per_device` | ❌ Wave 0 |
| D-11 | Cross-team read returns empty (RLS isolation) | integration | `cd backend && pytest tests/test_routes_firewall_read.py::test_cross_team_isolation` | ❌ Wave 0 |
| D-19 | Push 401/403/422 are non-retryable (existing push.Client contract) | unit | covered by Phase 10 `agent/internal/push/client_test.go` regression | ✅ |
| D-17 (CAB) | CAB threat-model.md contains TB-1/TB-2 firewall rows with T-11-* IDs | doc test | `grep -c '^| T-11-' agent/docs/cab/threat-model.md` ≥ 5 | manual review checkpoint |
| Pitfall 1 | CAB known-limitations.md mentions ASA REST EOL | doc test | `grep -i 'ASA REST.*9\.16\|9\.17' agent/docs/cab/known-limitations.md` | manual review checkpoint |

### Sampling Rate
- **Per task commit:** quick-run (Go: package-scoped `go test -race`; backend: file-scoped `pytest -x`).
- **Per wave merge:** full Go suite (`agent/...`) + full backend suite (`pytest`).
- **Phase gate:** Full agent + full backend suites green before `/gsd-verify-work`. Manual smoke checkpoint mirrors Phase 10 plan 10-08 task 3 pattern (operator runs against a real ASA / FMC / Checkpoint or against three pre-recorded mgmt_cli JSON dumps).

### Wave 0 Gaps
- [ ] `agent/internal/asa/rest_test.go` — covers ASA-01 (httptest.Server fixture)
- [ ] `agent/internal/asa/ssh_test.go` — covers ASA-03 (running-config fixture file under `agent/internal/asa/testdata/`)
- [ ] `agent/internal/fmc/client_test.go` — covers ASA-02 (httptest.Server fixture, including 401-then-refresh path)
- [ ] `agent/internal/checkpoint/live_test.go` — covers CKP-01 (httptest.Server fixture)
- [ ] `agent/internal/checkpoint/parser_test.go` — covers CKP-01 + CKP-02 + D-12 equivalence (committed JSON fixtures under `testdata/`: `live-rulebase.json`, `import-rulebase.json` matched pair, plus NAT and objects pairs)
- [ ] `agent/internal/checkpoint/import_test.go` — covers CKP-02
- [ ] `agent/cmd/infracanvas-agent/main_test.go` — extended for 4-ticker shape (D-02, D-03)
- [ ] `backend/tests/test_routes_firewall.py` — covers D-08, D-09, D-18 push endpoints
- [ ] `backend/tests/test_routes_firewall_read.py` — covers D-11 read endpoint
- [ ] `backend/tests/test_schemas_firewall.py` — covers Pydantic bounds + D-08 hybrid normalized+raw_blob shape
- [ ] No new framework install needed — `testify`, `pytest`, `httpx` all in place from Phase 6/10

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | Bearer site_token (Phase 10 inheritance, T-10-02-01..04). Clerk JWT for read API (Phase 6). No new auth scheme. |
| V3 Session Management | yes | (a) Site-token sessions are stateless (token = session); (b) Checkpoint Mgmt API SID is per-pull only (D-14) — no SID at rest, eliminating session-fixation surface. |
| V4 Access Control | yes | Postgres RLS on all four new tables via `current_setting('app.current_team_id')` — mirrors `dc_sites_team_isolation` pattern (migration 010 lines 53-58). |
| V5 Input Validation | yes | Pydantic `Field(..., max_length=N)` bounds on all push body lists (T-10-02-06 pattern); `str` types prevent SQL injection at the schema layer. JSONB `raw_blob` validated as a dict, not raw bytes. |
| V6 Cryptography | yes | TLS for HTTPS to vendor APIs and to backend (no hand-rolled crypto). Site-token storage uses SHA-256 lookup hash (Phase 10 plan 10-02 T-10-02-01) — same model. Vendor-side device credentials never transmitted. |

### Known Threat Patterns for Phase 11 stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| MITM on management VLAN to ASA / FMC / Checkpoint | Spoofing | Same posture as Phase 10 T-10-04-01 — `tls.Config{InsecureSkipVerify: ...}` decision documented in CAB; ops runs collector on management VLAN. CAB extension records: vendor TLS certs are operator-managed; `ssh.InsecureIgnoreHostKey()` for `asa-ssh` matches Phase 10 SSH posture. |
| Credential leakage via log fields | Information Disclosure | Phase 10 mitigations T-10-04-02 / T-10-05-02 / T-10-07-02 extend to firewall collectors. Code review checklist: zap fields for collectors emit `host`, `protocol`, `pull_id`, `count` only — never `username`, `password`, `sid`, `token`. Add a regression grep test in CAB packet review. |
| Adversary-controlled vendor returns malformed JSON | DoS / Tampering | Go `encoding/json` returns errors cleanly (no panics); collectors log WARN and return — push client's retry semantics handle the next pull. T-11-NN-MM rows in extended threat-model. |
| Replay of site-token push | Tampering | Phase 10 T-10-02-02 — accepted residual; TLS prevents in-transit replay; tokens are revocable per-site. |
| Cross-team firewall data leak via misrouted snapshot | Information Disclosure | RLS ENABLE + FORCE on all four new tables; `app.current_team_id` set inside transaction before insert; integration test asserts cross-team read returns empty. |
| `raw_blob` JSONB injection via crafted vendor response | Tampering | JSONB stored as `dict` after Pydantic parse — no string interpolation into SQL. Dict keys are vendor-controlled but Postgres treats them as data. T-11-NN-MM accept-with-rationale row. |
| Snapshot DoS via massive rule pushes | DoS | Pydantic `Field(..., max_length=50000)` on rules / nat / objects lists. Backend reject 422 (non-retryable). |
| Checkpoint SID hijack | Spoofing | Mitigated by D-14 login-per-pull — SID lifetime is bounded to seconds-to-minutes; no SID written to disk; `X-chkp-sid` header sent over TLS. |
| FMC refresh-token theft from logs | Information Disclosure | Tokens never logged (same posture as T-10-07-02). 30min TTL bounds blast radius. |
| ASA `--More--` pager injection (crafted device output causes parser panic) | DoS | Linear-regex parser; non-matching lines silently skipped (Phase 10 T-10-05-03 pattern). `terminal pager 0` issued first reduces probability. Regression test with adversarial-pager fixture. |
| Bypass of write side of RLS (operator-side BYPASSRLS regression) | Elevation of Privilege | CI grep gate (Phase 6 plan 06-08) catches BYPASSRLS introductions. New tables inherit the `infracanvas_app` role grants — no DDL grants ever set BYPASSRLS. |

## Sources

### Primary (HIGH confidence)
- [Cisco ASA REST API Quick Start Guide](https://www.cisco.com/c/en/us/td/docs/security/asa/api/quick-start/qsg-asa-api.html) — token auth via `/api/tokenservices`, `X-Auth-Token` header, privilege levels
- [About the ASA REST API](https://www.cisco.com/c/en/us/td/docs/security/asa/api/asa_rest_api.html) — **EOL at ASA 9.16 verified**
- [Cisco ASA Compatibility Matrix](https://www.cisco.com/c/en/us/td/docs/security/asa/compatibility/asamatrx.html) — ASA REST API supported only 9.3(2)–9.16
- [How To Generate Authentication Token For FMC REST API Interactions](https://www.cisco.com/c/en/us/support/docs/security/firepower-management-center/215918-how-to-generate-authentication-token-for.html) — `/api/fmc_platform/v1/auth/generatetoken`, `X-auth-access-token` (30min TTL), `X-auth-refresh-token` (3 refreshes), `DOMAIN_UUID`
- [Cisco Secure Firewall Management Center REST API Token Authentication](https://ciscolearning.github.io/cisco-learning-codelabs/posts/fmc-rest-token-authentication/) — full token lifecycle codelab
- [Check Point Management API reference](https://sc1.checkpoint.com/documents/R80/APIs/index.html) — official `web_api/login`, `show-access-rulebase`, `show-nat-rulebase`, `show-objects` reference
- [Check Point R81 Session docs](https://sc1.checkpoint.com/documents/R81/WebAdminGuides/EN/CP_R81_Gaia_AdminGuide/Topics-GAG/Session.htm) — default 600s session-timeout, 10–3600 range
- [pkg.go.dev: golang.org/x/crypto/ssh](https://pkg.go.dev/golang.org/x/crypto/ssh) — canonical SSH client library
- Phase 10 source code (`agent/cmd/infracanvas-agent/main.go`, `agent/internal/config/`, `agent/internal/push/`, `backend/app/routes/agent.py`, `backend/app/schemas/agent.py`, `backend/migrations/versions/20260507_010_dc_sites.py`, `agent/docs/cab/threat-model.md`) — verified by direct read

### Secondary (MEDIUM confidence)
- [GitHub: netascode/go-fmc](https://github.com/netascode/go-fmc) — Go FMC client library (recommended-against in favor of stdlib but available)
- [CheckMates community: Mgmt_cli show access-rule base issue](https://community.checkpoint.com/t5/API-CLI-Discussion/Mgmt-cli-show-access-rule-base-issue/td-p/208807) — `--format json` shape
- [CheckMates community: How to display policy rules in mgmt_cli](https://community.checkpoint.com/t5/API-CLI-Discussion/How-to-display-policy-rules-in-mgmt-cli/td-p/140781) — pagination via offset/limit, max 500
- [CheckMates community: Login session timeout](https://community.checkpoint.com/t5/API-CLI-Discussion/Login-session-timeout/td-p/91301) — login `session-timeout` body parameter
- [r80 api notes - cpwiki.net](http://cpwiki.net/index.php/r80_api_notes) — Checkpoint API field reference
- [Cisco DevNet: fmc-rest-api labs](https://github.com/CiscoDevNet/fmc-rest-api/blob/master/labs/firepower-restapi-101/2.md) — token lifecycle examples

### Tertiary (LOW confidence — flagged for plan-time validation)
- [Medium: REST API for Cisco ASA (Daniela Melo)](https://medium.com/@daniela.mh20/rest-api-for-cisco-asa-3374a22d2e24) — community walkthrough; verified against Cisco docs above
- [networkdirection.net: ASA REST](https://networkdirection.net/articles/firewalls/asarest/) — community ASA REST overview

## Plan Decomposition Recommendation

Suggested wave structure (planner refines):

**Wave 0 (test scaffold):** Single plan that creates all `_test.go` skeletons and `backend/tests/test_routes_firewall*.py` skeletons (Nyquist test-first scaffold; mirrors Phase 6/10 Wave 0 pattern). Commits failing tests so the implementation waves go RED → GREEN.

**Wave 1 (backend, parallel-safe):**
- Plan 11-01: Alembic migration `011_firewall_tables` + ORM models (`backend/app/db/models.py` extension) + Pydantic schemas (`backend/app/schemas/firewall.py`).
- Plan 11-02: Three push endpoints (`backend/app/routes/agent.py` extension) — implements Pattern 2 (snapshot_id from agent, ON CONFLICT DO NOTHING parent insert).
- Plan 11-03: Read endpoint (`backend/app/routes/firewalls.py` NEW) + `main.py` router include.

  Files modified: 11-01 → migrations + models + schemas (DISJOINT from 11-02/03). 11-02 → routes/agent.py (DISJOINT from 11-03 → routes/firewalls.py + main.py). All three can run in parallel.

**Wave 2 (agent shared infrastructure, sequential):**
- Plan 11-04: Push client extension (`agent/internal/push/client.go` + `types.go` — three new methods + three payload structs). Single-file changes.
- Plan 11-05: Config protocol enum extension + checkpoint-import file loader (`agent/internal/config/config.go` + new `agent/internal/config/checkpoint_import.go`). Single owner.
- Plan 11-06: 4th ticker scaffolding (`agent/cmd/infracanvas-agent/main.go` — `Intervals.Firewall`, 4th case in select, `collectAndPushFirewall` function with empty body that selects collector by protocol). Sequential because 11-04/11-05 must land first.

**Wave 3 (per-vendor collectors, parallel):**
- Plan 11-07: ASA REST collector (`agent/internal/asa/rest.go` + `types.go` + tests).
- Plan 11-08: ASA SSH collector (`agent/internal/asa/ssh.go` + parser + tests).
- Plan 11-09: FMC collector (`agent/internal/fmc/client.go` + `types.go` + tests).
- Plan 11-10: Checkpoint shared parser + live collector + import collector (`agent/internal/checkpoint/parser.go` + `live.go` + `import.go` + `types.go` + tests). Single plan because parser is shared between live + import.

  Files modified: each plan owns a disjoint package — fully parallel.

**Wave 4 (wiring + governance, sequential):**
- Plan 11-11: Wire collectors to the dispatch in `collectAndPushFirewall` (extends `agent/cmd/infracanvas-agent/main.go`). Snapshot-ID minting site lives here.
- Plan 11-12: TTL prune `taskiq_periodic` job (`backend/app/tasks/firewall_prune.py` NEW). Independent of 11-11 — could be parallelized but small.
- Plan 11-13: CAB packet extension (`agent/docs/cab/threat-model.md` + `architecture.md` + `dataflow.md` + `known-limitations.md`). Sequential after collectors land so the threat IDs reference real code paths. **Mark as `autonomous: false`** with `checkpoint:human-verify` gate (mirrors Phase 10 plan 10-09 pattern).
- Plan 11-14: Phase verification + manual GitHub-style smoke checkpoint (mirrors Phase 7.5 plan 11 / Phase 10 plan 10-08 task 3).

**Total: 14 plans (Wave 0: 1, Wave 1: 3, Wave 2: 3, Wave 3: 4, Wave 4: 4 — but planner may consolidate).** Estimate aligns with prior firewall-comparable phases (Phase 10 was 9 plans, Phase 11 carries new collectors × 4 + backend × 3 + scaffolding + governance which legitimately exceeds 9).

**Plans flagged for `autonomous: false` (human review required):**
- Plan 11-13 (CAB packet extension) — DCA-09 follow-on; Phase 10 plan 10-09 used the same gate.
- Plan 11-14 (final verification + smoke checkpoint) — operator runs against real or fixture-based vendor APIs.

## Risk Landmines

1. **ASA REST API EOL at 9.16** — Already covered in Pitfall 1. Highest-impact landmine; CAB language and operator runbook MUST surface it.

2. **Snapshot storage explosion** — Pitfall 7. Worst-case 800GB per large customer over 30 days. Recommendation: ship 7-14 day default TTL, document 30-day option.

3. **FMC token-refresh complexity** — Pitfall 3. Implementable but easy to get wrong. Recommend Wave 0 test fixture covers the 401-then-refresh-then-200 path explicitly.

4. **Checkpoint SID timeout on large rule bases** — Pitfall 2. Mitigation: pass `session-timeout: 3600` on login. If a customer has > 50k rules per layer, even 1 hour can be tight; document as known-limitation L-N.

5. **ASA SSH parser fragility** — Phase 10 T-10-05-03 already documents the linear-regex strategy. ASA `show running-config` is more verbose than IOS-XE `show ip route`; the parser will need broader patterns. Recommend the test corpus include a real-world `show running-config` from an ASA 9.18+ deployment with at least 100 ACL entries.

6. **Phase 12 forward-feed contract stability** — D-15 makes column names a hard contract. Plan 11-01 (migration) should add a doc-comment in the migration file explicitly listing the columns Phase 12 reads, so future migrations think twice before renaming.

7. **`mgmt_cli` JSON shape vs live API JSON shape divergence** — A6 Assumption. If shapes diverge, the "shared parser" decision (D-12) breaks. Mitigation: Wave 0 commits paired live + import fixture files; parser test asserts equivalence (`TestParser_LiveImportEquivalence`). If shapes diverge, raise to discuss-phase before Wave 3 lands.

8. **CKP-02 file path UX (open question 3)** — If planner chooses three-file layout, operator runbook must be explicit about the naming convention (`<base>.rulebase.json` / `.nat.json` / `.objects.json`) since `mgmt_cli` does not produce these names natively.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified against either Phase 10 source or official vendor docs.
- Vendor APIs: HIGH for FMC + Checkpoint (official Cisco docs + Checkpoint sc1 docs); HIGH-with-warning for ASA REST (verified that it is EOL at 9.16, which is the load-bearing fact).
- Architecture / Phase 10 inheritance: HIGH — verified by direct read of `main.go`, `config.go`, `push/client.go`, `routes/agent.py`, `schemas/agent.py`, migration `010_dc_sites`, `cab/threat-model.md`.
- Backend schema / RLS pattern: HIGH — `dc_sites` migration provides a copy-able template for all four new tables.
- Pitfalls: MEDIUM-HIGH — Pitfall 1 (ASA REST EOL), Pitfall 4 (`terminal pager 0`), Pitfall 5 (Checkpoint layer discovery), Pitfall 6 (FMC domain UUID) all verified. Pitfall 7 (snapshot growth math) is HIGH-confidence math but speculative customer profile.
- Plan decomposition: MEDIUM — 14 plans is a reasonable estimate but planner may consolidate or split. Wave dependency graph is sound.

**Research date:** 2026-05-10
**Valid until:** 2026-06-09 (30 days; vendor APIs are stable and Phase 10 inheritance is locked code)

## RESEARCH COMPLETE
