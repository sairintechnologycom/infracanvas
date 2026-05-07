---
phase: 10
plan: "03"
subsystem: dc-agent-core
tags: [go, cobra, daemon, config, tickers, graceful-shutdown, tdd]
dependency_graph:
  requires: ["10-01"]
  provides: [infracanvas-agent-binary, config-loader, daemon-harness, collector-stubs]
  affects: ["10-04", "10-05", "10-06", "10-07"]
tech_stack:
  added:
    - "github.com/spf13/cobra v1.10.2 — CLI root + run + version subcommands"
    - "go.uber.org/zap v1.28.0 — structured production logging"
    - "gopkg.in/yaml.v3 v3.0.1 — agent.yaml parsing"
    - "github.com/stretchr/testify v1.11.1 — require/assert in Go tests"
  patterns:
    - "signal.NotifyContext(SIGINT, SIGTERM) for graceful daemon shutdown"
    - "sync.WaitGroup drain before returning nil from daemon loop"
    - "Intervals struct as testable DCA-06 timing contract factory"
    - "TDD RED→GREEN — 2 RED commits + 2 GREEN commits"
key_files:
  created:
    - "agent/internal/config/config.go — Config + Device structs, Load(path), validate()"
    - "agent/cmd/infracanvas-agent/main.go — newRootCmd, runDaemonWithIntervals, defaultIntervals, collector stubs"
    - "agent/agent.yaml.example — documented schema with chmod 600 instruction"
  modified:
    - "agent/internal/config/config_test.go — 7 tests GREEN (was 2 t.Skip stubs)"
    - "agent/cmd/infracanvas-agent/main_test.go — 4 tests GREEN (was 2 t.Skip stubs)"
decisions:
  - "runDaemonWithIntervals factored out of the cobra RunE closure so tests can drive it directly without signal handling — divergence from RESEARCH Pattern 1 which called runDaemon from cobra directly"
  - "Intervals struct exported so downstream plans (10-04/05/06/07) can inject short intervals in their tests without redefining the type"
  - "Collector stubs accept _ context.Context + _ *config.Config to keep them valid no-ops while avoiding unused-variable errors"
  - "var version = 'dev' at package level enables -ldflags=-X main.version=... injection at build time per D-02"
metrics:
  duration: "5m"
  completed_date: "2026-05-07"
  tasks_completed: 2
  tasks_total: 2
  files_created: 3
  files_modified: 2
  tests_green: 11
  commits: 2
---

# Phase 10 Plan 03: Cobra CLI + Config Loader + Daemon Harness Summary

Go agent daemon wired end-to-end: cobra scaffold (root + run + version), agent.yaml config reader with validation, and three-ticker daemon loop with graceful WaitGroup shutdown — all 11 tests GREEN, binary builds and prints version via -ldflags.

## What Was Built

### Locked Intervals Contract (DCA-06)

The `Intervals` struct locks the three collection cadences. Plans 10-04/05/06/07 MUST NOT change these values:

| Ticker | Interval | Test that enforces it |
|--------|----------|----------------------|
| Routes | 5 × time.Minute | `TestTickerIntervals` — `require.Equal(t, 5*time.Minute, iv.Routes)` |
| BGP | 1 × time.Minute | `TestTickerIntervals` — `require.Equal(t, 1*time.Minute, iv.BGP)` |
| NetFlow flush | 30 × time.Second | `TestTickerIntervals` — `require.Equal(t, 30*time.Second, iv.Flow)` |

### Collector Stub Function Signatures

Plans 10-04/05/06/07 replace these stubs in `agent/cmd/infracanvas-agent/main.go`. The signatures are locked — the daemon's goroutine dispatch (`go func() { defer wg.Done(); collectAndPushRoutes(ctx, cfg, log) }()`) must not change.

```go
// Plan 10-04 (NETCONF collector) replaces this:
func collectAndPushRoutes(ctx context.Context, cfg *config.Config, log *zap.Logger)

// Plan 10-05 (SSH + config-import) replaces this:
// (BGP collection deferred to Phase 11 per RESEARCH.md — stub remains for now)
func collectAndPushBGP(ctx context.Context, cfg *config.Config, log *zap.Logger)

// Plan 10-06 (NetFlow) replaces this:
func flushFlowBuffer(ctx context.Context, cfg *config.Config, log *zap.Logger)
```

### Cobra Root Command Shape

```
infracanvas-agent
├── run [--config PATH]    # default ./agent.yaml
└── version                # prints var version (default "dev")
```

- `--config` flag defaults to `./agent.yaml`; fallback `/etc/infracanvas/agent.yaml` is documented in the flag description (multi-path search is a plan 10-04+ enhancement)
- `SilenceErrors: true` + `SilenceUsage: true` on root — errors propagate via `RunE` return value, not cobra's built-in printing
- `version` variable injected at build: `go build -ldflags="-X main.version=$(git describe --tags)" ./cmd/infracanvas-agent`

### Config Validation Rules (locked)

`config.Load(path)` enforces:
1. `site_token` non-empty (required)
2. `backend_url` non-empty (required)
3. Each device `protocol` must be `netconf`, `ssh`, or `config-import`
4. `config-import` devices must have non-empty `config_file`
5. Non-`config-import` devices must have non-empty `host`

## Divergence from RESEARCH Pattern 1

RESEARCH.md Pattern 1 shows `runDaemon` called directly from cobra's `RunE` field. This plan moves the ticker loop body into a separate `runDaemonWithIntervals(ctx, cfg, iv, log)` function for testability:

- **Why:** `TestDaemonStartStop` needs to drive the daemon with short tick intervals (50ms) without triggering real SIGINT. Factoring it out avoids spawning signal handlers in tests.
- **Impact:** All downstream plans should call `runDaemonWithIntervals` if they need to test the daemon loop; cobra's `RunE` wires `defaultIntervals()` for production.

## Test Coverage

| Package | Tests | Result |
|---------|-------|--------|
| `agent/internal/config` | 7 (TestConfigLoad, TestConfigLoadMissingSiteToken, TestConfigLoadMissingBackendURL, TestConfigLoadInvalidProtocol, TestConfigLoadConfigImportRequiresFile, TestConfigLoadNonexistentFile, TestConfigImport) | GREEN |
| `agent/cmd/infracanvas-agent` | 4 (TestDaemonStartStop, TestTickerIntervals, TestVersionCommand, TestRunRequiresConfig) | GREEN |
| All packages (`-race`) | 6 packages | GREEN |

## Deviations from Plan

None — plan executed exactly as written. The only minor note: `go mod tidy` needed two rounds (one for `testify` in the config package, one after wiring `cobra` and `zap` into `main.go`) because the initial `go.mod` from Plan 10-01 had the dependencies listed but `go.sum` entries were missing for test imports. This is normal for a greenfield Go module and not a deviation.

## Threat Mitigations Applied

| Threat | Mitigation |
|--------|------------|
| T-10-03-01: agent.yaml committed by mistake | `agent.yaml.example` uses `REPLACE_ME` placeholder; `chmod 600` instruction in file header; agent/.gitignore (from Plan 10-01) excludes `agent.yaml` |
| T-10-03-02: YAML billion-laughs | gopkg.in/yaml.v3 v3.0.1 has built-in alias depth limit; operator-authored config files |
| T-10-03-03: runaway tick goroutines | `sync.WaitGroup` in `runDaemonWithIntervals` gates shutdown — all in-flight collector goroutines drain before returning nil |
| T-10-03-04: env var override of version | `version` is build-time -ldflags injection only; no runtime override path |

## Known Stubs

Three collector functions in `agent/cmd/infracanvas-agent/main.go` are no-ops:
- `collectAndPushRoutes` — stub; plan 10-04 replaces with NETCONF/SSH collection
- `collectAndPushBGP` — stub; BGP deferred to Phase 11 per RESEARCH.md
- `flushFlowBuffer` — stub; plan 10-06 replaces with NetFlow ring buffer flush

These stubs are intentional design for this plan — the daemon harness is the deliverable. The stubs log at DEBUG level only and have no observable side effects.

## Self-Check

### Files Exist
- `agent/internal/config/config.go` — FOUND
- `agent/cmd/infracanvas-agent/main.go` — FOUND
- `agent/agent.yaml.example` — FOUND
- `agent/internal/config/config_test.go` — FOUND
- `agent/cmd/infracanvas-agent/main_test.go` — FOUND

### Commits Exist
- dd1f683 (Task 1: config loader + agent.yaml.example) — FOUND
- e598a44 (Task 2: cobra CLI + daemon) — FOUND

## Self-Check: PASSED
