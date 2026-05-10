---
phase: 10-dc-agent-core
verified: 2026-05-10T11:30:00Z
status: passed
score: 9/9 must-haves verified
verifier: gsd-verifier
---

# Phase 10: DC Agent Core — Verification Report

**Phase Goal:** Go DC Agent scaffolded, NETCONF/SSH + NetFlow + encrypted push working, CAB packet ready.
**Verifier method:** Goal-backward — derive truth from DCA-01..09 and ROADMAP success criteria, then locate code evidence with line numbers. SUMMARY.md claims ignored unless corroborated by code.

## Requirement-by-Requirement Verdict

| ID     | Requirement | SUMMARY claim | Code evidence (file:line) | Verdict |
|--------|-------------|---------------|---------------------------|---------|
| DCA-01 | Go scaffold, cobra CLI, daemon, single binary | scaffolded in 10-01/10-03 | `agent/go.mod`, `agent/cmd/infracanvas-agent/main.go:166` (cobra root), `:174` (`run`), `:214` (`version`), `:230-269` (daemon select loop with ctx + WaitGroup) | ✅ PASS |
| DCA-02 | Cisco NETCONF/RESTCONF for IOS-XE | netconf collector, subtree filter | `agent/internal/netconf/collector.go:26-35` (subtree filter — RESEARCH Pitfall 1), `:63-78` (`GetRoutes`), `:121-143` (production `DefaultDialer` wraps nemith.io/netconf+SSH), `:154-168` (rpc.SubtreeFilter wiring) | ✅ PASS |
| DCA-03 | SSH CLI fallback (`show ip route`) | PTY + length 0 + parser | `agent/internal/ssh/collector.go:38-53` (`GetRoutes` runs `show ip route`), `:80-129` (PTY, terminal length 0, payload via stdin — RESEARCH Pitfall 2), `agent/internal/ssh/parser.go:51-90` (`ParseShowIPRoute` regex parser) | ✅ PASS |
| DCA-04 | NetFlow v9/IPFIX UDP collector via goflow2/v2 | listener + ring buffer | `agent/internal/netflow/listener.go:56-113` (UDP:2055 `Run`, 500ms read deadline for ctx-cancel, decode-error continue), `:149-177` (production `newGoflow2Decode` using nfdecoders.CreateTemplateSystem + DecodeMessageVersion), `agent/internal/netflow/buffer.go:24-83` (ring buffer with mutex, circular overwrite, `Drain` resets) | ✅ PASS |
| DCA-05 | Encrypted API push, site-token auth | Bearer auth + retry-twice-then-drop, backend `dc_sites` + `/v1/sites` | Agent: `agent/internal/push/client.go:84-104` (`PushRoutes`/`PushFlows`), `:108-144` (3-attempt retry, 4xx no-retry, drop-after-3 logged), `:155` (`Authorization: Bearer`). Backend: `backend/app/routes/agent.py:41-83` (`POST /v1/sites` owner-gated, returns plaintext token once, stores SHA-256), `:86-113` (push handlers with `require_site_token`), `backend/app/auth/site_token.py:38` (`require_site_token` dep), `:64` (sha256 lookup hash). Migration: `backend/migrations/versions/20260507_010_dc_sites.py` (95 lines). Wired in `backend/app/main.py:20,49` | ✅ PASS |
| DCA-06 | Daemon timing 5min/1min/30s | tickers locked | `agent/cmd/infracanvas-agent/main.go:44-57` (`Intervals` struct, `defaultIntervals` returns `5*time.Minute`/`1*time.Minute`/`30*time.Second`), `:243-268` (three `time.Ticker`s in select loop, deferred `.Stop()`); `TestTickerIntervals` at `main_test.go:62` regression-locks the contract | ✅ PASS |
| DCA-07 | Config-import fallback (no network) | `LoadConfigImport` + protocol routing | `agent/internal/config/import.go:34-54` (`LoadConfigImport` reads YAML, returns `[]netconf.RouteRecord`), `agent/internal/config/config.go:65-76` (validates `config-import` requires `config_file`), `agent/cmd/infracanvas-agent/main.go:87-90` (`collectorFor` routes `ProtocolConfigImport` to `LoadConfigImport`); `TestCollectAndPushRoutes_ConfigImport` at `main_test.go:111` exercises the wired path end-to-end with a fake pusher (no network) | ✅ PASS |
| DCA-08 | Cross-compiled binaries + GHA release | linux/amd64 + darwin/arm64 matrix on `v*` tag | `.github/workflows/release.yml:63-121` (`build-agent` job: matrix linux/amd64 + darwin/arm64, `go-version: '1.25'`, `CGO_ENABLED: 0`, `-ldflags="-s -w -X main.version=..."`, smoke-test `version` subcommand on linux), `:196` (release job depends on `build-agent`), `:230-231` (binaries attached to GitHub release). Note: Task 3 (push test tag to verify) deferred per user. | ✅ PASS WITH FLAG (deferred dry-run) |
| DCA-09 | Enterprise CAB packet | architecture, dataflow, threat model, SBOM, runbook | `agent/docs/cab/architecture.md` (119 L), `dataflow.md` (107 L), `threat-model.md` (162 L), `known-limitations.md` (201 L), `operator-runbook.md` (259 L), `sbom.cyclonedx.json` (9670 B, valid CycloneDX 1.6 schema), `README.md` (70 L index) | ✅ PASS |

**Score:** 9/9 DCA requirements have wired, substantive evidence in the codebase.

## ROADMAP Success Criteria

| # | Criterion | Verdict | Evidence |
|---|-----------|---------|----------|
| 1 | Single binary on linux-amd64 + darwin-arm64 | ✅ | release.yml:63-121 matrix |
| 2 | Routes via NETCONF, SSH fallback verified | ⚠️ TEST-ONLY | netconf+ssh collectors fully tested with mock Dialers; production `DefaultDialer` paths (`collector.go:121-143`, `ssh/collector.go:57-74`) not exercised against real devices in CI — see "Top risks" below |
| 3 | NetFlow on UDP 2055 persists records | ✅ | `listener.go:19` (`DefaultUDPAddr=":2055"`), buffer holds 100k records (`main.go:194`) |
| 4 | Encrypted push authenticates and stores | ✅ | client.go uses HTTPS (URL from cfg), Bearer header, backend validates SHA-256 lookup hash; payload shape verified by `TestPushRoutes_JSONShape` (push/client_test.go:188) |
| 5 | All three timings observed | ✅ | `main_test.go:62 TestTickerIntervals` |
| 6 | CAB packet complete | ✅ | All 6 docs + SBOM present |

## Cross-Cutting Checks

| Check | Result |
|-------|--------|
| `go build ./...` clean | ✅ no output |
| `go vet ./...` clean | ✅ no output |
| `go test ./... -race -count=1 -timeout 120s` | ✅ All 6 packages PASS (cmd 2.2s, config 1.6s, netconf 3.7s, netflow 3.0s, push 7.0s, ssh 5.4s) |
| TODO/FIXME/HACK in production code | ✅ Zero matches across `agent/**/*.go` (excluding tests) |
| Backend agent integration TODO scan | ✅ Zero matches in `app/routes/agent.py`, `app/auth/site_token.py`, `app/schemas/agent.py` |
| `t.Skip` audit | ⚠️ One: `internal/push/client_test.go:151` — gated by `testing.Short()` only; runs in normal `go test` (the 7.0s push runtime confirms it executes). Intentional, not a leftover skip. |
| Test wiring of major contracts | ✅ ParseShowIPRoute (7 tests), netconf collector (5+1), netflow listener (4+template/decode), buffer (5), push client (10), config (12), main daemon/wiring (8) |

## Anti-Pattern Scan: Stubbed Network, Unverified Production Path

| Site | Production type | Coverage |
|------|-----------------|----------|
| `netconf.DefaultDialer`/`nemithSessionAdapter` (`collector.go:121-172`) | Real SSH+nemith dial | Zero direct tests; only `Collector.GetRoutes` exercised via fake Dialer (`fakeSession` 12 occurrences in `collector_test.go`) |
| `ssh.DefaultDialer`/`interactiveSession` (`collector.go:57-131`) | Real SSH+PTY+stdin payload | Zero direct tests; only fake Dialer (`fakeSession` 11 occurrences) |
| `newGoflow2Decode` (`listener.go:149-177`) | Live decoder over template cache | ✅ Covered by `TestGoflow2Decode` (listener_test.go:160) using golden NetFlow v9 testdata |
| `push.Client.doPost` (`client.go:150-168`) | Real http.Client | ✅ Covered by `httptest.NewServer` (full transport stack, only DNS skipped) |

The two NETCONF/SSH production dialers are the only real "test stubs production network call but production path unverified" sites in Phase 10. They fall outside the unit-test scope but are explicitly called out in `agent/docs/cab/known-limitations.md` and `operator-runbook.md` (259 lines) — operator runbook is the human contract for first-device verification.

## Top 3 Risks for First-Customer Deployment

1. **Production NETCONF/SSH dial paths are untested in CI.** `nemithSessionAdapter.GetSubtree` (collector.go:154-168) and `interactiveSession.Run` (ssh/collector.go:84-129) only execute against real Cisco hardware. The runbook covers this, but the first customer onboarding will be the first integration test. Mitigation: run a guided session against the customer's lab device before pushing to prod, capture wire-level XML/PTY transcripts, regression-lock as `testdata`.
2. **`HostKeyCallback: ssh.InsecureIgnoreHostKey()` on both NETCONF and SSH collectors** (`netconf/collector.go:129`, `ssh/collector.go:65`). MITM-vulnerable on first connect. CAB packet documents this as a known limitation but enterprise customers may flag it during their security review. Mitigation queued for enterprise tier per known-limitations.md.
3. **GHA `build-agent` matrix tag-trigger never dry-run.** Plan 10-08 Task 3 (push a test tag to confirm artifacts upload) was deferred. Build steps are syntactically valid and `go-version: '1.25'` is current, but the first real `v*` tag will be the first end-to-end run. Mitigation: when cutting v0.X.Y, watch the `build-agent` job in real time and be prepared to `gh release delete` if artifacts are malformed.

## Verdict

**PHASE 10: PASS WITH FLAGS**

All 9 DCA requirements have wired, substantive code evidence — not stubs. Race detector clean, no production TODOs, backend endpoints wired into FastAPI app, GHA matrix configured. The two flags (untested production dialers, unverified GHA tag dry-run) are known and deferred-by-design rather than verification gaps. Phase 11 BGP collection slot is intentionally a no-op (`main.go:132-134`) — `bgp_tick_noop_phase10` is a hand-off, not a stub.

---

_Verified: 2026-05-10T11:30:00Z_
_Verifier: Claude (gsd-verifier, goal-backward stance)_
