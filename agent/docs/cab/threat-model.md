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

Threat IDs use the form `T-PP-NN-MM` where `PP` is the originating
phase (`10` for Phase 10 DC-Agent core, `11` for Phase 11 firewall
integration), `NN` identifies the implementation work-item, and `MM`
is the local sequence. The IDs are preserved verbatim from the
originating work-items so traceability is preserved across the
engineering history. Phase 11 (firewall integration) extends the
register **additively** under each existing trust boundary — no Phase
10 row is modified.

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
| T-11-08-01 | Spoofing | MITM on ASA management VLAN (REST channel) | accept | Same posture as T-10-04-01. TLS validation enabled by default (`InsecureSkipVerify: false`, `MinVersion: TLS 1.2`) on the ASA REST `http.Client`; operator-managed cert chain on the device side. |
| T-11-08-02 | Spoofing | ASA REST `/api/tokenservices` 401 misclassified as transient | mitigate | `ErrASAAuth` sentinel returned on 401 from `/api/tokenservices`; `errors.Is(err, ErrASAAuth)` is true so the push client and dispatcher recognize the failure as non-retryable. Error message also contains "401" and "unauthorized" for log greppability. |
| T-11-08-03 | Information Disclosure | ASA REST API EOL at 9.17+ silently misleads operator | mitigate | Package + file doc-comment surfaces the ASA REST EOL boundary in `agent/internal/asa/rest.go`. This packet's [known-limitations.md](./known-limitations.md) L-11-01 lifts the same surface to the operator-facing review. |
| T-11-08-04 | Denial of Service | adversary-controlled ASA returns oversize JSON | mitigate | `io.LimitReader(resp.Body, 16*1024*1024)` caps every authenticated GET at 16 MiB. Token acquire path bounds discard via `io.CopyN(io.Discard, resp.Body, 4096)`. `encoding/json.Unmarshal` returns errors cleanly without panics on malformed payloads. |
| T-11-08-05 | Information Disclosure | ASA REST token leakage via `deleteToken` log path | accept | `deleteToken` uses a fresh `context.WithTimeout(context.Background(), 5*time.Second)` so cleanup survives parent ctx cancellation; errors swallowed silently (Pattern G — token is otherwise tempting to log). ASA times tokens out after 30 min, so a missed cleanup is bounded residual. |
| T-11-09-01 | Spoofing | MITM on ASA management VLAN (SSH channel) | accept | Same posture as T-10-05-01. `InsecureIgnoreHostKey` inherited from `xssh.DefaultDialer`. |
| T-11-09-02 | Information Disclosure | password leakage via PTY echo on ASA SSH | mitigate | `ECHO=0` set by the underlying `xssh.DefaultDialer`. Pattern G (only `host`, `protocol`, and counts logged) enforced in the asa-ssh `Pull` path. |
| T-11-09-03 | Denial of Service | adversarial `show running-config` output | mitigate | All seven regexes in `agent/internal/asa/ssh_parser.go` use bounded character classes (`\S+`, `\s+`, `[a-z]+`); no backreferences or unbounded quantifiers. Non-matching lines silently skipped. Verified by grep acceptance check in CI. |
| T-11-09-04 | Tampering | crafted ACL/NAT line injection in running-config | accept | Same residual class as T-10-05-04 — `raw_blob` preserves the original line text so downstream consumers see the actual config; misclassification surface is bounded by regex specificity. |
| T-11-09-05 | Denial of Service | oversized running-config consumes agent memory | mitigate | `bufio.Scanner.Buffer(make([]byte, 0, 64*1024), 1024*1024)` lifts the per-line cap to 1 MiB while bounding total memory. |
| T-11-09-06 | Denial of Service | ASA pager truncation in SSH path | mitigate | `terminal pager 0` issued before `show running-config` (ASA syntax — distinct from IOS-XE `terminal length 0` used at T-10-05-07). Regression-tested by `TestSSHCollector_DisablesPager` asserting the first command sent is `terminal pager 0`. |
| T-11-10-01 | Information Disclosure | FMC username/password/token logging | mitigate | Pattern G structural: the FMC `Client` has no `*zap.Logger` field; tokens flow only through `req.Header.Set` / `resp.Header.Get`. Verified via `grep -cE 'zap\.String\("(user\|pass\|password\|accessToken\|refreshToken)"' = 0`. |
| T-11-10-02 | Denial of Service | FMC access-token expiry mid-pull | mitigate | `maxRefreshAttempts = 3` constant + per-request refresh-count check at top of `refreshToken`; `ErrFMCAuth` bails out and forces full re-acquire on the next ticker tick. |
| T-11-10-03 | Spoofing | MITM against FMC management plane | accept | TLS-validating default `http.Client` with `InsecureSkipVerify: false` and `MinVersion: TLS 1.2`. Same posture as T-11-08-01 / T-10-04-01. |
| T-11-10-04 | Denial of Service | adversary-controlled FMC unbounded pagination | mitigate | Defensive index checks in `firstZoneName` / `firstNetworkValue` / `firstPortValue` / `firstPortProtocol`; `io.LimitReader(maxResponseBytes)`; hard `maxPages = 1000` cap in `paginatedGet`; collector-level error wraps via `fmt.Errorf`. |
| T-11-10-05 | Elevation of Privilege | hardcoded `DOMAIN_UUID` produces wrong-tenant rules | mitigate | `DOMAIN_UUID` is populated only from the auth response header; the collector refuses to proceed if empty. No caller-overridable domain parameter on `Pull`. |
| T-11-11-01 | Information Disclosure | Checkpoint SID logging at any layer | mitigate | SID is held only in `http.Request.Header` `X-chkp-sid`; never assigned to a zap field. `TestLiveCollector_LoginPullLogout` regression-tests that the captured log byte buffer contains zero SID occurrences across login / fetch / logout. |
| T-11-11-02 | Denial of Service | Checkpoint SID timeout mid-pull on large rule layers | mitigate | Login passes `"session-timeout": 3600` in the request body (Pitfall 2 mitigation). For pulls that legitimately exceed 1 hour the operator falls back to `checkpoint-import`; surfaced in [known-limitations.md](./known-limitations.md) L-11-02. |
| T-11-11-03 | Spoofing | MITM against Checkpoint management plane | accept | TLS-validating default `http.Client` with `InsecureSkipVerify: false` and `MinVersion: TLS 1.2`. Same posture as T-11-08-01 / T-11-10-03. |
| T-11-11-04 | Tampering | crafted `checkpoint-import` JSON injects false rules | accept | Operator-controlled file. `raw_blob` preserves the original rule envelope so any downstream forensic review sees the actual bytes. `chmod 600 agent.yaml` limits who can declare the `config_file` path (TB-3). |
| T-11-11-05 | Denial of Service | adversary-controlled Checkpoint unbounded pagination | mitigate | Pagination terminator `response.To >= response.Total`; hard `maxPages = 10000` cap (5M-row ceiling) in the live collector loop. `io.LimitReader` caps per-response body size. |
| T-11-11-06 | Information Disclosure | Checkpoint SID logout failure leaks SID lifetime | mitigate | Logout is best-effort; failure WARNs without propagating. SID is bounded by `session-timeout` server-side regardless of client logout success (D-14 — login-per-pull means no SID at rest under any failure mode). |

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
| T-11-02-01 | Denial of Service | unbounded `rules` / `nat_rules` / `objects` list in firewall push body | mitigate | Pydantic `Field(..., max_length=50000)` on every firewall push-body list (`backend/app/schemas/firewall.py`). Higher than Phase 10's 10k bound because enterprise rule bases can legitimately exceed 10k. |
| T-11-02-02 | Information Disclosure | cross-team firewall data leak via missing RLS on the four firewall tables | mitigate | `ENABLE` + `FORCE ROW LEVEL SECURITY` on `firewall_ruleset_snapshots`, `firewall_rules`, `firewall_nat_rules`, `firewall_objects` (migration `011_firewall_tables`). Child policies enforce team-scope via `snapshot_id IN (SELECT snapshot_id FROM firewall_ruleset_snapshots WHERE team_id = current_setting('app.current_team_id', true)::uuid)`. `app.current_team_id` is set inside every transaction via `set_config(..., true)` (Pattern B). |
| T-11-02-03 | Elevation of Privilege | future migration silently drops Phase 12 forward-feed columns (D-15) | mitigate | Doc-comment at the top of `20260510_011_firewall_tables.py` lists the locked column names (`src_cidr`, `dst_cidr`, `action`, `protocol`, `ports`, `src_translation`, `dst_translation`, `interface_in`, `interface_out`) so future renames require coordinated review with Phase 12. |
| T-11-02-04 | Tampering | crafted JSONB `raw_blob` causes SQL injection or storage corruption | accept | Pydantic `dict` parse; Postgres `JSONB` treats keys as data (no SQL surface). Bound through the `max_length=50000` parent list cap and a per-row `raw_blob` size policy enforced upstream by the vendor collector's `io.LimitReader`. |
| T-11-02-05 | Denial of Service | snapshot storage explosion via aggressive operator polling | mitigate | TTL-prune task `prune_firewall_snapshots` (`backend/app/queue/tasks/firewall_prune.py`) DELETEs `firewall_ruleset_snapshots WHERE snapshot_ts < NOW() - INTERVAL '<FIREWALL_SNAPSHOT_TTL_DAYS> days'`. Default 14 days. Child rows cascade. Per-team transaction so a partial failure does not roll back already-pruned teams. |
| T-11-03-01 | Repudiation | push handler crash mid-bulk-insert leaves orphan parent snapshot | mitigate | `INSERT ... ON CONFLICT (snapshot_id) DO NOTHING` on the parent (`firewall_ruleset_snapshots`); children chunked at 500 rows per asyncpg multi-row INSERT inside a single transaction. Crash → entire transaction rolls back. Successful child-insert without later failure is the only durable outcome. |
| T-11-03-02 | Denial of Service | malicious bulk-insert chunk size triggers asyncpg protocol limit | mitigate | Chunk size fixed at 500 rows per multi-row `INSERT` (RESEARCH Open Q4). Matches Checkpoint paginate-by-500 mental model; well within asyncpg statement-length envelope at the 50k-rule cap. |
| T-11-03-03 | Information Disclosure | push handler log surface contains secrets | mitigate | Handler logs `site_id`, `team_id`, `snapshot_id`, `firewall_id`, and counts only. Payload body never echoed. Pattern G structurally enforced (no secret-named fields exist on push handlers' log paths). |
| T-11-03-04 | Tampering | child re-insert on partial-fail retry produces duplicate child rows | accept | `uuid.uuid4()` minted at handler call time for `rule_id` / `nat_id` / `object_id` means a retried push of the same parent `snapshot_id` could insert duplicate children. Mitigation: D-07 push-client retry-twice-then-drop confines the blast radius; D-10 snapshot-per-pull replace means the next hourly tick overwrites with a fresh `snapshot_id`. Residual is bounded transient state, deleted by TTL prune within 14 days. |
| T-11-03-05 | Elevation of Privilege | push handler fails to set `app.current_team_id` GUC and writes cross-team rows | mitigate | Every handler runs `await session.execute(text("SELECT set_config('app.current_team_id', :t, true)"), {"t": str(principal.team_id)})` as the first transaction statement. The `FORCE ROW LEVEL SECURITY` policy then blocks any cross-team `INSERT` via the `WITH CHECK` clause. |
| T-11-04-01 | Information Disclosure | cross-team `site_id` probe leaks site existence on read endpoint | mitigate | `GET /v1/sites/{site_id}/firewall-rules` performs the site-membership probe FIRST (mirrors `github.py:144-152`); RLS hides Team B's `DCSite` row from Team A's transaction, so the lookup returns `404 site_not_found_or_no_access` before any firewall query runs. Regression-tested by `test_cross_team_isolation`. |
| T-11-04-02 | Denial of Service | unbounded join expansion on read endpoint | mitigate | Per-kind IN-list queries (N+0 not N+3) bounded by the 50k child-row cap (T-11-02-01) per snapshot. DISTINCT ON `(firewall_id) ORDER BY firewall_id, snapshot_ts DESC` uses the composite `ix_fw_ruleset_latest` index for index-only latest-per-device retrieval. |
| T-11-04-03 | Elevation of Privilege | read endpoint role allows team `basic_member` to view firewall rules | accept | `_READ_ROLES = ("owner", "admin", "member", "basic_member")` — same role set as `github.py` read endpoints. Firewall rule-base content is treated as the same sensitivity class as the existing route-and-flow telemetry already exposed at this role level. |
| T-11-04-04 | Information Disclosure | read endpoint response includes credential-shaped fields | mitigate | Response model is the typed `FirewallRulesetSnapshotResp` envelope which serializes only the normalized rule columns + `raw_blob`. The `raw_blob` is the vendor-native rule structure (action, source, dest, etc.) — it does NOT contain ASA tokens, FMC tokens, or Checkpoint SIDs because the agent collectors never marshal credential headers into `raw_blob`. |
| T-11-05-01 | Information Disclosure | push client logs firewall payload body | mitigate | Push methods (`PushFirewallRules`, `PushFirewallNAT`, `PushFirewallObjects`) reuse `postWithRetry` (Phase 10 T-10-07-02 guarantees preserved). Zap fields: `site_id`, `snapshot_id`, `firewall_id`, `count` — no payload body, no `Authorization` header. |
| T-11-05-02 | Denial of Service | push client fails to bound `raw_blob` decode | mitigate | `raw_blob` and `Object.value` are typed as `json.RawMessage` not `map[string]any` — defers parsing inside the agent so the agent never allocates an unbounded `interface{}` tree for a hostile vendor response. Pattern preserved end-to-end from collector through push client to backend Pydantic. |
| T-11-05-03 | Denial of Service | unbounded retry loop on firewall pushes | mitigate | Same `postWithRetry` (3-attempt cap, per-request 15s timeout, ctx propagation) as Phase 10 T-10-07-05. Retry contract is locked; per-collector retry logic is forbidden (RESEARCH Anti-Patterns). |
| T-11-07-01 | Denial of Service | firewall goroutine pile-up if pull duration exceeds 1h tick | accept | 1h cadence vs. observed sub-minute pull duration makes pile-up implausible at v1.1 scale. Per-device single-flight is a deferred enhancement (RESEARCH §"Plan Decomposition" deferred item). |
| T-11-07-02 | Denial of Service | shutdown signal with firewall pull in flight blocks process exit | mitigate | Same `sync.WaitGroup` drain pattern as Phase 10 T-10-03-03. The 4th-ticker goroutine is `wg.Add(1) / defer wg.Done()`-guarded. `TestRunDaemon_FirewallTick` regression-tests this with a 2s timeout. |
| T-11-12-01 | Tampering | dispatcher mints multiple `snapshot_id`s and breaks D-08 parent idempotency | mitigate | `collectAndPushFirewall` mints a single `uuid.NewString()` per device per tick BEFORE any push call; the same `SnapshotID` is threaded through `FirewallRulesPayload`, `FirewallNATPayload`, and `FirewallObjectsPayload`. `TestRunDaemon_FirewallTick` asserts `require.Equal` on `SnapshotID` across all three payloads — the lock is structural, not comment-based. |
| T-11-12-02 | Information Disclosure | dispatcher log surface contains credentials | mitigate | Pattern G — dispatcher log fields restricted to `device`, `protocol`, `snapshot_id`, and per-payload counts; zero `user`/`pass`/`token` references. Verified via test grep of captured log bytes. |
| T-11-12-03 | Tampering | dispatcher applies wrong collector to a device protocol | mitigate | `firewallCollectorFor(dev)` is a closed protocol switch: `asa-rest`, `asa-ssh`, `fmc`, `checkpoint`, `checkpoint-import`. Non-firewall protocols return `nil` and are silently skipped (handled by `collectAndPushRoutes` on the routes ticker). `config.Validate` (T-11-06-01) rejects unknown protocols at startup so the dispatcher never sees an invalid protocol value at runtime. |
| T-11-12-04 | Denial of Service | dispatcher's per-call `http.Client` accumulates Keep-Alive sockets | accept | Per-call `http.Client{Timeout: 60s}` keeps the dispatcher stateless and trivially safe to invoke from the ticker goroutine. Connection-pool savings at the 1h ticker cadence are negligible (a handful of TLS handshakes per hour). Per-call also means a stuck Keep-Alive connection cannot poison subsequent device pulls. |

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
| T-11-06-01 | Tampering | operator misconfigures `protocol:` in `agent.yaml` (e.g. typo, vendor confusion) | mitigate | Extended validation switch in `agent/internal/config/config.go` accepts only the 8 known protocol consts (`netconf`, `ssh`, `config-import`, `asa-rest`, `asa-ssh`, `fmc`, `checkpoint`, `checkpoint-import`); the `default` branch returns `device[%d]: invalid protocol: %s` at config-load time so the agent exits before any goroutine starts. |
| T-11-06-02 | Information Disclosure | crafted `config_file` path in `checkpoint-import` device causes path traversal | accept | Operator-controlled config; same acceptance posture as Phase 10 `ProtocolConfigImport` (T-10-05-05). `chmod 600` on `agent.yaml` is the trust boundary that limits who can specify the path. |
| T-11-06-03 | Tampering | `checkpoint-import` declared without `config_file` | mitigate | Validation extends the existing `config-import` guard: `if (d.Protocol == ProtocolConfigImport || d.Protocol == ProtocolCheckpointImport) && d.ConfigFile == ""` returns `device[%d]: config_file required when protocol=%s`. Same error format as Phase 10 for grep-stability. |
| T-11-06-04 | Information Disclosure | firewall mgmt credentials in `agent.yaml` committed by mistake | mitigate | Same control as T-10-01-02 / T-10-03-01 — `agent/.gitignore` contains `/agent.yaml`. The Phase 11 protocol expansion does not add new fields to the `Device` struct (CONTEXT D-16), so no new field is at risk of escape via copy-paste of an example. |

---

## Phase 11 — Firewall Management Credential Storage

Phase 11 firewall management credentials (ASA REST API users, ASA SSH
service accounts, FMC API users, Checkpoint Management API users) are
stored in the **same model as Phase 10 device credentials** (D-05 in
Phase 10 CONTEXT, D-17 in Phase 11 CONTEXT): plaintext in `agent.yaml`,
`chmod 600`, never transmitted to SaaS. The protocol expansion (D-16)
adds new values to the existing `protocol:` field — it does **not**
add new fields to the `Device` struct. The trust boundary is identical
to Phase 10's: filesystem permissions (T-10-03-01 / T-11-06-04) bound
who can read firewall mgmt credentials on the agent host.

The five specific guarantees an enterprise reviewer should be able to
audit (from CONTEXT.md `<specifics>` extension checklist):

1. **Firewall mgmt credentials never leave the agent host.** Same
   posture as Phase 10 D-05; the same threat ID T-10-03-01 applies.
   The agent never copies firewall mgmt credentials out of process
   memory; they are read once at startup, retained in
   `config.Device.Password`, and re-presented to the vendor API on
   each pull via the standard auth method for that protocol
   (HTTP Basic for ASA REST / FMC, SSH password for ASA SSH,
   JSON body for Checkpoint `/web_api/login`).
2. **Only rule-base + NAT + object metadata is transmitted to SaaS.**
   Never live traffic, never password material, never the Checkpoint
   SID, never the ASA `X-Auth-Token`, never the FMC
   `X-auth-access-token`. The push payload structures
   (`agent/internal/push/types.go` — `FirewallRulesPayload`,
   `FirewallNATPayload`, `FirewallObjectsPayload`) contain no
   credential field. There is no path in the codebase from
   `config.Device.{Username,Password}` to the HTTP request body of any
   firewall push endpoint.
3. **Transmission is TLS-encrypted via the existing push client.**
   The three new push methods (`PushFirewallRules`, `PushFirewallNAT`,
   `PushFirewallObjects`) reuse the Phase 10 `push.Client` verbatim
   (T-10-02-01 / T-10-07-01 mitigations preserved): Bearer-token auth
   over HTTPS to the configured `backend_url`, certificate chain
   validated against the host trust store, retry-twice-then-drop
   semantics (D-19).
4. **Site token is revocable per-site.** Revoking the site token via
   the backend admin endpoint (or by deleting the `dc_sites` row)
   kills all five ingest paths atomically: routes (Phase 10), flows
   (Phase 10), firewall-rules, firewall-nat, and firewall-objects.
   No per-protocol revocation is required — the site token is the
   single revocation lever.
5. **Login-per-pull for Checkpoint means no SID at rest.** D-14 fixes
   the Checkpoint Management API session lifecycle at login → fetch →
   logout per hourly pull. The SID lifetime is bounded to
   seconds-to-minutes; the SID is never written to disk, never
   logged (Pattern G; T-11-11-01), never returned in any push payload.
   If logout fails (T-11-11-06) the SID still expires server-side via
   the operator-configured `session-timeout`. There is no "SID
   refresh" code path — the next pull starts with a fresh login.

Operators are expected to use **read-only** firewall mgmt accounts.
The agent never issues write operations to ASA / FMC / Checkpoint —
all four collectors execute only `show` / GET commands. This guarantee
is mechanically enforced: each collector's command list is hardcoded
in source:

- `agent/internal/asa/ssh.go` — issues only `terminal pager 0` and
  `show running-config`; no `configure terminal`, no `write memory`.
- `agent/internal/asa/rest.go` — issues only `POST /api/tokenservices`
  (auth), GET on `/api/objects/networkobjects` / `/api/access/in/.../rules`
  / `/api/nat`, and `DELETE /api/tokenservices/<token>` (cleanup of
  the agent's own token). No `POST` / `PATCH` / `PUT` to any
  configuration endpoint.
- `agent/internal/fmc/client.go` — issues only
  `POST /api/fmc_platform/v1/auth/generatetoken` and
  `/api/fmc_platform/v1/auth/refreshtoken` (auth), and GET on the
  `accesspolicies` / `natpolicies` / `object` endpoints. No
  configuration-write paths.
- `agent/internal/checkpoint/live.go` — issues only `POST /web_api/login`,
  `POST /web_api/show-access-rulebase` / `show-nat-rulebase` /
  `show-objects` (all are read-side `show-*` APIs in Checkpoint's
  taxonomy), and `POST /web_api/logout`. No `add-*` / `set-*` /
  `delete-*` / `publish` calls.

Reviewers can grep the four collector sources for any `POST`/`PATCH`/`PUT`/`DELETE`
beyond the auth and `show-*`/`logout` paths above; an empty grep is
the structural proof of the read-only posture.

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
6. **ASA / FMC / Checkpoint management-plane MITM (T-11-08-01,
   T-11-09-01, T-11-10-03, T-11-11-03)** — same posture as L-1; see
   [known-limitations.md](./known-limitations.md). TLS validation is
   enabled by default for the three HTTPS collectors; ASA SSH inherits
   the Phase 10 `InsecureIgnoreHostKey` acceptance.
7. **Crafted rule lines / import files (T-11-09-04, T-11-11-04)** —
   `raw_blob` preserves the original vendor envelope; misclassification
   surface is bounded by parser specificity. Phase 12 path-correlation
   will detect rules that contradict observed traffic.
8. **Best-effort ASA `deleteToken` cleanup (T-11-08-05)** — bounded by
   ASA's 30-minute server-side token expiry.
9. **Best-effort Checkpoint `logout` (T-11-11-06)** — bounded by the
   `session-timeout: 3600` the agent sets at login.
10. **Single FMC domain (T-11-10-05 partial residual)** — Phase 11
    scopes to the auth-response `DOMAIN_UUID`; multi-domain support is
    deferred — see [known-limitations.md](./known-limitations.md) L-11-04.

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
