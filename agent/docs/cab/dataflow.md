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

## Encryption in Transit

| Channel | Protection | Notes |
|---------|-----------|-------|
| Agent → Backend (TB-2) | TLS 1.2+ via Go stdlib `net/http` defaults | Certificate chain validated against the host trust store. No custom CA pinning in Phase 10 (deferred — see [known-limitations.md](./known-limitations.md) L-6). |
| Agent → NETCONF device (TB-1) | SSH-encrypted NETCONF transport | RFC 6242 (NETCONF over SSH); host-key verification posture documented in L-1. |
| Agent → SSH device (TB-1) | SSH-encrypted CLI transport | Host-key verification posture documented in L-1. |
| NetFlow exporter → Agent (TB-1) | **Not encrypted** | NetFlow v9 / IPFIX is a UDP-only legacy protocol with no encryption. Mitigated by deploying the agent on the management VLAN; see L-4. |

## Encryption at Rest

| Datum | Where | Posture |
|-------|-------|---------|
| `agent.yaml` (creds + token) | Agent host filesystem | Plaintext. Protected by Unix file permissions only (`chmod 600`). See [known-limitations.md](./known-limitations.md) L-2 for rationale and remediation path. |
| Site token (server side) | Backend Postgres | The backend stores the **SHA-256 hash** of the site token (not the plaintext). The plaintext is returned exactly once at issuance via `POST /v1/sites` and never persists in the cloud. |
| Routes / flows | Backend Postgres + R2 | Cloud provider–managed encryption at rest (Neon Postgres, Cloudflare R2). Out of scope for the agent CAB review. |
| NetFlow ring buffer | Process memory only | Lost on agent restart. No disk spill. See L-5. |

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

> **Operator note:** the `chmod 600` requirement on `agent.yaml` is
> enforced by the operator (see [operator-runbook.md](./operator-runbook.md)
> Step 2). The agent does not refuse to start if the permissions are wider,
> but a hardening warning is on the deferred-items list.
