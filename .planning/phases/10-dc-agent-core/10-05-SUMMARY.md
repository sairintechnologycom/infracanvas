---
phase: 10
plan: "05"
subsystem: dc-agent-core
tags: [go, ssh, ios-xe, config-import, tdd, dca-03, dca-07, collector]
dependency_graph:
  requires: ["10-03", "10-04"]
  provides:
    - "agent/internal/ssh/parser.go (ParseShowIPRoute IOS-XE table parser)"
    - "agent/internal/ssh/collector.go (SSH Collector + Dialer/Session + DefaultDialer + PTY+terminal-length-0)"
    - "agent/internal/ssh/parser_test.go (7 GREEN parser tests)"
    - "agent/internal/ssh/collector_test.go (5 GREEN collector tests)"
    - "agent/internal/config/import.go (LoadConfigImport YAML→[]netconf.RouteRecord)"
    - "agent/internal/config/config_test.go (5 new TestConfigImport_* tests)"
  affects:
    - "10-07 (push client — consumes []netconf.RouteRecord from all 3 collectors; main.go fans out NETCONF/SSH/config-import)"
    - "10-09 (CAB packet — documents config-import air-gapped mode + SSH PTY behavior + InsecureIgnoreHostKey)"
tech_stack:
  added:
    - "(none — gopkg.in/yaml.v3 + golang.org/x/crypto already present from 10-03/10-04)"
  patterns:
    - "Pure-function parser separate from network-bound Collector for deterministic testing"
    - "Mirror of netconf Dialer/Session interface shape — uniform test seam across collectors"
    - "PTY+`terminal length 0` payload sent BEFORE the show command (RESEARCH Pitfall 2)"
    - "Explicit configImportRoute → netconf.RouteRecord mapping — keeps netconf/types.go JSON-only"
    - "Collector.GetRoutes accepts (host, port, user, pass) primitives — avoids config↔netconf import cycle"
key_files:
  created:
    - "agent/internal/ssh/parser.go"
    - "agent/internal/ssh/parser_test.go"
    - "agent/internal/ssh/collector.go"
    - "agent/internal/ssh/collector_test.go"
    - "agent/internal/config/import.go"
  modified:
    - "agent/internal/config/config_test.go (5 new TestConfigImport_* tests)"
    - "agent/internal/netconf/collector.go (GetRoutes signature: dev config.Device → primitives)"
    - "agent/internal/netconf/collector_test.go (5 call sites updated; sample primitives instead of sampleDevice)"
    - "agent/internal/ssh/collector.go (drops config import in same refactor)"
decisions:
  - "Refactored netconf.Collector.GetRoutes + ssh.Collector.GetRoutes to take (host, port, user, pass) primitives instead of config.Device — Plan 10-04/05's original signature created an internal/config↔internal/netconf import cycle once config.LoadConfigImport returned netconf.RouteRecord. Primitives are what the Dialer interface already takes; the change is small and removes a layer of coupling."
  - "configImportRoute is a sibling type with explicit yaml: tags rather than adding yaml: tags to netconf.RouteRecord — keeps types.go JSON-tag-only (Pydantic mirror) and decouples the on-disk YAML shape from the wire JSON shape."
  - "Empty `routes: []` returns ([]RouteRecord{}, nil) rather than skipping silently — operators see '0 routes pushed' in the agent log and can distinguish 'no routes' from 'collector skipped'."
  - "ParseShowIPRoute uses regexp.MustCompile for the two route line forms (via-route + connected) — IOS-XE `show ip route` has only these two structural variants; legend / banner / blank lines silently skipped."
metrics:
  duration: "~30m (Tasks 1+2 prior session, Task 3 + cycle refactor this session)"
  completed_date: "2026-05-10"
  tasks_completed: 3
  tasks_total: 3
  files_created: 5
  files_modified: 4
  tests_green: 12
  commits: 5
---

# Phase 10 Plan 05: SSH + Config-Import Collectors (DCA-03 + DCA-07) Summary

Three collection paths now converge on the same `[]netconf.RouteRecord`:
NETCONF (10-04, prior plan), SSH `show ip route` (this plan), and operator-authored
YAML route files for air-gapped sites (this plan). Plan 10-07 wires all three
into the daemon and pushes to the backend.

## What Was Built

### Task 1: Pure-function IOS-XE route table parser

**Commits:** `9830b77` (RED, 7 failing parser tests) → `8312b0a` (GREEN, ParseShowIPRoute implementation).

`ParseShowIPRoute(string) []netconf.RouteRecord` handles the two structural forms IOS-XE emits:

- `<code> <prefix>/<mask> [<admin>/<metric>] via <next-hop>[, <iface>][, <age>]`
- `<code> <prefix>/<mask> is directly connected, <iface>`

Single-char protocol codes (`S`, `S*`, `B`, `R`, `O`, `C`, `L`, `D`, `i`) normalize to lowercase strings. Codes legend, gateway-of-last-resort, and blank lines are silently skipped via per-line regex match.

### Task 2: SSH Collector + Dialer/Session abstraction

**Commits:** `e36e97d` (RED, 5 failing collector tests) → `e91c398` (GREEN, Collector + DefaultDialer).

Mirror of the netconf package's interface shape: `Dialer.Dial(ctx, host, port, user, pass) (Session, error)` and `Session.Run(ctx, command) (string, error)` + `Close() error`.

DefaultDialer's `interactiveSession.Run`:
1. Allocates a PTY (`xterm`, 200×200, ECHO=0).
2. Opens a shell via `sess.Shell()` and writes `terminal length 0\n<command>\nexit\n` to stdin in one payload.
3. Captures stdout via `bytes.Buffer`. PTY+stdin pattern is required because IOS-XE without `terminal length 0` truncates `show ip route` at 24 lines (RESEARCH Pitfall 2).

### Task 3: Config-import fallback (DCA-07)

**Commits:** `9d386bf` (RED, 5 failing TestConfigImport_* tests) → `0509633` (GREEN, LoadConfigImport + cycle refactor).

`LoadConfigImport(path) ([]netconf.RouteRecord, error)` reads operator-authored YAML:

```yaml
routes:
  - prefix: "10.0.0.0/8"
    next_hop: "192.168.1.254"
    protocol: static
    metric: 1
```

Empty `routes: []` returns an empty slice (no error). Missing files / malformed YAML produce wrapped errors with `config-import: read` / `config-import: parse` prefixes.

#### Cycle refactor (in same GREEN commit)

Adding `LoadConfigImport(path) ([]netconf.RouteRecord, error)` to package `config` created an `internal/config → internal/netconf → internal/config` cycle (both NETCONF and SSH collectors took `config.Device`). Resolved by changing both collectors' `GetRoutes` signatures to primitives:

```go
func (c *Collector) GetRoutes(ctx context.Context, host string, port int, user, pass string) ([]RouteRecord, error)
```

Primitives match what `Dialer.Dial` already takes — call-site noise is unchanged once Plan 10-07 destructures `dev.Host, dev.Port, dev.Username, dev.Password` at the daemon fan-out. Updated 9 call sites in test files.

## Verification

| Check | Result |
|-------|--------|
| `go test ./internal/ssh/... -count=1 -timeout 30s` | 12 tests PASS (7 parser + 5 collector) |
| `go test ./internal/config/... -count=1 -timeout 30s` | 12 tests PASS (7 prior + 5 new TestConfigImport_*) |
| `go test ./... -race -count=1 -timeout 120s` | 6 packages GREEN under -race |
| `go vet ./...` | clean |

## Convergence on RouteRecord

After this plan, three distinct collection paths produce the same `[]netconf.RouteRecord`:

1. **NETCONF** — `netconf.Collector.GetRoutes(ctx, host, 830, user, pass)` (10-04).
2. **SSH CLI** — `ssh.Collector.GetRoutes(ctx, host, 22, user, pass)` (this plan).
3. **Air-gapped file** — `config.LoadConfigImport(path)` (this plan).

Plan 10-07's daemon wiring will branch on `device.Protocol` (`netconf`/`ssh`/`config-import`) and dispatch to the appropriate path before pushing the merged route batch.

## Out of Scope

- Real device integration tests (require live IOS-XE — defer to manual smoke test).
- known_hosts host-key verification (CAB-documented limitation, Plan 10-09).
- Encrypted credential storage (Plan 10-09 documents OS-keychain hand-off).
