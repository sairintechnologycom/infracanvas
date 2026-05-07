# Phase 10: DC Agent Core - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-07
**Phase:** 10-dc-agent-core
**Areas discussed:** Repo/module location, Agent provisioning + auth, Device credential storage, NetFlow buffer strategy

---

## Repo/module location

| Option | Description | Selected |
|--------|-------------|----------|
| agent/ subfolder in this repo | New agent/ directory at repo root, Go module co-located with Python CLI. One PR, one release cut. | ✓ |
| Separate repo (infracanvas-agent) | Independent repo with separate versioning. Cross-repo coordination required. | |

**User's choice:** agent/ subfolder in this repo (monorepo)

| Option | Description | Selected |
|--------|-------------|----------|
| Standard Go layout: cmd/ + internal/ | agent/cmd/infracanvas-agent/main.go + agent/internal/{netconf,ssh,netflow,push,config}/ | ✓ |
| Flat: agent/*.go | All code at agent/ root level | |

**User's choice:** Standard Go layout (cmd/ + internal/)

| Option | Description | Selected |
|--------|-------------|----------|
| Shared semver tag (v0.X.Y) — same tag releases both | One git tag triggers both Python CLI wheel and Go agent binary builds | ✓ |
| Independent agent version tag (agent/v0.X.Y) | Separate tags for independent version bumps | |
| You decide | Leave to Claude's discretion | |

**User's choice:** Shared semver tag

---

## Agent provisioning + auth

| Option | Description | Selected |
|--------|-------------|----------|
| Dashboard-generated site token | Team owner creates DC site, copies one-time token, pastes into agent.yaml. Revocable per site. | ✓ |
| Pre-shared API key in config | Static team-level API key, less granular, harder to rotate per-site. | |
| mTLS mutual certificate | CA-signed cert per site. Requires PKI infra — significant overhead for solo-founder. | |

**User's choice:** Dashboard-generated site token

| Option | Description | Selected |
|--------|-------------|----------|
| Authorization: Bearer <site_token> header | Standard HTTP bearer token; consistent with existing Clerk JWT middleware shape. | ✓ |
| X-Agent-Token custom header | Non-standard; no benefit over Bearer. | |

**User's choice:** Authorization: Bearer header

| Option | Description | Selected |
|--------|-------------|----------|
| Backend only in Phase 10 — dashboard UI later | Ships POST /v1/sites endpoint + token generation; dashboard UI deferred. | ✓ |
| Include minimal dashboard token page | /settings/sites page in Phase 10. More scope but self-service from day 1. | |

**User's choice:** Backend only in Phase 10; dashboard UI later

---

## Device credential storage

| Option | Description | Selected |
|--------|-------------|----------|
| Plaintext in agent.yaml with file-permission guidance | chmod 600; CAB packet documents security model explicitly. | ✓ |
| Env vars referenced from config | $ENV_NETCONF_PASS references in config. Better for automation, more ops complexity. | |
| Encrypted config (AES-256, passphrase at startup) | Encrypted at rest but breaks unattended daemon restarts. | |

**User's choice:** Plaintext in agent.yaml with chmod 600 guidance

| Option | Description | Selected |
|--------|-------------|----------|
| devices[] array with per-device creds | One agent.yaml, multiple devices. Each entry: host, port, protocol, username, password, site_id. | ✓ |
| One device per agent instance | One process per device. Simpler config, more processes to manage. | |

**User's choice:** devices[] array — one agent process manages multiple devices

---

## NetFlow buffer strategy

| Option | Description | Selected |
|--------|-------------|----------|
| In-memory ring buffer, drop oldest on overflow | Fixed-size ring buffer (~5min capacity). On flush failure: retry twice then drop + log count. Stateless agent. | ✓ |
| Disk-backed queue (local file) | Write flows to local file; flush from file. Survives restarts and longer outages. More complex. | |
| Drop immediately on failure | Discard batch on HTTP failure; no buffering beyond 30s collection window. | |

**User's choice:** In-memory ring buffer with retry-twice-then-drop

| Option | Description | Selected |
|--------|-------------|----------|
| JSON-encoded batch in HTTP POST body | POST /v1/agent/flows with JSON array. Same pattern as route push. | ✓ |
| NDJSON (newline-delimited JSON) | Streaming-friendly but no real benefit at 30s batch size. | |
| Protobuf / binary encoding | More efficient but requires schema management + generated Go code. Overkill for Phase 10. | |

**User's choice:** JSON-encoded batch in HTTP POST body

---

## Claude's Discretion

None — all areas had user-confirmed choices.

## Deferred Ideas

- Dashboard UI for site token management (`/settings/sites`) — Phase 11+
- mTLS per-site certificates — Enterprise tier (v1.2+)
- Disk-backed NetFlow queue — After Phase 10 in-memory approach is validated
- Protobuf push encoding — Deferred until high-volume customer demand
- CPC-02 flow-log-driven attribution — Phase 12 (confirmed carry-over from Phase 9)
