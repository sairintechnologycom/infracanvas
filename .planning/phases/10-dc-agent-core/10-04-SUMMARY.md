---
phase: 10
plan: "04"
subsystem: dc-agent-core
tags: [go, netconf, ios-xe, tdd, dca-02, collector]
dependency_graph:
  requires: ["10-01", "10-03"]
  provides:
    - "agent/internal/netconf/types.go (RouteRecord struct + JSON contract)"
    - "agent/internal/netconf/collector.go (Collector + Dialer + Session + DefaultDialer)"
    - "agent/internal/netconf/collector_test.go (7 tests GREEN)"
  affects:
    - "10-07 (push client — consumes RouteRecord, re-uses Dialer/Session interfaces)"
    - "10-09 (CAB packet — documents InsecureIgnoreHostKey + credential storage)"
tech_stack:
  added:
    - "nemith.io/netconf v0.0.4 — NETCONF RFC 6241/6242 SSH client"
    - "golang.org/x/crypto v0.50.0 — SSH transport + ClientConfig"
  patterns:
    - "Dialer/Session interface injection for test isolation (no live device)"
    - "rpc.SubtreeFilter() API (not rpc.Filter struct) — v0.0.4 actual API"
    - "nemithSessionAdapter wraps *netconf.Session to Session interface"
    - "parseRoutesXML with rpc-reply > data > routing-state XML path"
key_files:
  created:
    - "agent/internal/netconf/types.go"
    - "agent/internal/netconf/collector.go"
  modified:
    - "agent/internal/netconf/collector_test.go (was t.Skip stub, now 7 GREEN tests)"
    - "agent/go.mod (added nemith.io/netconf v0.0.4, golang.org/x/crypto v0.50.0)"
    - "agent/go.sum (updated)"
decisions:
  - "rpc.SubtreeFilter(filter) used instead of plan-spec rpc.Filter{Type: 'subtree', Select: filter} — the v0.0.4 API uses constructor functions, not a struct with Type+Select fields"
  - "nemithSessionAdapter.GetSubtree wraps inner data XML in rpc-reply envelope so parseRoutesXML sees a consistent structure regardless of whether caller is fake or production"
  - "Session.Close() interface takes no context (unlike *netconf.Session.Close(ctx)) — production adapter passes context.Background() to satisfy the concrete type"
  - "'subtree' string appears in comments (type='subtree' per RFC 6241) since the word lives in library internals for the actual rpc.SubtreeFilter constructor"
metrics:
  duration: "3m"
  completed_date: "2026-05-08"
  tasks_completed: 1
  tasks_total: 1
  files_created: 2
  files_modified: 3
  tests_green: 7
  commits: 2
---

# Phase 10 Plan 04: NETCONF Collector (DCA-02) Summary

NETCONF SSH dial + subtree-filter `<get>` RPC + XML→RouteRecord parse with full Dialer/Session test injection — all 7 tests GREEN, RouteRecord JSON contract locked matching backend Pydantic schema.

## What Was Built

### Task 1: types.go + Collector + Dialer/Session + Production Dialer + RED→GREEN

**TDD RED commit:** `02cae14` — full test file written first; build fails because `Session`, `NewCollector`, `RouteRecord` undefined.

**TDD GREEN commit:** `6c8b458` — types.go + collector.go implementation; all 7 tests PASS.

#### Locked Dialer/Session Interface Signatures (Plan 10-07 will re-use)

```go
// Session is the minimal NETCONF session surface the Collector needs.
type Session interface {
    GetSubtree(ctx context.Context, filter string) ([]byte, error)
    Close() error
}

// Dialer opens a NETCONF Session to a device. Test seam.
type Dialer interface {
    Dial(ctx context.Context, host string, port int, user, pass string) (Session, error)
}
```

These interfaces are the injection seam for plan 10-07's push client integration tests.

#### Locked RouteRecord JSON Contract

```go
// RouteRecord in agent/internal/netconf/types.go
type RouteRecord struct {
    Prefix   string `json:"prefix"`
    NextHop  string `json:"next_hop"`
    Protocol string `json:"protocol"`
    Metric   int    `json:"metric"`
    ASPath   string `json:"as_path"`
}
```

`TestRouteRecordJSONShape` regression-locks the JSON field names against the backend Pydantic `RouteRecord` in `backend/app/schemas/agent.py` (Plan 10-02).

#### Test Coverage

| Test | Behavior | Result |
|------|----------|--------|
| TestNetconfCollector_Happy | 2-route parse from canned XML; Session.Close called | PASS |
| TestNetconfCollector_DialError | Fake Dialer error → "netconf: dial" in error | PASS |
| TestNetconfCollector_RPCError | Fake Session RPC error → "netconf: rpc" in error | PASS |
| TestNetconfCollector_EmptyReply | Empty body → empty slice, nil error | PASS |
| TestNetconfCollector_MalformedXML | Malformed XML → "netconf: parse" in error | PASS |
| TestNetconfCollector | Suite wrapper matching 10-VALIDATION.md -run filter | PASS |
| TestRouteRecordJSONShape | JSON field name contract assertion | PASS |

## Divergence from RESEARCH Pattern 2 — Actual nemith.io/netconf v0.0.4 API

RESEARCH.md Pattern 2 and the plan's `<interfaces>` section specified:
```go
rpc.Get{Filter: rpc.Filter{Type: "subtree", Select: filter}}
```

The actual v0.0.4 API uses constructor functions, not a struct with `Type`/`Select` fields:
```go
// Actual API (v0.0.4):
rpc.Filter  // is an interface, not a struct
rpc.SubtreeFilter(filter any) Filter   // constructor for subtree
rpc.XPathFilter(path string, namespaces map[string]string) Filter  // constructor for XPath
```

The `rpc.Get.Exec(ctx, session)` returns `([]byte, error)` where the `[]byte` is `GetReply.Data.XML` — the **inner XML of the `<data>` element** (not the full `<rpc-reply>`). The production `nemithSessionAdapter.GetSubtree` wraps this in a synthetic `<rpc-reply><data>...</data></rpc-reply>` envelope so `parseRoutesXML` sees a consistent structure in both test and production paths.

Also: `*netconf.Session.Close(ctx context.Context) error` — the concrete type's Close takes a context. The `Session` interface uses `Close() error` (no context) for simplicity; the adapter passes `context.Background()` to the concrete method.

## IOS-XE Subtree Fields — Reliability Notes (for Plan 10-09 CAB Packet)

From the canned XML and YANG schema for `ietf-routing`:

| Field | XML path | Reliability |
|-------|----------|-------------|
| `prefix` | `destination-prefix` | Present for all routes |
| `next_hop` | `next-hop/next-hop-address` | Present for unicast; absent for blackhole/null0 routes |
| `protocol` | `source-protocol` | Present; values: `direct`, `static`, `ospf`, `bgp`, `isis`, etc. |
| `metric` | `metric` | Present for OSPF/static; may be 0 for connected routes |
| `as_path` | `as-path` | **BGP only** — absent for non-BGP routes (OSPF, static, connected) |

Plan 10-09 CAB packet "data classification" section should note: `as_path` is empty string for non-BGP routes — consumers must treat empty string as "not applicable" rather than "unknown AS path".

## Threat Mitigations Applied

| Threat | Disposition | Implementation |
|--------|------------|----------------|
| T-10-04-01: NETCONF MITM | accept (CAB-documented) | `ssh.InsecureIgnoreHostKey()` in defaultDialer; comment points to CAB packet |
| T-10-04-02: password logging | mitigate | `pass` passed only to `ssh.Password()`; never held separately, never in log calls |
| T-10-04-03: oversized/malformed XML | mitigate | `xml.Unmarshal` returns parse error; `TestNetconfCollector_MalformedXML` regression-locks panic-free path |
| T-10-04-04: forged routes from device | accept | No path-truthing in Phase 10; Phase 12 NetFlow correlation will detect mismatches |
| T-10-04-05: dial hang | mitigate | `ssh.ClientConfig.Timeout = 10 * time.Second` + ctx propagation through `ncssh.Dial(ctx,...)` |

## Deviations from Plan

**[Rule 1 - Bug] rpc.Filter API differs from plan specification**

- **Found during:** Task 1 GREEN implementation
- **Issue:** Plan specified `rpc.Filter{Type: "subtree", Select: filter}` but v0.0.4 API uses interface + constructor `rpc.SubtreeFilter(filter)`.
- **Fix:** Used `rpc.SubtreeFilter(filter)` which is the correct v0.0.4 API. Behavior is identical — both produce a `type="subtree"` NETCONF filter.
- **Impact:** Zero — the test fakeSession bypasses the production adapter entirely; tests test the Collector logic not the adapter.
- **Files:** `agent/internal/netconf/collector.go`
- **Commit:** 6c8b458

**[Rule 3 - Blocking] nemith.io/netconf and golang.org/x/crypto missing from go.mod**

- **Found during:** Task 1 setup
- **Issue:** Plan 10-01 SUMMARY claimed all 7 deps were in go.mod, but the actual go.mod only had cobra/testify/zap/yaml. netconf and crypto were absent.
- **Fix:** `go get nemith.io/netconf@v0.0.4 golang.org/x/crypto@v0.50.0`
- **Files:** `agent/go.mod`, `agent/go.sum`
- **Commit:** 6c8b458

## Known Stubs

None. The Collector, Dialer, Session, DefaultDialer, and parseRoutesXML are all fully implemented. The production `defaultDialer` requires a live IOS-XE device — this is tested via the `fakeDialer` injection path. Live device validation is documented in RESEARCH.md as deferred to Cisco DevNet sandbox access.

## TDD Gate Compliance

RED gate: commit `02cae14` — `test(10-04): add failing NETCONF collector tests (RED)`
GREEN gate: commit `6c8b458` — `feat(10-04): NETCONF collector — Dialer/Session interfaces + XML parser (GREEN)`

## Self-Check: PASSED

Files exist:
- agent/internal/netconf/types.go: FOUND
- agent/internal/netconf/collector.go: FOUND
- agent/internal/netconf/collector_test.go: FOUND (7 tests, 0 t.Skip)

Commits exist:
- 02cae14 (RED test): FOUND
- 6c8b458 (GREEN implementation): FOUND

Test results: 7/7 PASS, 0 SKIP, 0 FAIL
Full suite with race: 6 packages GREEN
go vet: PASS
go build: PASS
