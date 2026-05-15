---
phase: 11-firewall-integration
plan: 12
subsystem: agent/cmd/infracanvas-agent
tags: [agent, dispatcher, wave-4, integration, d-08, research-pattern-2]
requires:
  - phase-11-plan-07-summary  # 4th ticker + Pusher interface + collectAndPushFirewall stub site
  - phase-11-plan-08-summary  # asa.NewRESTCollector + Pull signature
  - phase-11-plan-09-summary  # asa.NewSSHCollector + Pull signature (used DefaultSSHDialer added here as prereq)
  - phase-11-plan-10-summary  # fmc.NewClient + Pull signature
  - phase-11-plan-11-summary  # checkpoint.NewLiveCollector + LoadImport
provides:
  - firewall-dispatcher       # collectAndPushFirewall body — per-protocol fan-out
  - firewall-collector-fn-map # firewallCollectorFor — switch dev.Protocol → vendor puller
  - shared-snapshot-id-mint   # uuid.NewString() once per device per tick, threaded through 3 pushes
  - checkpoint-import-paths   # checkpointImportPaths — base/sibling convention
  - asa-default-ssh-dialer    # asa.DefaultSSHDialer exported helper (out-of-plan prereq, Rule 3)
affects:
  - plan-11-13  # CAB packet + operator runbook (documents the checkpoint-import path convention)
tech-stack:
  added:
    - github.com/google/uuid v1.6.0  # UUIDv4 minting per RESEARCH Pattern 2
  patterns:
    - "RESEARCH Pattern 2 — single snapshot_id minted once per device per tick, shared across the 3 push endpoints so backend ON CONFLICT DO NOTHING parent insert is idempotent regardless of arrival order"
    - "Pattern H — closures pass primitives (host/port/user/pass) to vendor Pull methods, never config.Device — preserves the no-import-cycle invariant established by Wave 3"
    - "Pattern G — log fields restricted to device/protocol/snapshot_id/counts; zero user/pass/token references"
    - "D-08 hybrid — payloads carry normalized columns + raw_blob from each vendor collector"
    - "D-15 forward-feed — snapshot_ts on every payload as RFC3339 UTC"
    - "checkpoint-import path convention: dev.ConfigFile may be `base.rulebase.json` (siblings derived by suffix trim) or `base` prefix (3 extensions appended)"
    - "Per-call http.Client (60s timeout) — production ticker is 1h so no pool-sharing benefit; keeps dispatcher stateless"
key-files:
  modified:
    - agent/cmd/infracanvas-agent/main.go      # +201/-15: collectAndPushFirewall body filled + 4 helpers + new imports
    - agent/cmd/infracanvas-agent/main_test.go # +61/-12: TestRunDaemon_FirewallTick tightened + writeCheckpointImportConfig helper + 3 fixture string consts
    - agent/go.mod                              # google/uuid v1.6.0 added; Wave 3 deps promoted to direct
    - agent/go.sum                              # google/uuid checksum entries
    - agent/internal/asa/ssh.go                 # +7 lines: DefaultSSHDialer exported helper (Rule 3 prereq deviation)
decisions:
  - "Path-convention helper checkpointImportPaths accepts both forms (operator path ending in `.rulebase.json` vs base prefix) so an operator can copy-paste a full path or a base prefix without ceremony. The plan's RESOLVE: bullet picked option (b) operator-friendly; I implemented both — a `.rulebase.json` suffix is detected and trimmed; otherwise the 3 extensions are appended to dev.ConfigFile. This is wider than the plan's single-form proposal but strictly a superset — both forms work."
  - "Per-call http.Client at 60s timeout (production ticker fires hourly). Considered sharing a single client across the dispatcher but rejected: per-call clients keep the dispatcher stateless and trivially safe to invoke from the ticker goroutine; the connection-pool savings amount to a handful of TLS handshakes per hour. Per-call also means a stuck Keep-Alive connection cannot poison subsequent device pulls."
  - "FirewallID = dev.Host directly. push/types.go field comment says 'device serial / dev.Host'; the agent has no per-device serial lookup in v1.1 (would require a separate auth dance per vendor). Host name is the operator-facing identifier and matches the backend's natural-key expectation."
  - "asa.DefaultSSHDialer added as exported helper (Rule 3 deviation — out of plan's 2-file files_modified scope). Plan 11-09 left the production defaultSSHDialer struct unexported, but the dispatcher needs a way to construct an SSH dialer from outside the asa package. The exported helper is a 1-line constructor returning the existing unexported type — minimal surface change, no behavior change. Documented as a Rule 3 prereq deviation in the chore() commit message; Plan 11-09 SUMMARY's signature convention (single-arg NewSSHCollector + SetLogger setter) is preserved."
  - "writeCheckpointImportConfig (test helper) writes minimal valid Checkpoint JSON inline rather than copying the agent/internal/checkpoint/testdata/ fixtures. Reason: test data ownership — the cmd/infracanvas-agent test should not depend on internal/checkpoint/testdata/ file layout (would couple the two packages' test fixtures). Inline JSON is 3 lines of consts at the top of main_test.go and produces exactly 1 rule + 0 NAT + 0 objects, which is enough for the dispatcher's 3 push calls to fire (parser tolerates empty rulebases on each axis)."
  - "Module-wide `go mod tidy` promoted Wave 3 transitive deps (netsampler/goflow2/v2, golang.org/x/crypto, nemith.io/netconf) from `// indirect` to direct require. These were already used by Phase 10 collectors but go.mod tracking was stale; the Wave 3 cmd/infracanvas-agent now imports the asa/fmc/checkpoint packages which transitively pull them in. Zero behavior change — just dependency-graph hygiene."
  - "checkpointImportPaths handles both `.rulebase.json` suffix and base-prefix forms. The plan called out this RESOLVE: explicitly; this implementation closes both paths. The strings.HasSuffix check is O(1); zero allocation in the suffix-trim path (TrimSuffix returns the same underlying string when the suffix matches)."
  - "TestRunDaemon_FirewallTick assertions verify shared snapshot_id across rules/NAT/objects payloads. This is the load-bearing test of RESEARCH Pattern 2 — if the dispatcher mints a new UUID per push call, the assertion fails. require.Equal on SnapshotID across the three payloads locks the contract structurally rather than via comment."
metrics:
  duration_minutes: 25
  tasks_completed: 4  # prereqs commit, RED test, GREEN impl, this SUMMARY
  files_created: 1   # this SUMMARY.md
  files_modified: 5  # main.go, main_test.go, go.mod, go.sum, asa/ssh.go
  total_files: 6
  completed_date: "2026-05-15"
---

# Phase 11 Plan 12: Firewall Dispatcher Summary

Plan 11-07's `collectAndPushFirewall` stub is now filled. The 4th-ticker entry point dispatches per-device by `dev.Protocol`, mints one UUIDv4 `snapshot_id` per device per tick (shared across the three push calls per RESEARCH Pattern 2 + D-08), and sequentially calls `PushFirewallRules` → `PushFirewallNAT` → `PushFirewallObjects` with the same envelope.

`firewallCollectorFor(dev)` maps the 5 firewall protocols to their Wave-3 vendor pullers:

| Protocol | Vendor entry point | Source label |
|----------|-------------------|--------------|
| `asa-rest` | `asa.NewRESTCollector(http.Client) + Pull` | `asa-rest` |
| `asa-ssh` | `asa.NewSSHCollector(asa.DefaultSSHDialer()) + Pull` | `asa-ssh` |
| `fmc` | `fmc.NewClient(http.Client) + Pull` | `fmc` |
| `checkpoint` | `checkpoint.NewLiveCollector(http.Client) + Pull` | `checkpoint` |
| `checkpoint-import` | `checkpoint.LoadImport(rb, nat, objs)` via `checkpointImportPaths(dev.ConfigFile)` | `checkpoint-import` |

Non-firewall protocols (`netconf`, `ssh`, `config-import`) return `nil` from `firewallCollectorFor` and are silently skipped — they're handled by `collectAndPushRoutes` on the routes ticker.

`TestRunDaemon_FirewallTick` (Plan 11-07 stub-only) is tightened from "no panic" to **structural verification of the dispatcher contract**:

- `firewallRulesCount > 0` — `PushFirewallRules` was invoked
- `firewallNATCount > 0` — `PushFirewallNAT` was invoked
- `firewallObjectsCount > 0` — `PushFirewallObjects` was invoked
- All three payloads carry the **same** `snapshot_id` (RESEARCH Pattern 2 lock)

The test exercises the `checkpoint-import` path with inline temp-dir JSON fixtures so it runs fully offline with deterministic output.

## Test results

```
go vet ./... clean
go build ./... clean
go test -race -count=1 ./... — all 9 packages GREEN
  cmd/infracanvas-agent  1.606s
  internal/asa           2.974s
  internal/checkpoint    4.121s
  internal/config        3.493s
  internal/fmc           5.901s
  internal/netconf       5.282s
  internal/netflow       4.984s
  internal/push          8.747s
  internal/ssh           5.340s
```

## Deviations

1. **Rule 3 — asa.DefaultSSHDialer exported helper.** Plan 11-12's `files_modified` declared only `main.go` + `main_test.go`, but the dispatcher needed an exported way to construct the production SSH dialer (Plan 11-09 kept `defaultSSHDialer` unexported). Added a 1-line `DefaultSSHDialer() SSHDialer` constructor in `agent/internal/asa/ssh.go` that returns the existing unexported type — zero behavior change. Committed separately in `7a94d23` (chore) for auditability.

2. **Rule 1 — checkpointImportPaths accepts both path forms.** Plan body documented a RESOLVE: bullet asking which path convention to adopt; this implementation accepts both (suffix `.rulebase.json` → siblings derived by trim; otherwise `dev.ConfigFile` treated as base prefix). Wider than the proposal but strictly a superset.

3. **Pre-emptive `go mod tidy`** promoted Wave 3 transitive deps to direct require. Bundled with the prereq commit (`7a94d23`).

## Commits

- `7a94d23` — chore(agent): Plan 11-12 dispatcher prereqs (go mod tidy + asa.DefaultSSHDialer)
- `5c8d697` — test(11-12): tighten TestRunDaemon_FirewallTick (RED — fails against the noop stub)
- `3a5486b` — feat(11-12): implement collectAndPushFirewall dispatcher (GREEN — all 9 packages pass)

## Phase 11 status after this plan

- Wave 0 ✅ • Wave 1 ✅ • Wave 2 ✅ • Wave 3 ✅ • **Wave 4 ✅**
- Wave 5 (Plan 11-13 — CAB packet extension, `autonomous: false`) remains, gated on user confirmation.
- ROADMAP success criteria 1, 2, 3, 4 are now end-to-end demonstrable: agent → 4 vendor collectors → 3 backend ingest endpoints → backend read API → operator GET returns latest-per-device firewall snapshots.
