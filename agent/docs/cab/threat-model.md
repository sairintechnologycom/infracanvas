# Threat Model (STRIDE)

This document is the consolidated STRIDE threat register for the
InfraCanvas DC Agent at the Phase 10 baseline. It rolls up the
per-component threat models that were authored alongside each
implementation work-item into a single review surface, organised by
trust boundary.

## Methodology

Threats are classified using **STRIDE**:

- **S**poofing — falsifying identity (of a peer, of the agent, of a
  device).
- **T**ampering — unauthorised modification of data in transit, at rest,
  or in flight through the agent.
- **R**epudiation — inability to prove that an action did or did not
  occur.
- **I**nformation Disclosure — leaking data to a party that should not
  see it.
- **D**enial of Service — preventing legitimate operation.
- **E**levation of Privilege — gaining capabilities beyond the assigned
  authorization.

Each threat is recorded with a **disposition**:

- **mitigate** — control implemented in Phase 10 code or configuration.
- **accept** — known residual risk; documented and tracked for future
  remediation in [known-limitations.md](./known-limitations.md).
- **transfer** — customer / operator responsibility (e.g. firewall
  rules, file permissions).

Trust boundaries are defined in [dataflow.md](./dataflow.md):

- **TB-1** — Network device → Agent
- **TB-2** — Agent → Cloud backend
- **TB-3** — Filesystem → Agent process

Threat IDs use the form `T-10-NN-MM` where `NN` identifies the
implementation work-item and `MM` is the local sequence. The IDs are
preserved verbatim from the originating work-items so traceability is
preserved across the engineering history.

---

## Threat Register

### Trust Boundary 1 — Network Device → Agent (TB-1)

| Threat ID | STRIDE | Component | Disposition | Mitigation |
|-----------|--------|-----------|-------------|-----------|
| T-10-04-01 | Spoofing | NETCONF / SSH MITM on management VLAN | accept | `ssh.InsecureIgnoreHostKey()` in initial implementation. Operators advised to deploy on the management VLAN where the trust assumption is "no untrusted hosts on this VLAN". Remediation deferred to enterprise tier — see [known-limitations.md](./known-limitations.md) L-1. |
| T-10-04-02 | Information Disclosure | password log leakage via NETCONF auth | mitigate | Password held only in `ssh.Password()` auth method; never logged via zap fields. Log lines emit `host` and `protocol` only. |
| T-10-04-03 | Denial of Service | malicious XML reply (XXE, billion laughs) | mitigate | Go `encoding/xml` does not resolve external entities by default. Library has a default token-buffer ceiling; oversize replies are returned as parse errors, not panics. A regression test locks the panic-free path. |
| T-10-04-04 | Tampering | adversary-controlled device returns forged routes | accept | Phase 10 has no path-truthing layer. Phase 12 NetFlow correlation will detect routes that don't match observed traffic. Logged as known limitation. |
| T-10-04-05 | Denial of Service | NETCONF dialer hang | mitigate | `ssh.ClientConfig.Timeout = 10s`; `ctx` cancellation propagates through the dialer; daemon ticker cadence (5 min routes) bounds blast radius to one cycle per device. |
| T-10-05-01 | Spoofing | SSH-CLI MITM | accept | Same posture as T-10-04-01. |
| T-10-05-02 | Information Disclosure | password leakage via PTY echo | mitigate | `cryptossh.TerminalModes{ECHO: 0}` set before any payload write. |
| T-10-05-03 | Denial of Service | adversarial `show ip route` output | mitigate | Linear-time regex parser; non-matching lines silently skipped. No backreferences or unbounded quantifiers. |
| T-10-05-04 | Tampering | crafted route line bypasses parser | accept | Same residual as T-10-04-04 — Phase 12 NetFlow correlation will catch it. |
| T-10-05-05 | Information Disclosure | config-import file world-readable | transfer | Operator `chmod 600` (documented in [operator-runbook.md](./operator-runbook.md) Step 2). |
| T-10-05-06 | Denial of Service | YAML billion-laughs in static route file | mitigate | `gopkg.in/yaml.v3` v3.0.1 enforces alias-depth limits; parse errors return cleanly rather than allocating exponentially. |
| T-10-05-07 | Denial of Service | "More" pager truncation in SSH show output | mitigate | `terminal length 0` issued before `show ip route` so the device disables paging. Regression-tested. |
| T-10-06-01 | Denial of Service | malicious / malformed NetFlow packet | mitigate | `DecodeFunc` errors logged at WARN; the read loop continues. The agent does not panic on malformed input. |
| T-10-06-02 | Denial of Service | flood fills NetFlow ring buffer | mitigate | Fixed-capacity circular buffer; oldest records overwritten. Push-tick drains every 30 s; ≈ 5 min of headroom at 333 records/sec. |
| T-10-06-03 | Denial of Service | hung `ReadFromUDP` blocks shutdown | mitigate | `SetReadDeadline(now + 500ms)` on every loop iteration so context cancellation is observed within 500 ms. |
| T-10-06-04 | Tampering | spoofed-source NetFlow pollutes template cache | transfer | Operator-controlled ACL on the management VLAN limits which hosts can send to UDP/2055. |
| T-10-06-05 | Information Disclosure | UDP socket binds 0.0.0.0 by default | mitigate | Default `:2055`; operator may override with a management-VLAN or loopback bind address. The runbook recommends scoping. |

### Trust Boundary 2 — Agent → Cloud Backend (TB-2)

| Threat ID | STRIDE | Component | Disposition | Mitigation |
|-----------|--------|-----------|-------------|-----------|
| T-10-02-01 | Spoofing | site-token forgery | mitigate | Token is `secrets.token_urlsafe(32)`; backend stores SHA-256 lookup hash, so 2^256 search space. Plaintext is never persisted in the cloud. |
| T-10-02-02 | Tampering | replay attack on push | accept | TLS prevents in-transit replay; tokens are long-lived per-site (revocable by row delete). Token rotation deferred to enterprise tier — see L-3. |
| T-10-02-03 | Information Disclosure | site_token in CreateSiteResp body | mitigate | Token returned exactly once at `POST /v1/sites`; only the SHA-256 hash is stored. |
| T-10-02-04 | Elevation of Privilege | non-owner creates a DC site | mitigate | `Depends(require_role("owner"))` reuses existing Clerk RBAC. |
| T-10-02-05 | Information Disclosure | cross-team data leak via site_id | mitigate | Postgres RLS (`team_isolation` policy) on `dc_sites`; `app.current_team_id` set after principal resolution. |
| T-10-02-06 | Denial of Service | unbounded routes / flows array in push body | mitigate | Pydantic `Field(..., max_length=10000)` on push-body lists. |
| T-10-02-07 | Repudiation | agent claims push, server has no record | accept | Phase 10 logs receipt with `site_id` + count; the structured-log drain (Axiom) provides retention. Phase 11+ adds DB persistence and a UI. |
| T-10-02-08 | Tampering | malicious `site_id` triggers SQL injection | mitigate | Pydantic `str` field; never interpolated into SQL — only used parameterised. |
| T-10-07-01 | Spoofing | DNS spoofing of `backend_url` | mitigate | TLS cert validation by default; `backend_url` is pinned in `agent.yaml`. Operator chooses the value, then the validation chain resists hijack. |
| T-10-07-02 | Information Disclosure | site_token logged in error message | mitigate | The push client logs the *response* body sample (not the request). The `Authorization` header is set on the request and is never echoed. |
| T-10-07-03 | Tampering | replay window for retried requests | accept | All retry attempts carry the same payload; observability log dedup is operator-side. Idempotency tokens deferred. |
| T-10-07-04 | Denial of Service | server returns 200 with garbage body | accept | Backend correctness is the backend's contract. The agent only retries on transport-layer or 5xx errors. |
| T-10-07-05 | Denial of Service | infinite retry loop | mitigate | 3-attempt cap; per-request 15 s timeout; `ctx` propagation. |
| T-10-07-06 | Denial of Service | huge response body fills agent memory | mitigate | `io.CopyN(&sample, body, 512)` caps the snippet read so the agent never reads an unbounded response body. |
| T-10-07-07 | Tampering | malformed JSON crash from `goflow2` | mitigate | Decode errors return Go errors; the produced `FlowRecord` types are statically typed. |

### Trust Boundary 3 — Filesystem → Agent Process (TB-3)

| Threat ID | STRIDE | Component | Disposition | Mitigation |
|-----------|--------|-----------|-------------|-----------|
| T-10-01-01 | Tampering | `go.sum` tampering / dependency confusion | mitigate | `go.sum` committed; `go mod verify` gated in CI and at release time. |
| T-10-01-02 | Information Disclosure | `agent.yaml` committed by mistake | mitigate | `agent/.gitignore` contains `/agent.yaml`. |
| T-10-03-01 | Information Disclosure | `agent.yaml` committed by mistake (config loader) | mitigate | Same control as T-10-01-02. |
| T-10-03-02 | Denial of Service | YAML billion-laughs / deep recursion in `agent.yaml` | mitigate | yaml.v3 default alias-depth limits. |
| T-10-03-03 | Denial of Service | runaway tick goroutines on shutdown | mitigate | `sync.WaitGroup` gates shutdown; `signal.NotifyContext` cancels the parent context. |
| T-10-03-04 | Tampering | env-var override of `version` at runtime | accept | `version` is build-time `-ldflags` injection only — there is no runtime override path. |
| T-10-08-01 | Tampering | dependency confusion / supply chain | mitigate | `go mod verify` in CI and release; pinned versions. |
| T-10-08-02 | Spoofing | adversary commits and pushes a tag | accept | Repo permissions and branch protection. Tag signing deferred to enterprise tier. |
| T-10-08-03 | Tampering | binary modified between build and download | mitigate | TLS to github.com; SHA-256 hashes available via this packet's SBOM. |
| T-10-08-04 | Information Disclosure | tag-name leak via `-ldflags` | accept | Intentional behaviour — `infracanvas-agent version` is required by operators. |
| T-10-08-05 | Tampering | future PR flips `CGO_ENABLED=1` | mitigate | `release.yml` `grep` gate locks the literal `CGO_ENABLED=0` so future refactors cannot silently re-enable cgo (which would change the supply-chain surface and the binary's syscall profile). |

---

## Accepted Risks Summary

The accepted risks above are consolidated for reviewer convenience.
Each is tracked with a remediation path in
[known-limitations.md](./known-limitations.md):

1. **SSH / NETCONF host-key MITM (T-10-04-01, T-10-05-01)** — see L-1.
2. **Long-lived site tokens (T-10-02-02, T-10-07-03)** — see L-3.
3. **No tag signing (T-10-08-02)** — see L-7.
4. **No path-truthing for forged routes (T-10-04-04, T-10-05-04)** —
   Phase 12 NetFlow correlation closes this gap.
5. **No replayability proof (T-10-02-07)** — Phase 11+ adds DB
   persistence; Phase 10 relies on observability-log retention.

## Cross-Cutting Mitigations

These controls apply to multiple boundaries and are easier to reason
about as a single surface:

- **Failure mode is "log + continue", never "panic".** Decode errors at
  any boundary (XML, YAML, NetFlow, JSON) log WARN and continue; the
  agent does not crash on malformed input.
- **Every external read has a deadline.** SSH dial 10 s; HTTP request
  15 s; UDP read 500 ms; routes ticker 5 min; NetFlow flush 30 s.
- **Defense in depth on token redaction.** Token redaction at three
  layers — (a) token is set on the request header at construction time
  and never re-read, (b) response-body snippets are length-capped at
  512 bytes, (c) zap structured-log fields never receive the token at
  any call site.
- **No inbound network surface.** Apart from the optional NetFlow UDP
  listener (which receives one-way traffic from operator-owned
  exporters on the management VLAN), the agent never accepts inbound
  connections.
- **No persistent state on disk.** The agent reads `agent.yaml` once
  at startup; it does not write to disk. NetFlow records live only in
  the in-memory ring buffer.
- **Operator-managed secrets posture.** Device credentials and the
  site token live in `agent.yaml` only; the agent never copies them
  out of process memory; the operator is responsible for filesystem
  permissions (see [operator-runbook.md](./operator-runbook.md) Step 2).

## Future-Phase Threats (out of scope for this packet)

- **Asymmetric-routing / path-correlation engine (Phase 12)** — closes
  the residual on T-10-04-04, T-10-05-04.
- **Token-rotation API (enterprise tier, v1.2+)** — closes T-10-02-02,
  T-10-07-03.
- **mTLS to backend (enterprise tier, v1.2+)** — closes the residual on
  T-10-02-01 (single-factor authentication).
- **Sigstore cosign artifact signing (enterprise tier, v1.2+)** —
  closes T-10-08-02, T-10-08-03 with cryptographic post-download
  attestation.
- **HashiCorp Vault / cloud KMS credential retrieval (enterprise
  tier, v1.2+)** — closes the residual on L-2 (plaintext credentials
  on disk).
