# Data Flow and Classification

This document catalogs every datum the agent reads or produces, classifies
it (operational, secret, PII), and records whether it crosses a trust
boundary. The objective is to give a reviewer a single page from which they
can answer the question "what data leaves my network?" with confidence.

## Trust Boundaries

| ID | Boundary | Crossed by |
|----|----------|-----------|
| **TB-1** | Network device → Agent | NETCONF reply XML, SSH command stdout, NetFlow UDP packets |
| **TB-2** | Agent → Cloud backend | HTTPS POST with `Bearer site_token` + JSON payload |
| **TB-3** | Filesystem → Agent process | `agent.yaml` read at startup; static route files read on tick |

These three boundaries are referenced throughout
[threat-model.md](./threat-model.md). Internal goroutine-to-goroutine
state transfer is not classified as a trust boundary — the daemon is a
single OS process with no IPC.

## Data Inventory

| Datum | Source | Storage Lifetime | Classification | Crosses Trust Boundary? |
|-------|--------|------------------|----------------|------------------------|
| Device username | `agent.yaml` | Process lifetime + host filesystem | **Secret** (operational) | NO — never transmitted |
| Device password | `agent.yaml` | Process lifetime + host filesystem | **Secret** (operational) | NO — never transmitted |
| Site token | `agent.yaml` | Process lifetime + host filesystem | **Secret** (auth credential) | YES — sent in `Authorization: Bearer` header to `api.infracanvas.dev` over HTTPS (TB-2) |
| Routes (prefix, next-hop, protocol, metric) | NETCONF / SSH / file | In-memory until next push tick (≤ 5 min) | Operational | YES — POST `/v1/agent/routes` over HTTPS (TB-2) |
| NetFlow records (5-tuple, bytes, packets, sampler IP) | UDP/2055 (TB-1) | In-memory ring buffer (≈ 5 min capacity) | Operational (network metadata) | YES — POST `/v1/agent/flows` over HTTPS (TB-2) |
| NetFlow template cache | NetFlow packets | In-memory; reset on restart | Operational | NO — used only to decode subsequent records |
| Decoded sampler IPs | NetFlow packet src | In-memory template cache | Operational | NO — not pushed beyond the aggregate FlowRecord `src_ip` field |
| Daemon logs | stdout / stderr | Operator-managed (e.g. `systemd-journald`) | Operational + diagnostic | NO — local-only unless operator forwards |
| Backend URL | `agent.yaml` | Process lifetime + host filesystem | Operational | YES — used as the connect target |
| Build version string | embedded (`-ldflags`) | Process lifetime | Operational | NO — Phase 10 does not include version in push payloads |
| Firewall rule-base (src/dst zone, src/dst CIDR, action, protocol, ports, position, raw_blob) | ASA REST / ASA SSH / FMC / Checkpoint Mgmt API / `mgmt_cli` export file (TB-1) | In-memory until next push tick (≤ 1h) | Operational | YES — POST `/v1/agent/firewall-rules` over HTTPS (TB-2); team-RLS-scoped in backend `firewall_rules` table |
| Firewall NAT table (src/dst translation, interface_in, interface_out, position, raw_blob) | ASA REST / ASA SSH / FMC / Checkpoint Mgmt API / `mgmt_cli` export file (TB-1) | In-memory until next push tick (≤ 1h) | Operational | YES — POST `/v1/agent/firewall-nat` over HTTPS (TB-2); team-RLS-scoped in backend `firewall_nat_rules` table |
| Firewall objects (host / network / group / service definitions; `kind` + `name` + `value` + `raw_blob`) | ASA REST / ASA SSH / FMC / Checkpoint Mgmt API / `mgmt_cli` export file (TB-1) | In-memory until next push tick (≤ 1h) | Operational | YES — POST `/v1/agent/firewall-objects` over HTTPS (TB-2); team-RLS-scoped in backend `firewall_objects` table |
| Firewall mgmt username | `agent.yaml` (`devices[].username` for `asa-rest`/`asa-ssh`/`fmc`/`checkpoint`) | Process lifetime + host filesystem | **Secret** (operational) | NO — never transmitted; presented to vendor API on each pull only |
| Firewall mgmt password | `agent.yaml` (`devices[].password`) | Process lifetime + host filesystem | **Secret** (operational) | NO — never transmitted; presented to vendor API on each pull only |
| ASA REST `X-Auth-Token` | `POST /api/tokenservices` response (TB-1 inbound) | In-memory; scoped to a single Pull; best-effort DELETE on cleanup; ASA-side 30-min expiry | **Secret** (auth credential) | NO — never logged (T-11-08-05), never written to disk, never returned in any push payload |
| Cisco FMC `X-auth-access-token` + refresh token | `POST /api/fmc_platform/v1/auth/generatetoken` response (TB-1 inbound) | In-memory; up to 3 refreshes; 30-min access TTL; FMC-side server expiry | **Secret** (auth credential) | NO — never logged (T-11-10-01 / Pattern G), never written to disk, never in any push payload |
| Cisco FMC `DOMAIN_UUID` | Auth response header (TB-1 inbound) | In-memory; per-Pull | Operational (tenant identifier) | NO — used only to construct GET URL paths server-side of the agent; not present in push payloads |
| Checkpoint SID (`X-chkp-sid`) | `POST /web_api/login` response (TB-1 inbound) | In-memory ONLY; login-per-pull (D-14); seconds-to-minutes lifetime per pull; logged out at end of pull | **Secret** (auth credential) | NO — never logged (T-11-11-01; verified by test grep on captured log bytes), never written to disk, never in any push payload, never present at rest (no SID at rest, D-14) |
| Firewall snapshot_id (UUIDv4) | Minted by agent dispatcher (`uuid.NewString()`) per device per tick (RESEARCH Pattern 2) | In-memory; threaded through 3 push payloads in a single tick | Operational | YES — sent in `snapshot_id` field of all three firewall push bodies; persisted server-side as the PK of `firewall_ruleset_snapshots` |

### Classification scheme

- **Secret**: must never appear in logs, telemetry, or push payloads.
  All secrets in this inventory are either filesystem-local or
  transmitted only inside an HTTPS Authorization header (never in a body
  field).
- **Operational**: routine telemetry; encrypted in transit, but not
  considered sensitive at rest in the cloud.
- **PII**: not collected by Phase 10. The agent does not see end-user
  identifiers, request URLs, application payloads, packet contents, or
  any layer-7 data — only IP-layer and routing-protocol metadata.

## Data NOT Transmitted (Phase 10 hard guarantees)

These are deliberate scope guarantees enforced by the codebase, not
by policy alone:

- **Device usernames and passwords are never included in any push
  payload.** The push payload structures (`internal/push/types.go`) only
  marshal `RoutesPayload` and `FlowsPayload`, and neither contains a
  credential field. There is no path in the codebase from
  `config.Device.{Username,Password}` to the HTTP request body.
- **Device configuration text is not collected.** The agent does not
  invoke `show running-config` or any equivalent NETCONF subtree that
  would return device configuration. Only routing-table state and (in a
  future phase) BGP-neighbour summaries are in scope.
- **Device state is not modified.** NETCONF `<edit-config>` is not
  exercised; SSH `configure terminal` is not entered. The collector
  issues only NETCONF `<get>` and SSH `show ip route`.
- **No layer-7 packet contents are captured.** The NetFlow listener
  decodes only the records the exporter has already aggregated
  (5-tuple + counters); it does not see packet payloads at any point.
- **No outbound connection except to the configured backend URL.**
  There is no telemetry channel, crash-reporter, update-checker, or
  third-party SDK inside the agent.
- **Phase 11 — Firewall management credentials are never included in any
  push payload.** The push payload structures
  (`agent/internal/push/types.go` — `FirewallRulesPayload`,
  `FirewallNATPayload`, `FirewallObjectsPayload`) contain no credential
  field; there is no path from `config.Device.{Username,Password}` to
  the HTTP request body of any firewall push endpoint.
- **Phase 11 — Vendor-API session tokens are never transmitted.** ASA
  REST `X-Auth-Token`, FMC `X-auth-access-token` + refresh token, and
  Checkpoint `X-chkp-sid` live only as HTTP request headers between
  agent and the customer's firewall management plane; they are never
  echoed to the SaaS backend, never logged, and never written to disk.
- **Phase 11 — Firewall device configuration outside the rule base is
  not collected.** The ASA SSH collector parses ONLY access-list / NAT
  / object lines from `show running-config`; it does not extract
  general device configuration, interface configuration, routing
  protocol configuration, AAA configuration, SNMP configuration, or
  any other surface of the running-config. ASA REST / FMC / Checkpoint
  GETs are scoped to the rules / NAT / objects endpoints only — no
  device-status, user, or audit-log endpoints are exercised.
- **Phase 11 — Firewall device state is not modified.** All four
  collectors execute only read-side commands. There is no
  `add-*` / `set-*` / `delete-*` / `publish` call to Checkpoint, no
  `POST` / `PATCH` / `PUT` to ASA or FMC configuration endpoints
  beyond auth (and a best-effort `DELETE` of the agent's own ASA
  token), and no `configure terminal` / `write memory` in any SSH
  session. The four collectors' command lists are hardcoded in source
  — see the [threat-model.md](./threat-model.md) "Phase 11 — Firewall
  Management Credential Storage" section for the structural proof and
  reviewer grep guide.

## Encryption in Transit

| Channel | Protection | Notes |
|---------|-----------|-------|
| Agent → Backend (TB-2) | TLS 1.2+ via Go stdlib `net/http` defaults | Certificate chain validated against the host trust store. No custom CA pinning in Phase 10 (deferred — see [known-limitations.md](./known-limitations.md) L-6). |
| Agent → NETCONF device (TB-1) | SSH-encrypted NETCONF transport | RFC 6242 (NETCONF over SSH); host-key verification posture documented in L-1. |
| Agent → SSH device (TB-1) | SSH-encrypted CLI transport | Host-key verification posture documented in L-1. |
| NetFlow exporter → Agent (TB-1) | **Not encrypted** | NetFlow v9 / IPFIX is a UDP-only legacy protocol with no encryption. Mitigated by deploying the agent on the management VLAN; see L-4. |
| Agent → ASA REST device (TB-1, Phase 11) | TLS 1.2+ via Go stdlib `net/http` | `InsecureSkipVerify: false`, `MinVersion: TLS 1.2`. Certificate chain validated against the host trust store (T-11-08-01 accept-posture for MITM, same as L-1 / T-10-04-01). |
| Agent → ASA SSH device (TB-1, Phase 11) | SSH-encrypted CLI transport | Host-key verification posture inherited from Phase 10 `xssh.DefaultDialer` (T-11-09-01 accept; documented in L-1). |
| Agent → Cisco FMC device (TB-1, Phase 11) | TLS 1.2+ via Go stdlib `net/http` | `InsecureSkipVerify: false`, `MinVersion: TLS 1.2`. Same posture as ASA REST (T-11-10-03). |
| Agent → Checkpoint Mgmt server (TB-1, Phase 11) | TLS 1.2+ via Go stdlib `net/http` | `InsecureSkipVerify: false`, `MinVersion: TLS 1.2`. Same posture as ASA REST (T-11-11-03). |

## Encryption at Rest

| Datum | Where | Posture |
|-------|-------|---------|
| `agent.yaml` (creds + token) | Agent host filesystem | Plaintext. Protected by Unix file permissions only (`chmod 600`). See [known-limitations.md](./known-limitations.md) L-2 for rationale and remediation path. |
| Site token (server side) | Backend Postgres | The backend stores the **SHA-256 hash** of the site token (not the plaintext). The plaintext is returned exactly once at issuance via `POST /v1/sites` and never persists in the cloud. |
| Routes / flows | Backend Postgres + R2 | Cloud provider–managed encryption at rest (Neon Postgres, Cloudflare R2). Out of scope for the agent CAB review. |
| NetFlow ring buffer | Process memory only | Lost on agent restart. No disk spill. See L-5. |
| Firewall mgmt credentials (Phase 11) | Agent host filesystem (`agent.yaml`) | Plaintext. Protected by Unix file permissions only (`chmod 600`). Same posture as Phase 10 device credentials — see L-2 / [threat-model.md](./threat-model.md) "Phase 11 — Firewall Management Credential Storage" section. |
| ASA REST `X-Auth-Token` / FMC access+refresh tokens / Checkpoint SID (Phase 11) | Agent process memory ONLY | Never written to disk. ASA token: best-effort `DELETE` on Pull return + 30-min ASA-side expiry. FMC: up-to-3 refreshes + new login on next tick. Checkpoint: login-per-pull + logout, no SID at rest (D-14). |
| `checkpoint-import` export files (Phase 11) | Agent host filesystem (operator-placed) | Operator-managed. Recommended `chmod 600` matching `agent.yaml`. Contains firewall rule-base data (not credentials). See [operator-runbook.md](./operator-runbook.md) Phase 11 section. |
| Firewall rules / NAT / objects / snapshots | Backend Postgres | Cloud provider–managed encryption at rest (Neon Postgres). RLS team_isolation policies on all four tables (`firewall_ruleset_snapshots`, `firewall_rules`, `firewall_nat_rules`, `firewall_objects`); 14-day TTL prune (env-overridable `FIREWALL_SNAPSHOT_TTL_DAYS`). Out of scope for the agent CAB review. |

## Logging Posture

The agent emits structured JSON logs (zap) to stdout/stderr. Log fields
are deliberately scoped:

- Device records are logged by `Host` and `Protocol` only — never the
  `Password` field.
- Push errors log the HTTP status code and a length-capped (≤ 512 byte)
  snippet of the *response* body, never the request body. The
  `Authorization` header is set on the request and is never echoed
  back into a log field.
- The site token never appears in a log field. (Threat IDs T-10-04-02,
  T-10-07-02 in [threat-model.md](./threat-model.md) lock this down.)
- **Phase 11 — Firewall mgmt credentials and vendor session tokens
  never appear in log fields.** Pattern G (the same one that holds
  the site token off the log surface) extends to firewall collectors
  structurally: the ASA REST `Client` / FMC `Client` /
  Checkpoint `LiveCollector` types either have no `*zap.Logger` field
  or restrict log fields to host / protocol / pull_id / counts.
  `TestLiveCollector_LoginPullLogout` regression-tests that the
  captured log byte buffer contains zero occurrences of the
  Checkpoint SID across login → fetch → logout. T-11-08-05 /
  T-11-10-01 / T-11-11-01 in the threat register lock the same
  guarantee down for ASA REST tokens and FMC tokens respectively.

> **Operator note:** the `chmod 600` requirement on `agent.yaml` is
> enforced by the operator (see [operator-runbook.md](./operator-runbook.md)
> Step 2). The agent does not refuse to start if the permissions are wider,
> but a hardening warning is on the deferred-items list.
