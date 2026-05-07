# Phase 10: DC Agent Core - Context

**Gathered:** 2026-05-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Scaffold a standalone Go binary agent (`infracanvas-agent`) that collects network routing and flow data from physical DC devices via NETCONF/RESTCONF (IOS-XE), SSH CLI fallback, or static config file import — then pushes it encrypted to the InfraCanvas cloud backend. Covers: Go module scaffold, NETCONF/SSH collectors, NetFlow v9/IPFIX UDP listener, encrypted push API with site-token auth, daemon timing, cross-compiled release binaries, and the CAB enterprise security-review packet.

**In scope:**
- `agent/` directory at repo root — Go module `github.com/infracanvas/infracanvas/agent`
- `agent/cmd/infracanvas-agent/` — cobra CLI entry point, daemon mode
- `agent/internal/{netconf,ssh,netflow,push,config}/` — collector internals
- Backend: `dc_sites` table + site-token generation endpoint (`POST /v1/sites`) in `backend/`
- GHA release workflow update: cross-compile agent Linux amd64 + macOS arm64 alongside existing Python CLI wheel, triggered by shared `v*` semver tag
- CAB security-review packet: architecture diagram, data flow, threat model, SBOM (DCA-09)

**Out of scope:**
- Dashboard UI for site token management — deferred to Phase 11+
- Asymmetric routing detection, path computation — Phase 12
- Firewall integrations (ASA/Checkpoint) — Phase 11
- Protobuf/binary push encoding
- Disk-backed NetFlow persistence (beyond in-memory ring buffer)

</domain>

<decisions>
## Implementation Decisions

### Repo and module structure (DCA-01, DCA-08)
- **D-01:** Go agent lives in `agent/` subfolder inside the InfraCanvas monorepo. Module path: `github.com/infracanvas/infracanvas/agent`. Standard Go layout: `agent/cmd/infracanvas-agent/main.go` (cobra entry) + `agent/internal/` (netconf, ssh, netflow, push, config packages).
- **D-02:** Shared semver tag — one `v0.X.Y` git tag triggers GHA to build both the Python CLI wheel and the Go agent binaries in the same release job. No separate `agent/vX.Y.Z` tags.

### Agent authentication (DCA-05)
- **D-03:** Dashboard-generated site token model. Team owner creates a DC site in the backend (via `POST /v1/sites` admin endpoint or CLI seed command), receives a one-time token. Token is stored in `agent.yaml`. Phase 10 ships the backend endpoint and agent config reader only — no dashboard UI yet.
- **D-04:** Agent sends `Authorization: Bearer <site_token>` header on all push requests. Backend validates via hashed-token DB lookup → resolves `team_id` + `site_id`. Consistent with existing Clerk JWT middleware shape (different token type, same header).

### Device credential storage (DCA-02, DCA-03, DCA-07)
- **D-05:** Credentials stored as plaintext in `agent.yaml` (chmod 600). CAB packet explicitly documents: credentials are not transmitted to SaaS, not stored in cloud, protected by filesystem permissions alone. Ops teams are expected to use read-only NETCONF service accounts.
- **D-06:** `agent.yaml` supports a `devices[]` array — one agent process manages multiple devices. Per-device config: `host`, `port`, `protocol` (netconf | ssh | config-import), `username`, `password`, and optional `site_id` override.

### NetFlow buffer strategy (DCA-04, DCA-06)
- **D-07:** In-memory ring buffer. Fixed size (enough for ~5 minutes of flow records). On 30-second flush: if HTTP push fails, retry twice (with short backoff), then drop the batch and log the dropped count. No disk I/O or SQLite dependency — agent stays stateless.
- **D-08:** Push format: JSON-encoded batch in HTTP POST body to `POST /v1/agent/flows`. Same JSON-over-HTTPS pattern as route push (`POST /v1/agent/routes`). No protobuf in Phase 10.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §"Category 10 — DC Agent" — DCA-01..09 full requirement text
- `.planning/ROADMAP.md` §"Phase 10: DC Agent Core" — goal, success criteria, dependencies

### Existing backend (push target)
- `backend/app/main.py` — FastAPI app entrypoint; new `/v1/agent/*` and `/v1/sites` routes register here
- `backend/app/routes/` — existing route handler pattern (e.g. `scans.py`, `github.py`) — new agent push routes follow the same structure
- `backend/alembic/versions/` — migration naming pattern; new `dc_sites` table + `site_tokens` (hashed) columns follow prior migrations

### Authentication / token pattern
- `backend/app/auth.py` (or equivalent) — existing Clerk JWT middleware; site-token validation is a parallel path, same `Authorization: Bearer` header convention
- `.planning/phases/08-github-webhook-autoscan/08-CONTEXT.md` — webhook token auth pattern established in Phase 8 (Bearer token validation, hashed storage) — agent token auth follows this precedent

### GHA release workflow
- `.github/workflows/` — existing Python release workflow; agent cross-compile step is added alongside it

### CAB packet precedents
- `.planning/REQUIREMENTS.md` §DCA-09 — CAB deliverable requirements (architecture diagram, data flow, threat model, SBOM)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/routes/github.py` — route handler pattern with Clerk auth + RLS; new agent push routes follow same skeleton but use site-token auth instead of Clerk JWT
- `backend/alembic/` — migration pattern for new tables; `dc_sites` migration follows same up/down structure
- `backend/app/storage/r2.py` — `put_bytes` helper; agent-pushed topology data may be stored to R2 following the same pattern as scan JSON

### Established Patterns
- **Static JSON push**: scan_repo task pushes JSON to R2 via `put_bytes` — agent push to backend follows the same JSON-over-HTTPS approach, just from a Go client
- **Bearer token auth with DB lookup**: Pattern established in Phase 8 webhook token validation; site tokens reuse this pattern (hash token at creation, store hash, validate on every request)
- **TDD discipline**: All backend additions should follow the existing RED→GREEN test pattern (pytest for backend, Go `testing` + `testify` for agent)

### Integration Points
- **Backend push endpoints**: `POST /v1/agent/routes` and `POST /v1/agent/flows` are new FastAPI routes that the agent calls. These need the `dc_sites` token validation middleware.
- **Backend provisioning**: `POST /v1/sites` (admin-only or team-owner-only) creates a `dc_sites` row and returns the plaintext token once (never again). Token hash stored in DB.
- **GHA release**: Existing `release.yml` or equivalent — add a `go build` + `GOOS/GOARCH` matrix step for `linux/amd64` and `darwin/arm64`, attach binaries to the same GitHub release.
- **agent.yaml config file**: Agent reads config from `./agent.yaml` or `/etc/infracanvas/agent.yaml` (walks up or checks system path); same discovery pattern as `cli/infracanvas/config.py`.

</code_context>

<specifics>
## Specific Ideas

- Agent config file shape (user-confirmed):
  ```yaml
  # agent.yaml — chmod 600
  site_token: "ic_site_xxxxxxxxxxxxx"
  backend_url: "https://api.infracanvas.dev"

  devices:
    - host: "192.168.1.1"
      port: 830
      protocol: netconf
      username: "infracanvas-ro"
      password: "secret"
    - host: "192.168.1.2"
      port: 22
      protocol: ssh
      username: "infracanvas-ro"
      password: "secret"
  ```

- CAB packet must document that: (1) device credentials never leave the agent host, (2) only topology/routing data is transmitted, (3) transmission is TLS-encrypted, (4) site token is revocable per-site.

- NetFlow ring buffer: approximately 5 minutes of capacity, with dropped-batch count logged at WARN level so ops teams can detect persistent backend connectivity issues.

</specifics>

<deferred>
## Deferred Ideas

- **Dashboard UI for site token management** — `/settings/sites` page for team owners to create/revoke DC sites. Deferred to Phase 11 or a dedicated dashboard hardening phase.
- **mTLS per-site certificates** — Stronger identity than bearer tokens, but requires PKI infrastructure. Deferred to enterprise tier (v1.2+).
- **Disk-backed NetFlow queue** — Persistent flow storage that survives agent restarts and longer backend outages. Deferred; Phase 10 in-memory ring buffer is sufficient for initial deployment.
- **Protobuf push encoding** — Worth revisiting if high-volume customers emerge. Deferred until demand is validated.
- **CPC-02 (flow-log-driven data transfer attribution)** — Requires NetFlow data from this agent. Deferred to Phase 12 (confirmed in Phase 9 CONTEXT.md).

</deferred>

---

*Phase: 10-DC Agent Core*
*Context gathered: 2026-05-07*
