---
phase: 11
slug: firewall-integration
status: verified
threats_open: 0
asvs_level: 1
created: 2026-05-15
---

# Phase 11 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.
> Phase 11 — Firewall Integration spans 13 plans (11-01..11-13) and 51 STRIDE
> threats across 8 trust boundaries. Each row below was verified by grep
> evidence in the cited implementation file (mitigate) or recorded as accepted
> residual risk in the Accepted Risks Log (accept). T-11-12-01 was originally
> declared `mitigate` but downgraded to `accept` after audit found the
> per-device `ctx.WithTimeout(50min)` wrap was not implemented; rationale and
> approval recorded as AR-11-17.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| TB-1 (Network device → Agent) | Agent reaches ASA REST / ASA SSH / FMC REST / Checkpoint Mgmt API over the management VLAN | Bearer tokens, basic-auth credentials, SSH passwords, X-chkp-sid SIDs, vendor-native rule/NAT/object payloads |
| TB-2 (Agent → Cloud backend HTTPS) | Agent pushes firewall snapshot payloads via 3 endpoints with `Authorization: Bearer <site_token>` | site_token, snapshot_id, vendor blobs, normalized rule/NAT/object rows |
| TB-3 (Backend → Postgres) | FastAPI handlers write/read firewall tables under RLS `team_isolation` policies | team_id-scoped firewall_ruleset_snapshots + 3 child tables |
| TB-4 (Browser → Backend HTTPS) | Dashboard / operator reads firewall snapshots via Clerk JWT-protected read API | Clerk JWT, snapshot payloads |
| TB-5 (Operator → agent.yaml) | Operator-supplied config file is read at startup; protocol/path values cross trust boundary | Device entries, protocol enum, config_file paths |
| TB-6 (Ticker → goroutine) | Internal — 4th ticker spawns wg-guarded goroutine; bounded by wg.Wait() drain on shutdown | none (intra-process) |
| TB-7 (Operator → import file) | Agent reads checkpoint-import file from operator-controlled filesystem path | Hand-exported mgmt_cli JSON (rulebase + nat + objects siblings) |
| TB-8 (CAB document → enterprise security reviewer) | CAB packet (architecture / dataflow / threat-model / known-limitations / operator-runbook) is the trust artifact during enterprise review | Documentation describing posture, credentials, network reach |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-11-01-01 | Tampering | adversary commits malformed fixture | accept | Code review + CI test failure surface; fixtures live in repo | closed |
| T-11-01-02 | Information Disclosure | fixture contains real customer data | mitigate | Synthetic IPs (10.x / 192.168.x), synthetic hostnames; reviewer checks no real secrets — `agent/internal/{asa,fmc,checkpoint}/testdata/*` | closed |
| T-11-02-01 | DoS | unbounded `rules`/`nat_rules`/`objects` list in push body | mitigate | `Field(..., max_length=50000)` on all three list fields — `backend/app/schemas/firewall.py:79,94,109` | closed |
| T-11-02-02 | Information Disclosure | cross-team firewall data leak via missing RLS | mitigate | `ENABLE + FORCE ROW LEVEL SECURITY` + `team_isolation` policy on all 4 tables — `backend/migrations/versions/20260510_011_firewall_tables.py:88-92, 131-138, 183-190, 231-238` | closed |
| T-11-02-03 | Elevation of Privilege | future migration renames Phase 12 forward-feed columns | mitigate | Doc-comment top of migration lists locked columns — `backend/migrations/versions/20260510_011_firewall_tables.py:5-8` | closed |
| T-11-02-04 | Tampering | crafted JSONB raw_blob | accept | JSONB stored as dict after Pydantic parse; bounded by T-11-02-01 | closed |
| T-11-02-05 | DoS | snapshot storage explosion (800 GB/30d worst case) | mitigate | TTL prune task `prune_firewall_snapshots` with 14-day default — `backend/app/queue/tasks/firewall_prune.py:33-75`; FK CASCADE removes children automatically | closed |
| T-11-03-01 | Spoofing | unauthenticated POST to firewall ingest endpoint | mitigate | `Depends(require_site_token)` on all 3 handlers — `backend/app/routes/agent.py:177, 234, 283` | closed |
| T-11-03-02 | Tampering | cross-team firewall data injection via crafted body | mitigate | RLS GUC `app.current_team_id` set in handler txn — `backend/app/routes/agent.py:193, 245, 295`; RLS `WITH CHECK` on parent table rejects mismatched team_id INSERT | closed |
| T-11-03-03 | Information Disclosure | credentials accidentally logged in handler structlog | mitigate | Pattern G — `_log.info` allowlist only includes site_id, team_id, snapshot_id, firewall_id, vendor, source, count — `backend/app/routes/agent.py:218-228` | closed |
| T-11-03-04 | Repudiation | duplicate inserts from agent retries pollute history | mitigate | `on_conflict_do_nothing(index_elements=["snapshot_id"])` — `backend/app/routes/agent.py:169` | closed |
| T-11-03-05 | DoS | massive payload starving worker threads | mitigate | Inherits T-11-02-01 Pydantic max_length=50000; FastAPI returns 422 before handler executes | closed |
| T-11-04-01 | Information Disclosure | cross-team firewall data exposed via crafted site_id | mitigate | Site-membership probe first; cross-team → 404 `site_not_found_or_no_access` — `backend/app/routes/firewalls.py:111-118`; regression-tested by `test_cross_team_isolation` | closed |
| T-11-04-02 | Spoofing | unauthenticated read of firewall snapshots | mitigate | `Depends(require_role(*_READ_ROLES))` — `backend/app/routes/firewalls.py:88` with `_READ_ROLES = ("owner","admin","member","basic_member")` (line 59) | closed |
| T-11-04-03 | Information Disclosure | rule contents accidentally logged | mitigate | `_log.info` allowlist limited to team_id, site_id, snapshot_count — `backend/app/routes/firewalls.py:137-142, 207` | closed |
| T-11-04-04 | DoS | huge snapshot OOMs API server | accept | Bounded by upstream T-11-02-01 (50k rows max); read returns at most one snapshot per firewall_id; pagination deferred | closed |
| T-11-05-01 | Information Disclosure | site_token leakage in postWithRetry log fields | mitigate | Inherits Phase 10 T-10-07-02 — `postWithRetry` never adds Authorization to zap fields; response sample capped at 512 bytes — `agent/internal/push/client.go:204, 222`; no `zap.String("token"/"password"/"Authorization", ...)` calls present | closed |
| T-11-05-02 | Tampering | snapshot_id collision causes wrong-snapshot child writes | accept | UUIDv4 (2^122 random bits); backend ON CONFLICT DO NOTHING is structural fallback | closed |
| T-11-05-03 | DoS | very large payload causes agent OOM during json.Marshal | mitigate | Inherits backend Pydantic Field max_length=50000 (T-11-02-01) as wire-level cap; per-vendor collectors bound output | closed |
| T-11-06-01 | Tampering | operator misconfigures protocol → agent crashes | mitigate | Validation switch in `Validate()` returns `device[%d]: invalid protocol: %s` at config-load — `agent/internal/config/config.go:75-79` | closed |
| T-11-06-02 | Information Disclosure | crafted config_file path → path traversal | accept | Operator-controlled config; chmod 600 on agent.yaml is the trust boundary; `os.ReadFile` respects mount-namespace | closed |
| T-11-07-01 | DoS | firewall ticker fires while previous pull running → goroutine pile-up | accept | 1h cadence vs sub-minute pull duration; deferred per-device single-flight if observed | closed |
| T-11-07-02 | DoS | shutdown signal with firewall pull in flight → resource leak | mitigate | Same `wg.Add/wg.Done` + `wg.Wait()` drain as Phase 10 — `agent/cmd/infracanvas-agent/main.go:475, 488-489`; `TestRunDaemon_FirewallTick` regression-test | closed |
| T-11-08-01 | Spoofing | MITM on ASA management VLAN | accept | TLS validation on by default; `InsecureSkipVerify: false` baseline — `agent/internal/asa/rest.go:100-101` | closed |
| T-11-08-02 | Information Disclosure | username/password/X-Auth-Token leakage in logs | mitigate | Pattern G — `ErrASAAuth` sentinel returned on 401 — `agent/internal/asa/rest.go:55-59, 194, 261`; basic-auth via `req.SetBasicAuth`; no zap-field logging of tokens | closed |
| T-11-08-03 | Information Disclosure | ASA REST EOL at 9.17+ → cryptic 404s | mitigate | Package doc-comment surfaces EOL — `agent/internal/asa/rest.go:20-21`, `agent/internal/asa/types.go:19-20`; CAB known-limitations.md captures operator-facing | closed |
| T-11-08-04 | Tampering | adversary-controlled ASA returns crafted JSON | mitigate | `io.LimitReader(resp.Body, 16*1024*1024)` 16 MiB cap — `agent/internal/asa/rest.go:269`; `encoding/json.Unmarshal` returns errors cleanly | closed |
| T-11-08-05 | Repudiation | dangling token after Pull due to DELETE failure | accept | ASA expires tokens after 30 min; `deleteToken` uses fresh 5s context to survive parent cancel — `agent/internal/asa/rest.go` deleteToken | closed |
| T-11-09-01 | Spoofing | SSH MITM on ASA management | accept | InsecureIgnoreHostKey inherited from Phase 10 `xssh.DefaultDialer`; CAB-documented | closed |
| T-11-09-02 | Information Disclosure | password leak via PTY echo | mitigate | ECHO=0 set by underlying `xssh.DefaultDialer` (Phase 10 T-10-05-02 inheritance) — `agent/internal/asa/ssh.go:12-21` | closed |
| T-11-09-03 | DoS | adversarial running-config causes parser hang | mitigate | All regexes use bounded character classes, no backreferences — `agent/internal/asa/ssh_parser.go:46-83`; non-matching lines silently skipped | closed |
| T-11-09-04 | Tampering | crafted config line bypasses parser to inject false rule | accept | `raw_blob` preserves original line text; Phase 12 path-comp sees actual text — `agent/internal/asa/ssh_parser.go:133, 162, 176` | closed |
| T-11-09-05 | DoS | very large running-config (>10 MB) blows agent memory | mitigate | `scanner.Buffer(make([]byte, 0, 64*1024), 1024*1024)` caps per-line at 1 MiB — `agent/internal/asa/ssh_parser.go:142` | closed |
| T-11-10-01 | Information Disclosure | X-auth-access-token / X-auth-refresh-token leak | mitigate | Pattern G — `Client` has no `*zap.Logger` field; tokens flow only through `req.Header.Set` / `resp.Header.Get` — `agent/internal/fmc/client.go` (no `zap.String("token"/"accessToken"/"refreshToken"...)` calls) | closed |
| T-11-10-02 | DoS | infinite refresh loop on misbehaving FMC | mitigate | `const maxRefreshAttempts = 3` + refreshCount check; `ErrFMCAuth` bails — `agent/internal/fmc/client.go:85, 289`; `agent/internal/fmc/types.go:49` | closed |
| T-11-10-03 | Spoofing | MITM on FMC management network | accept | TLS to FMC; `InsecureSkipVerify: false` — `agent/internal/fmc/client.go:132` | closed |
| T-11-10-04 | Tampering | crafted FMC response causes panic in normalize | mitigate | `io.LimitReader` 16 MiB cap; defensive index checks; `maxPages = 1000` cap in `paginatedGet`; `fmt.Errorf` collector wrap | closed |
| T-11-10-05 | Information Disclosure | wrong DOMAIN_UUID across multi-tenant FMC | mitigate | `DOMAIN_UUID` sourced only from auth response header (`resp.Header.Get("DOMAIN_UUID")` line 297); collector refuses to proceed if empty (lines 175-179); no caller-overridable domain parameter — `agent/internal/fmc/client.go` | closed |
| T-11-11-01 | Information Disclosure | SID leakage in zap log fields | mitigate | Pattern G — `grep 'zap\.String\("sid"' agent/internal/checkpoint/live.go` returns zero matches; SID flows only through `X-chkp-sid` header — `agent/internal/checkpoint/live.go:264` | closed |
| T-11-11-02 | DoS | SID timeout on >50k rule layers | mitigate | `"session-timeout": 3600` passed at login — `agent/internal/checkpoint/live.go:202`; known-limitation L-N documented in CAB | closed |
| T-11-11-03 | Spoofing | Checkpoint SID hijack via MITM | mitigate | TLS to mgmt API: `MinVersion: tls.VersionTLS12, InsecureSkipVerify: false` — `agent/internal/checkpoint/live.go:133-134`; SID never written to disk (login-per-pull) | closed |
| T-11-11-04 | Tampering | crafted import file injects false rules | accept | Operator-controlled file (chmod 600 by convention); `raw_blob` preserves original | closed |
| T-11-11-05 | DoS | massive show-objects response blows agent memory | mitigate | `const maxPages = 10000` page-limit cap — `agent/internal/checkpoint/live.go:74`; per-call client 60s timeout | closed |
| T-11-11-06 | Repudiation | failed logout leaves dangling SID | accept | Best-effort logout with WARN log; SID expires after session-timeout | closed |
| T-11-12-01 | DoS | one slow device blocks the firewall ticker | accept | Disposition downgraded from `mitigate` post-audit; declared per-device `ctx.WithTimeout(50min)` wrap not implemented in `agent/cmd/infracanvas-agent/main.go:276-335`. Compensating controls: 1h ticker cadence (next pull recovers), parent ctx cancel on shutdown, `http.Client{Timeout: 60s}` socket-level cap (line 172). See AR-11-17. | closed |
| T-11-12-02 | Tampering | snapshot_id collision across devices in same tick | accept | UUIDv4 collision is statistically zero; backend ON CONFLICT DO NOTHING handles intra-tick collisions | closed |
| T-11-12-03 | Information Disclosure | snapshot_id in logs links to agent IP via correlation | accept | UUID has no PII; log retention is operator-controlled | closed |
| T-11-12-04 | DoS | partial push leaves orphaned parent snapshot row | accept | Parent row harmless (no security impact); next tick replaces; prune cleans over time | closed |
| T-11-13-01 | Repudiation | Phase 11 ships without CAB packet update → enterprise rejection | mitigate | CAB packet `agent/docs/cab/*` extended with Phase 11 rows (README, architecture, dataflow, threat-model, known-limitations, operator-runbook) — all 6 files reference Phase 11 / T-11- IDs | closed |
| T-11-13-02 | Information Disclosure | CAB packet documents non-existent credential leak vector (over-disclosure) | mitigate | Human verification gate (`autonomous: false` on Plan 11-13) per 11-13-SUMMARY; reviewed language for accuracy before phase closure | closed |
| T-11-13-03 | Tampering | Phase 10 CAB content overwritten by Phase 11 extensions | mitigate | grep checks (Task 1 acceptance criteria) verify Phase 10 row counts preserved; CAB packet retains 17 TB-1 T-10 rows + 15 TB-2 T-10 rows alongside new T-11 extensions | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Open Threats

None — T-11-12-01 resolved via disposition downgrade to `accept` (AR-11-17).

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-11-01 | T-11-01-01 | Fixtures live in-repo under code review; CI test failure surfaces any malformed fixture; no external untrusted source. | gsd-security-auditor (auto) | 2026-05-15 |
| AR-11-02 | T-11-02-04 | Pydantic parses JSONB raw_blob into a dict before storage; Postgres treats JSONB keys as data not code; dict size is bounded by T-11-02-01 list-length cap (50k items × bounded raw_blob). | gsd-security-auditor (auto) | 2026-05-15 |
| AR-11-03 | T-11-04-04 | Snapshots bounded by upstream T-11-02-01 (50k rules max per push); read returns at most one snapshot per firewall_id; pagination deferred to Phase 11+1 if dashboard requires it. | gsd-security-auditor (auto) | 2026-05-15 |
| AR-11-04 | T-11-05-02 | UUIDv4 collision probability ~5×10^-39 per pull (122 random bits). Backend `ON CONFLICT DO NOTHING` on snapshot_id provides structural fallback if collision ever occurs. | gsd-security-auditor (auto) | 2026-05-15 |
| AR-11-05 | T-11-06-02 | Same posture as Phase 10 ProtocolConfigImport — operator owns the config file; chmod 600 agent.yaml is the trust boundary; `os.ReadFile` respects mount-namespace boundaries; no privilege escalation across the agent process boundary. | gsd-security-auditor (auto) | 2026-05-15 |
| AR-11-06 | T-11-07-01 | 1h cadence vs typical sub-minute pull duration makes goroutine pile-up implausible at v1.1 scale; if customer rule bases grow >50k and pulls exceed 1h, Plan 11-12+ can add per-device single-flight. Added to deferred-items list. | gsd-security-auditor (auto) | 2026-05-15 |
| AR-11-07 | T-11-08-01 | Same posture as Phase 10 T-10-04-01 — TLS cert is operator-managed; agent runs on management VLAN; `InsecureSkipVerify: false` baseline; CAB packet documents the posture for enterprise reviewers. | gsd-security-auditor (auto) | 2026-05-15 |
| AR-11-08 | T-11-08-05 | ASA times out auth tokens after 30 min server-side anyway; `deleteToken` uses fresh 5s context to survive parent cancellation; cleanup failures are non-fatal. Logged in CAB packet. | gsd-security-auditor (auto) | 2026-05-15 |
| AR-11-09 | T-11-09-01 | Same posture as Phase 10 T-10-05-01 — `InsecureIgnoreHostKey` is the v1.1 SSH baseline; CAB packet known-limitations.md surfaces this to enterprise reviewers; ops runs on management VLAN. | gsd-security-auditor (auto) | 2026-05-15 |
| AR-11-10 | T-11-09-04 | Parser emits `raw_blob` preserving original line text; downstream Phase 12 path-computation can audit the actual config text; misclassification surface bounded by regex specificity. | gsd-security-auditor (auto) | 2026-05-15 |
| AR-11-11 | T-11-10-03 | TLS to FMC; same posture as ASA REST T-11-08-01; `InsecureSkipVerify: false`; operator-managed cert. | gsd-security-auditor (auto) | 2026-05-15 |
| AR-11-12 | T-11-11-04 | Operator-controlled file (chmod 600 by ops convention); `raw_blob` preserves original mgmt_cli JSON — downstream consumer can audit. | gsd-security-auditor (auto) | 2026-05-15 |
| AR-11-13 | T-11-11-06 | Best-effort logout with WARN log; Checkpoint expires SIDs after session-timeout (3600s passed at login) regardless of logout success. | gsd-security-auditor (auto) | 2026-05-15 |
| AR-11-14 | T-11-12-02 | UUIDv4 collision is statistically zero (2^122 random bits). Per-device minting means intra-tick collision (already non-existent) would be handled by backend `ON CONFLICT DO NOTHING`. | gsd-security-auditor (auto) | 2026-05-15 |
| AR-11-15 | T-11-12-03 | snapshot_id is a random UUID with no PII; agent IP correlation requires log retention plus log access, which is operator-controlled and within the same trust posture as the rest of the agent's operational logs. | gsd-security-auditor (auto) | 2026-05-15 |
| AR-11-16 | T-11-12-04 | Parent ruleset_snapshots row is harmless without children (no security impact — no auth/PII content); next tick replaces with full snapshot; backend TTL prune (T-11-02-05 mitigation) cleans orphaned parents within 14 days. | gsd-security-auditor (auto) | 2026-05-15 |
| AR-11-17 | T-11-12-01 | Declared `mitigate` (per-device `ctx.WithTimeout(50min)` wrap in `collectAndPushFirewall`) was not implemented. Compensating controls bound exposure to one tick window: (1) 1h ticker cadence means a hung device only blocks the dispatcher until the next tick, when the parent ctx is replaced; (2) parent ctx cancel on shutdown via existing wg.Wait() drain (T-11-07-02); (3) `http.Client{Timeout: 60s}` socket-level cap at agent/cmd/infracanvas-agent/main.go:172 prevents any single HTTP request from stalling indefinitely; (4) ASVS L1 does not require per-operation wall-clock deadlines. Per-device fan-out / single-flight deferred to a future plan if production telemetry shows slow-device blocking. Phase owner accepted residual risk for v1.1. | phase owner (Bhushan) via /gsd-secure-phase 11 prompt | 2026-05-15 |

*Accepted risks do not resurface in future audit runs.*

---

## Unregistered Flags

None. SUMMARY.md files for Plans 11-01 through 11-13 either explicitly map
every newly-introduced surface to a registered T-11- threat (e.g.,
11-07-SUMMARY "No new external surface", 11-08/09/10/11 Threat Model
Compliance tables) or attest to no new surface (11-02/03/04/05/12/13).

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-05-15 | 51 | 50 | 1 | gsd-security-auditor (Opus 4.7) |
| 2026-05-15 | 51 | 51 | 0 | /gsd-secure-phase 11 — T-11-12-01 downgraded to accept (AR-11-17) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log (17 entries)
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-05-15 — Phase 11 threat register fully closed.
T-11-12-01 disposition downgraded from `mitigate` to `accept` (AR-11-17);
remaining 50 threats verified by grep evidence (35 mitigate) or accepted with
documented rationale (16 accept).
