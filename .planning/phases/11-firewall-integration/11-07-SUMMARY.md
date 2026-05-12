---
phase: 11-firewall-integration
plan: 07
subsystem: agent/cmd/infracanvas-agent
tags: [agent, ticker, scaffold, stub-first, firewall, phase-11, wave-2, d-02, d-03]
requires:
  - phase-11-plan-01-summary  # Wave 0 RED scaffold (TestDefaultIntervals extended; TestRunDaemon_FirewallTick t.Skip)
  - phase-11-plan-05-summary  # push.Client.PushFirewallRules/NAT/Objects (3 methods Pusher interface now requires)
  - phase-11-plan-06-summary  # 5 firewall protocol consts (consumed by Plan 11-12's collectAndPushFirewall body)
  - phase-10-plan-07-summary  # collectAndPushBGP stub-first precedent + Phase 10 ticker drain pattern
provides:
  - intervals/firewall-1h        # Intervals.Firewall = 1 * time.Hour (D-02)
  - pusher/firewall-3-methods    # Pusher interface extended with 3 firewall push methods
  - ticker/firewall-4th-case     # run() select-loop has 4th case for fwT.C with same wg.Add/wg.Done drain
  - collector-stub/firewall      # collectAndPushFirewall(ctx, cfg, pusher, log) — signature locked for Plan 11-12 fill-in
affects:
  - plan-11-12/checkpoint-import-loader  # Wave 4 will fill in collectAndPushFirewall body in-place
  - plan-11-08/asa-rest-collector        # Wave 3 collectors plug into the 4th ticker
  - plan-11-09/asa-ssh-collector         # Wave 3 collectors plug into the 4th ticker
  - plan-11-10/fmc-collector             # Wave 3 collectors plug into the 4th ticker
  - plan-11-11/checkpoint-live-collector # Wave 3 collectors plug into the 4th ticker
tech-stack:
  added: []  # zero new dependencies; reuses Phase 10 ticker + Pattern G logging
  patterns:
    - "Phase 10 collectAndPushBGP stub-first precedent (log.Debug noop → real collector lands in a downstream plan)"
    - "Same wg.Add/wg.Done shutdown-drain pattern as routes/bgp/flow cases (D-03)"
    - "Pusher interface widening — push.Client (Plan 11-05) already implements all 5 methods; fakePusher extended in same commit to keep tests compiling"
    - "TODO(plan 11-12) marker — explicit handoff to Wave 4 in the code"
    - "Hermetic test wiring — TestRunDaemon_FirewallTick uses zero-device cfg + 10ms ticker; no network"
key-files:
  created: []
  modified:
    - agent/cmd/infracanvas-agent/main.go
    - agent/cmd/infracanvas-agent/main_test.go
decisions:
  - "Stub-first pattern mirrors collectAndPushBGP from Phase 10 plan 10-07: ship the 4th ticker + the call site + a no-op stub, defer the real body to Plan 11-12 (Wave 4). Lets Wave 3 collector plans (11-08/09/10/11) land in parallel against a stable ticker scaffold."
  - "fakePusher in main_test.go gained a sync.Mutex (not present in Phase 10) — required because Pusher methods are now called from multiple goroutines under -race (the daemon's 4 goroutines may race on shared slices/counters). Phase 10 was already racy but masked because PushFlows ran inside a single 30s-ticker goroutine and PushRoutes inside a single 5min-ticker; -race didn't fire because tick intervals never overlapped in test. Adding the mutex now is correctness-required."
  - "TestRunDaemon_FirewallTick asserts shutdown drain only (not pusher.firewallRulesCount > 0) because the stub body never calls the pusher. The fakePusher counter fields exist already so Plan 11-12 can tighten this with a 1-line require.Greater() change. This matches the plan's <behavior>: 'Stub does not call pusher; the assertion is no panic + shutdown drain succeeded'."
  - "TestDaemonStartStop required a fix: it sets Intervals{Routes:50ms, BGP:50ms, Flow:50ms} with Firewall=0, but time.NewTicker(0) panics. Rule 1 (bug-fix) applied — added Firewall:50ms to the literal. Without this fix, every Phase 10 daemon test would panic at startup once the 4th ticker landed. This is a direct consequence of D-03 wiring, not pre-existing tech debt."
  - "Plan's <action> step 4 referenced 'countingPusher' — the actual Phase 10 test fake is named 'fakePusher'. Adapted method names accordingly; behaviour identical (no-op + counter++). Plan instructions and code diverged on naming only; capability matches verbatim."
  - "Plan's <action> step 4 example called runDaemonWithIntervals(ctx, cfg, pusher, log, iv) — the actual Phase 10 signature is runDaemonWithIntervals(ctx, cfg, iv, log, rb, pusher). Used the actual signature; behaviour matches."
metrics:
  duration_minutes: ~3
  tasks_completed: 2
  files_created: 0
  files_modified: 2
  total_files: 2
  completed_date: "2026-05-12"
---

# Phase 11 Plan 07: Agent 4th-Ticker Scaffold Summary

**One-liner:** Extend `agent/cmd/infracanvas-agent/main.go` with the 4th firewall ticker scaffold — `Intervals.Firewall = 1h` (D-02), `Pusher` interface gains 3 firewall methods (matching `push.Client` from Plan 11-05), `run()` select-loop gains a 4th case `<-fwT.C` with the same `wg.Add/wg.Done` drain pattern as routes/bgp/flow (D-03), and a `collectAndPushFirewall` STUB function lands the call site so Plan 11-12 (Wave 4) can fill the body in-place. Stub-first pattern mirrors Phase 10's `collectAndPushBGP` precedent.

## What Was Built

### Task 1 — Intervals + Pusher widening (commit `e4d4c52`)

`agent/cmd/infracanvas-agent/main.go`:
- `Intervals` struct gains a 4th field: `Firewall time.Duration` with a `// PHASE 11 D-02 — firewall pulls every 1h` comment.
- `defaultIntervals()` returns `Firewall: 1 * time.Hour` as the 4th interval; the existing 3 cadences (Routes/BGP/Flow) are preserved verbatim.
- `Pusher` interface widened from 2 → 5 methods. The 3 new methods (`PushFirewallRules`, `PushFirewallNAT`, `PushFirewallObjects`) take the payload structs introduced by Plan 11-05's `agent/internal/push/types.go` (`FirewallRulesPayload`, `FirewallNATPayload`, `FirewallObjectsPayload`).
- A header comment on `Pusher` calls out that `push.Client` already implements all 5 methods (Plan 11-05) and `fakePusher` implements the 3 new ones as no-ops (this commit, Task 1).

`agent/cmd/infracanvas-agent/main_test.go`:
- `fakePusher` extended with: 3 new slice fields (`firewallRules`, `firewallNAT`, `firewallObjects`), 3 new counter fields (`firewallRulesCount`, `firewallNATCount`, `firewallObjectsCount`), a `sync.Mutex`, and 3 new methods (`PushFirewallRules`, `PushFirewallNAT`, `PushFirewallObjects`). Existing `PushRoutes`/`PushFlows` methods also gained the same mutex for race-safety once 4 tickers run concurrently.
- `sync` added to the import block.
- `TestDefaultIntervals` (Plan 11-01 already extended it with the 4-interval assertion) now compiles and passes — Plan 11-01's RED is now Plan 11-07's GREEN.

### Task 2 — 4th ticker + collectAndPushFirewall stub (commit `db9416e`)

`agent/cmd/infracanvas-agent/main.go`:
- `runDaemonWithIntervals` `run()` select-loop:
  - 4th ticker declared: `fwT := time.NewTicker(iv.Firewall)` with paired `defer fwT.Stop()`.
  - 4th case appended: `case <-fwT.C:` with the same `wg.Add(1) / go func() { defer wg.Done(); collectAndPushFirewall(ctx, cfg, pusher, log) }()` shape as routes/bgp/flow. The `wg.Wait()` in the `case <-ctx.Done():` branch (line ~273) drains the firewall goroutine on shutdown — no new drain code needed (D-03's "same drain pattern" is satisfied structurally).
- `collectAndPushFirewall` stub function appended after `collectAndPushBGP`:
  ```go
  func collectAndPushFirewall(ctx context.Context, cfg *config.Config, pusher Pusher, log *zap.Logger) {
      log.Debug("firewall_tick_noop_phase11_plan_07",
          zap.Int("device_count", len(cfg.Devices)))
      // TODO(plan 11-12): per-device dispatch + snapshot_id minting + 3-way push
      _ = ctx
      _ = pusher
  }
  ```
  Signature `(ctx, cfg, pusher, log)` is locked so Plan 11-12 can fill the body in-place without touching the call site. `_ = ctx; _ = pusher` silences unused-arg lint until Plan 11-12 actually uses them.

`agent/cmd/infracanvas-agent/main_test.go`:
- `TestRunDaemon_FirewallTick` unskipped. Test body: build a config with zero devices, `Intervals{Routes:1h, BGP:1h, Flow:1h, Firewall:10ms}`, launch `runDaemonWithIntervals` in a goroutine, sleep 80ms (≥ 7 firewall ticks fire), `cancel()`, assert `done` channel returns `nil` within 2s. This is the D-03 "shutdown drain" regression lock — if a future refactor breaks the drain pattern (e.g., spawns the goroutine without `wg.Add(1)`), this test will hang and fail the 2s timeout.
- `TestDaemonStartStop` (Phase 10 regression test) Rule 1 fix: the test sets `Intervals{Routes:50ms, BGP:50ms, Flow:50ms}` and relied on a 3-field struct literal. With `Firewall` added as the 4th field, the literal sets `Firewall:0`, which makes `time.NewTicker(0)` panic at line 281. Added `Firewall: 50 * time.Millisecond` to the literal to match the pattern of the other 3 fields.

## Decisions Made

Captured in frontmatter `decisions:`. Summary:

1. **Stub-first pattern** — Phase 10 plan 10-07 introduced `collectAndPushBGP` as a `log.Debug("bgp_tick_noop_phase10")` stub before the real BGP collector landed. Plan 11-07 lands `collectAndPushFirewall` the same way, with `log.Debug("firewall_tick_noop_phase11_plan_07", ...)` and an explicit `TODO(plan 11-12)` marker. Wave 3 collector plans (11-08/09/10/11) can land in parallel against this stable scaffold.

2. **fakePusher needed a mutex.** Without it, `go test -race` fires on the four-ticker daemon under contended ticks (4 goroutines may concurrently append to the same slice or increment the same counter). Phase 10 was technically already racy but masked because PushRoutes/PushFlows never ran concurrently in tests. Adding `sync.Mutex` is correctness-required now and was applied to all 5 methods, not just the 3 new ones.

3. **TestRunDaemon_FirewallTick asserts shutdown drain only.** The plan's `<behavior>` block explicitly says: "Stub does not call pusher; the assertion is 'no panic + shutdown drain succeeded'." The fakePusher counter fields exist already, so Plan 11-12 can tighten with a 1-line `require.Greater(t, pusher.firewallRulesCount, 0)`.

4. **TestDaemonStartStop required a Rule 1 fix.** Without `Firewall: 50ms`, every Phase 10 daemon test would panic at startup once the 4th ticker landed. This is a direct consequence of D-03 wiring, not pre-existing tech debt.

5. **Plan/code naming divergence absorbed.** The plan's `<action>` examples referenced `countingPusher` and a `runDaemonWithIntervals(ctx, cfg, pusher, log, iv)` signature. The actual code uses `fakePusher` and `runDaemonWithIntervals(ctx, cfg, iv, log, rb, pusher)`. Adapted to the real names and signature; behaviour is identical.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `TestDaemonStartStop` `time.NewTicker(0)` panic**
- **Found during:** Task 2, first `go test -race` run after wiring the 4th ticker.
- **Issue:** The test sets `Intervals{Routes:50ms, BGP:50ms, Flow:50ms}` — a 3-field struct literal. Adding the 4th `Firewall` field means the literal defaults `Firewall:0`. `time.NewTicker(0)` panics with `non-positive interval`.
- **Fix:** Added `Firewall: 50 * time.Millisecond` to the literal — same cadence as the other 3 tickers in the test.
- **Files modified:** `agent/cmd/infracanvas-agent/main_test.go`
- **Commit:** `db9416e` (rolled into the Task 2 commit since both changes are part of the D-03 wiring)

### Naming/Signature Adaptations (not deviations — capability matches)

- Plan's `<action>` step 4 references `countingPusher`; actual fake is `fakePusher`. Adapted.
- Plan's `<action>` step 4 example calls `runDaemonWithIntervals(ctx, cfg, pusher, log, iv)`; actual signature is `runDaemonWithIntervals(ctx, cfg, iv, log, rb, pusher)`. Adapted.

## Authentication Gates

None.

## Known Stubs

**Intentional stub — to be filled by Plan 11-12:**
- `collectAndPushFirewall` (agent/cmd/infracanvas-agent/main.go) emits a single `log.Debug` line and returns. The signature `(ctx, cfg, pusher, log)` is locked; Plan 11-12 fills the body with per-protocol dispatch (asa-rest / asa-ssh / fmc / checkpoint / checkpoint-import), UUIDv4 snapshot_id minting (RESEARCH Pattern 2), and three sequential push calls (rules/nat/objects) with the same snapshot_id. Explicit `TODO(plan 11-12)` marker in the code.

The stub is the explicit deliverable of Plan 11-07 per the plan's success criteria: *"collectAndPushFirewall stub exists; ready for Plan 11-12 to fill."*

## TDD Gate Compliance

| Gate     | Commit       | Status |
| -------- | ------------ | ------ |
| RED      | (Plan 11-01) | `TestDefaultIntervals` extended with `iv.Firewall == 1h` assertion in Plan 11-01 → failed to compile (`iv.Firewall undefined`) until Task 1 of this plan. Plan 11-01 commit IS the RED commit for Plan 11-07 Task 1. |
| GREEN    | `e4d4c52`    | Intervals.Firewall + Pusher widening lands; `TestDefaultIntervals` compiles and passes. |
| RED      | (Plan 11-01) | `TestRunDaemon_FirewallTick` stub `t.Skip(...)` in Plan 11-01 — placeholder for Plan 11-07 to unskip. The structural RED is the acceptance grep (`fwT := time.NewTicker(iv.Firewall)` count must be 1) which was 0 before Task 2. |
| GREEN    | `db9416e`    | 4th ticker + collectAndPushFirewall stub + `TestRunDaemon_FirewallTick` unskipped and passes. |
| REFACTOR | (none)       | Implementation is minimal: 4 field/method/case/stub additions; nothing to clean up. |

Both tasks committed as `feat(...)` because the Plan 11-01 scaffold tests were the RED commits; Plan 11-07 is the GREEN that satisfies them. This matches the plan's frontmatter `tdd="true"` on both tasks.

## Verification

### Automated checks performed

```bash
# Task 1 acceptance greps (main.go)
M=agent/cmd/infracanvas-agent/main.go
grep -c 'Firewall time.Duration' $M                                          # 1
grep -cE 'Firewall: 1 \* time.Hour' $M                                       # 1
grep -cE 'PushFirewallRules|PushFirewallNAT|PushFirewallObjects' $M          # 3
grep -cE 'PushRoutes|PushFlows' $M                                           # 7 (≥ 2 — Phase 10 preserved)

# Task 2 acceptance greps (main.go + main_test.go)
grep -c 'fwT := time.NewTicker(iv.Firewall)' $M                              # 1
grep -c 'defer fwT.Stop()' $M                                                # 1
grep -c 'case <-fwT.C:' $M                                                   # 1
grep -c 'collectAndPushFirewall' $M                                          # 3 (function decl + 1 call site + 1 doc-comment ref)
grep -c 'firewall_tick_noop_phase11_plan_07' $M                              # 1
grep -c 'TODO(plan 11-12)' $M                                                # 1

T=agent/cmd/infracanvas-agent/main_test.go
grep -cE 'firewallRulesCount|firewallNATCount|firewallObjectsCount' $T       # 8 (3 field decls + 3 increments + 2 comment refs)
grep -cE 'func \(f \*fakePusher\) PushFirewallRules|func \(f \*fakePusher\) PushFirewallNAT|func \(f \*fakePusher\) PushFirewallObjects' $T  # 3

# Build / vet / test
cd agent
go vet ./cmd/infracanvas-agent/... ./internal/push/... ./internal/config/... \
       ./internal/netconf/... ./internal/ssh/... ./internal/netflow/...      # exits 0
go build ./cmd/... ./internal/push/... ./internal/config/... \
         ./internal/netconf/... ./internal/ssh/... ./internal/netflow/...    # exits 0
go test -race ./cmd/infracanvas-agent/...                                    # ok 1.835s — 7 tests pass
go test -race ./cmd/infracanvas-agent/... ./internal/push/... \
        ./internal/config/... ./internal/netconf/... ./internal/ssh/... \
        ./internal/netflow/...                                                # all ok
```

All acceptance-criterion greps match expected values. All in-scope packages pass `go vet`, `go build`, and `go test -race`.

### Pre-existing failures (out of scope — Plan 11-01 RED scaffolds for downstream plans)

`go vet ./internal/asa/... ./internal/fmc/... ./internal/checkpoint/...` returns:
- `internal/checkpoint/import_test.go:30:40: undefined: Parse` (Plan 11-12 deliverable)
- `internal/fmc/client_test.go:75:7: undefined: NewClient` (Plan 11-10 deliverable)
- `internal/asa/ssh_test.go:36:7: undefined: SSHSession` (Plan 11-09 deliverable)

These are Wave 0 RED scaffolds intentionally seeded by Plan 11-01 (`tests-passing: false` in Plan 11-01's frontmatter for `internal/asa`, `internal/fmc`, `internal/checkpoint`). They will turn GREEN when Plans 11-09/10/11/12 land. Verified pre-existing by running `git stash && go vet` on the parent commit `e4d4c52`. Out of scope for Plan 11-07; no change required.

## Threat Surface Scan

No new external surface. The 4th ticker is purely internal — `time.NewTicker(iv.Firewall)` is a Go-stdlib primitive, the case `<-fwT.C` spawns a goroutine guarded by `wg.Add(1) / defer wg.Done()` (T-11-07-02 mitigation), and the stub `collectAndPushFirewall` only logs. Threat register entries from the plan's `<threat_model>`:

| Threat ID | Status |
|-----------|--------|
| T-11-07-01 (DoS — goroutine pile-up if pull duration exceeds 1h tick) | accept — 1h cadence vs sub-minute pull duration makes pile-up implausible; deferred per-device single-flight to Plan 11-12 if observed |
| T-11-07-02 (DoS — shutdown signal with firewall pull in flight) | mitigate — same `wg.Wait()` drain pattern as Phase 10; `TestRunDaemon_FirewallTick` regression-tests this with a 2s timeout |

No threat-flags introduced (no new endpoints, auth paths, file access, or schema changes).

## Forward Feed for Downstream Plans

- **Plan 11-08 (asa-rest collector)** — can land in parallel; will provide a function `asa.PullREST(ctx, host, port, user, pass) (rules, nat, objects, error)` that Plan 11-12 calls inside `collectAndPushFirewall`.
- **Plan 11-09 (asa-ssh collector)** — same shape, parses `show running-config`.
- **Plan 11-10 (fmc collector)** — same shape, FMC REST API + token refresh.
- **Plan 11-11 (checkpoint live collector)** — same shape, login-per-pull lifecycle.
- **Plan 11-12 (checkpoint-import loader + collectAndPushFirewall body)** — fills in:
  1. Per-device protocol dispatch (5 cases matching Plan 11-06's protocol consts)
  2. UUIDv4 `snapshot_id` minting per device (RESEARCH Pattern 2)
  3. Three sequential `pusher.PushFirewall*` calls with the same snapshot_id
  4. Tightens `TestRunDaemon_FirewallTick` to assert `pusher.firewallRulesCount > 0` (counter field already exists)

## Commits

| Commit    | Type | Summary                                                                                            | Files |
| --------- | ---- | -------------------------------------------------------------------------------------------------- | ----- |
| `e4d4c52` | feat | extend Intervals + Pusher with firewall (D-02) — `Intervals.Firewall=1h`, 3 firewall Pusher methods, fakePusher widening with race-safe mutex | 2     |
| `db9416e` | feat | add 4th firewall ticker + collectAndPushFirewall stub (D-03) — `fwT := time.NewTicker`, 4th select case, stub function, unskipped test, `TestDaemonStartStop` Firewall:50ms fix | 2     |

## Self-Check: PASSED

- `agent/cmd/infracanvas-agent/main.go` — modified, contains `Firewall time.Duration` + `Firewall: 1 * time.Hour` + 3 firewall Pusher methods + `fwT := time.NewTicker(iv.Firewall)` + `defer fwT.Stop()` + `case <-fwT.C:` + `collectAndPushFirewall` stub with `TODO(plan 11-12)` marker ✓
- `agent/cmd/infracanvas-agent/main_test.go` — modified, contains `sync.Mutex`-protected `fakePusher` with 3 firewall methods + counters + `TestRunDaemon_FirewallTick` unskipped + `TestDaemonStartStop` Firewall:50ms ✓
- Commit `e4d4c52` exists on `dev/local-no-auth` (Task 1) ✓
- Commit `db9416e` exists on `dev/local-no-auth` (Task 2) ✓
- `go vet ./cmd/infracanvas-agent/... ./internal/push/... ./internal/config/... ./internal/netconf/... ./internal/ssh/... ./internal/netflow/...` exits 0 ✓
- `go build ./cmd/... ./internal/{push,config,netconf,ssh,netflow}/...` exits 0 ✓
- `go test -race ./cmd/infracanvas-agent/...` exits 0 (7 tests pass including `TestDefaultIntervals` + `TestRunDaemon_FirewallTick`) ✓
- Phase 10 contracts preserved (PushRoutes/PushFlows unchanged; routes/bgp/flow ticker cases unchanged; wg.Wait drain unchanged) ✓
- Pre-existing failures in internal/asa, internal/fmc, internal/checkpoint confirmed pre-existing (verified by `git stash` test on parent commit) — out of scope for Plan 11-07 ✓

## Next Plan

Wave 2 is now complete (Plans 11-05, 11-06, 11-07 all green). Wave 3 begins: Plans **11-08** (asa-rest), **11-09** (asa-ssh), **11-10** (fmc), **11-11** (checkpoint-live) can land in parallel — they all produce the same `(rules, nat, objects, error)` collector shape and plug into the 4th ticker scaffold established by this plan. Plan **11-12** (checkpoint-import loader + `collectAndPushFirewall` body fill-in) closes the loop in Wave 4 once collectors exist.

---

*Plan: 11-07 — Agent 4th-Ticker Scaffold*
*Completed: 2026-05-12*
*Wave: 2 (alongside 11-05 ✅ and 11-06 ✅)*
*Phase 11 progress after this plan: 5/13 plans complete (11-01, 11-02, 11-05, 11-06, 11-07)*
