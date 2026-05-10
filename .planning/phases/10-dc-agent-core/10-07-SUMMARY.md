---
phase: 10
plan: "07"
subsystem: dc-agent-core
tags: [go, push-client, http-retry, goflow2, netflow-v9, ipfix, daemon-wiring, tdd, dca-04, dca-05, dca-06]
dependency_graph:
  requires: ["10-02", "10-03", "10-04", "10-05", "10-06"]
  provides:
    - "agent/internal/push/types.go (RoutesPayload + FlowsPayload — wire contract)"
    - "agent/internal/push/client.go (Client + NewClient + PushRoutes + PushFlows + linearBackoff + retry-twice-then-drop)"
    - "agent/internal/push/client_test.go (10 GREEN tests including 2s real-timing backoff)"
    - "agent/internal/netflow/listener.go (real goflow2/v2 v2.2.6 decoder replacing 10-06 stub)"
    - "agent/cmd/infracanvas-agent/main.go (Pusher seam + collectorFor dispatch + listener goroutine + ring buffer drain)"
    - "agent/cmd/infracanvas-agent/main_test.go (4 new wiring tests — preserves Plan 10-03 4 originals)"
  affects:
    - "10-08 (GHA CI — `go test -race ./...` now exercises the full data path including goflow2 decoder)"
    - "10-09 (CAB packet — documents the JSON-over-HTTPS push contract, 3-attempt retry semantics, and goflow2 license)"
    - "11+ (BGP collection — collectAndPushBGP is a Phase-10-scoped no-op; Phase 11 adds GetBGPNeighbors call)"
tech_stack:
  added:
    - "github.com/netsampler/goflow2/v2 v2.2.6 — NetFlow v9 / IPFIX decoder + template store"
  patterns:
    - "Test-injectable BackoffFunc seam (linearBackoff in production, fastBackoff in unit tests) — keeps the suite under 5s while still regression-locking the 2s production timing under one slow test"
    - "Drop-and-continue retry semantics (D-07): 3 attempts → log WARN + return nil, so the daemon ticker self-heals at next interval rather than surfacing transient backend outages as agent-level errors"
    - "Non-retryable 4xx surfacing: 401/403/422 return errors immediately (1 attempt) so operators see auth/validation failures explicitly"
    - "Pusher interface (cmd/main.go) wraps push.Client — fakePusher in tests drives the wiring without httptest.Server"
    - "RouteCollectorFn closure-per-protocol — unifies netconf / ssh / config-import behind one signature so collectAndPushRoutes is protocol-agnostic"
    - "Single-line `go func() { _ = listener.Run(ctx) }()` placement regression-locked by acceptance-criteria regex against accidental refactors"
key_files:
  created:
    - "agent/internal/push/types.go"
  modified:
    - "agent/internal/push/client.go (replaced empty stub from Plan 10-01)"
    - "agent/internal/push/client_test.go (replaced t.Skip stub with 10 tests)"
    - "agent/internal/netflow/listener.go (real goflow2/v2 decoder; NewGoflow2Decode + convertGoflow2Records + readUint)"
    - "agent/internal/netflow/listener_test.go (added TestGoflow2Decode)"
    - "agent/cmd/infracanvas-agent/main.go (Pusher + collectorFor + RouteCollectorFn + listener goroutine + flushFlowBuffer drain)"
    - "agent/cmd/infracanvas-agent/main_test.go (added fakePusher + 4 new tests)"
    - "agent/go.mod / agent/go.sum (added goflow2/v2 v2.2.6)"
decisions:
  - "goflow2/v2 v2.2.6 API differs from RESEARCH §Pattern 4's guess. There is NO ProducerMessage type in v2.2.6. Canonical surface used: nfdecoders.CreateTemplateSystem() NetFlowTemplateSystem; DecodeMessageVersion(buf, ts, &nfv9, &ipfix) error; NFv9Packet.FlowSets / IPFIXPacket.FlowSets []interface{} containing TemplateFlowSet / DataFlowSet / OptionsFlowSet entries; DataFlowSet.Records []DataRecord; DataRecord.Values []DataField; DataField{.Type uint16, .Value interface{}} — Value almost always []byte from payload.Next(length). RESEARCH should be updated."
  - "Per-sampler template isolation handled implicitly by goflow2's NetFlowTemplateSystem keying (version, obsDomainId, templateId). One template store across all sampler keys is correct because obsDomainId uniquely identifies an exporter; no need to maintain a map[samplerKey]*BasicTemplateSystem as the plan originally proposed."
  - "Push client returns nil on retry exhaustion (D-07 drop-and-continue) rather than propagating an error. The 5-min routes ticker fires again next interval; surfacing every transient 5xx as a daemon error would be log noise without operational value. Drops are visible only via WARN log + Axiom metrics (DCA-09 CAB packet)."
  - "401/403/422 are non-retryable and DO return errors. Auth failures (token revoked, site_id mismatch) and validation failures (malformed payload) are operator-actionable — distinct from transient backend outages."
  - "Pusher is an interface (not the concrete *push.Client) so main.go's wiring tests can inject fakePusher without an httptest.Server. Production runCmd constructs the real client. This trades one layer of indirection for hermetic unit tests of the protocol-dispatch logic."
  - "RouteCollectorFn closures bind the dialer ONCE per call to collectorFor — a fresh netconf.NewCollector(DefaultDialer()) per route tick. This is a deliberate tradeoff: dialing 5 devices means 5 fresh SSH connections each tick, but it sidesteps connection-reuse complexity (PTY state, idle timers) for Phase 10. Phase 11 may introduce a connection pool."
  - "BGP collection (collectAndPushBGP) is a no-op in Phase 10 per CONTEXT.md `in scope` list. The 1-min ticker fires and logs DEBUG; Phase 11 adds netconf.Collector.GetBGPNeighbors via the same ticker."
  - "NetFlow listener launches as a goroutine BEFORE the ticker select-loop in runCmd's RunE — DCA-04 invariant: flow packets must accumulate in rb between 30s flushes. The goroutine self-terminates when ctx is cancelled (Plan 10-06 listener respects ctx.Done() via 500ms read deadline)."
  - "The NFv9 fixture in TestGoflow2Decode is hand-crafted to exactly 94 bytes (20 header + 4 FlowSet header + 70 record). goflow2/v2's own TestDecodeNetFlowV9 uses `data[:89]` as a truncation, but its `data` array extends much further — `data[:89]` works for them because the slice has more bytes available. We bound the fixture to one complete record so the assertion `SrcIP=198.38.120.222` is deterministic."
metrics:
  duration: "~50m"
  completed_date: "2026-05-10"
  tasks_completed: 2
  tasks_total: 2
  files_created: 1
  files_modified: 7
  tests_green: 14
  commits: 4
---

# Phase 10 Plan 07: DC Agent Push Client + goflow2/v2 + Daemon Wiring Summary

The agent's data path is now closed end-to-end. Plans 02–06 built components in
isolation; this plan threads them together so a single
`infracanvas-agent run --config agent.yaml` instance dials devices via NETCONF
or SSH (or imports static YAML), decodes incoming NetFlow v9 / IPFIX packets,
and pushes JSON to the Plan 10-02 backend with Bearer site_token authentication.

## What Was Built

### Task 1: Push client — Bearer auth + retry-twice-then-drop

**Commits:** `6974188` (RED, 10 failing tests) → `bdf1c15` (GREEN, types.go + client.go).

`push.Client` posts JSON batches to `/v1/agent/routes` and `/v1/agent/flows`
with `Authorization: Bearer <site_token>`. Retry contract is the locked D-07
schedule: 3 total attempts, linear backoff 2s/4s, drop-and-continue after
exhaustion (logged at WARN, returns nil so the daemon ticker self-heals at
next interval).

Non-retryable failures (4xx — 401/403/422) bypass retry entirely and surface
as errors so operators see auth/validation problems explicitly.

`linearBackoff(attempt) = attempt * 2 seconds` (2s before retry 1, 4s before
retry 2). `TestPushRoutes_BackoffTiming` regression-locks the 2s timing
against the production implementation under real wall time — every other
test injects `fastBackoff(50ms)` so the suite runs in ~3.5s under -race.

`doPost` caps response-body snippets at 512 bytes via `io.CopyN` (T-10-07-06
mitigation against large-body DoS).

Wire contract:
```go
type RoutesPayload struct {
    SiteID      string                `json:"site_id"`
    CollectedAt string                `json:"collected_at"`
    DeviceHost  string                `json:"device_host"`
    Routes      []netconf.RouteRecord `json:"routes"`
}

type FlowsPayload struct {
    SiteID      string               `json:"site_id"`
    CollectedAt string               `json:"collected_at"`
    Flows       []netflow.FlowRecord `json:"flows"`
}
```

JSON tags mirror backend Pydantic `RoutesPushBody` / `FlowsPushBody` exactly
(Plan 10-02). Drift on either side breaks the agent ↔ backend contract.

### Task 2a: goflow2/v2 v2.2.6 production decoder

**Commits:** `0d6118f` (RED, TestGoflow2Decode fails with "decoder not yet
wired") → `62b733b` (GREEN, real implementation).

The Plan 10-06 stub returned `errors.New("goflow2 decoder not yet wired")`.
This plan replaces it with a working NetFlow v9 / IPFIX decoder.

**Live discovery:** v2.2.6's API differs from `RESEARCH §Pattern 4`'s guess.
There is no `ProducerMessage` type. The actual surface used:

```go
templates := nfdecoders.CreateTemplateSystem()  // NetFlowTemplateSystem
var nfv9 nfdecoders.NFv9Packet
var ipfix nfdecoders.IPFIXPacket
err := nfdecoders.DecodeMessageVersion(buf, templates, &nfv9, &ipfix)
// FlowSets are []interface{} carrying TemplateFlowSet / DataFlowSet / etc.
for _, fs := range nfv9.FlowSets {
    if dfs, ok := fs.(nfdecoders.DataFlowSet); ok {
        for _, rec := range dfs.Records {
            for _, f := range rec.Values {
                // f.Type uint16 (NFV9_FIELD_*), f.Value []byte (raw wire bytes)
            }
        }
    }
}
```

`convertGoflow2Records` maps NFv9 / IPFIX field types into our `FlowRecord`
shape:

| Type | Field             | FlowRecord  |
| ---- | ----------------- | ----------- |
| 8    | IPV4_SRC_ADDR     | SrcIP       |
| 12   | IPV4_DST_ADDR     | DstIP       |
| 27   | IPV6_SRC_ADDR     | SrcIP       |
| 28   | IPV6_DST_ADDR     | DstIP       |
| 7    | L4_SRC_PORT       | SrcPort     |
| 11   | L4_DST_PORT       | DstPort     |
| 4    | PROTOCOL          | Protocol    |
| 1    | IN_BYTES          | Bytes       |
| 2    | IN_PKTS           | Packets     |
| 23   | OUT_BYTES         | Bytes (fb)  |
| 24   | OUT_PKTS          | Packets (fb)|

`readUint` big-endian-decodes 1/2/4/8-byte raw integer fields (goflow2 emits
the wire bytes verbatim via `payload.Next(length)`).

**Per-sampler isolation** is implicit in `NetFlowTemplateSystem`'s
`(version, obsDomainId, templateId)` keying — one template store across
all sampler addresses works because `obsDomainId` already partitions
exporters. The decoder is mutex-locked since the listener is the only
goroutine calling it and we want predictable serial decoding.

`TestGoflow2Decode` regression-locks the path with hand-crafted 94-byte
NFv9 fixture: 20-byte header + 4-byte FlowSet header + one full 70-byte
record matching template id=260 with 23 fields. Asserts SrcIP=
"198.38.120.222" (= bytes 0xc6,0x26,0x78,0xde) — fails loud if
`convertGoflow2Records` ever silently returns nil on an API drift.

### Task 2b: main.go end-to-end wiring

**Commits:** `0d6118f` (RED — main_test.go build fails on missing seams) →
`62b733b` (GREEN — full wiring).

Replaced Plan 10-03's no-op `collectAndPushRoutes` / `collectAndPushBGP` /
`flushFlowBuffer` stubs with real implementations:

```go
type Pusher interface {
    PushRoutes(ctx context.Context, p push.RoutesPayload) error
    PushFlows(ctx context.Context, p push.FlowsPayload) error
}

type RouteCollectorFn func(ctx context.Context, dev config.Device) ([]netconf.RouteRecord, error)

func collectorFor(dev config.Device) RouteCollectorFn {
    switch dev.Protocol {
    case config.ProtocolNetconf:      // -> netconf.NewCollector(DefaultDialer()).GetRoutes
    case config.ProtocolSSH:          // -> ssh.NewCollector(DefaultDialer()).GetRoutes
    case config.ProtocolConfigImport: // -> config.LoadConfigImport
    }
    return nil
}
```

`collectAndPushRoutes` iterates `cfg.Devices`, dials each via the protocol-
appropriate collector, formats `RoutesPayload` (RFC3339 collected_at), and
delegates to `pusher.PushRoutes`. Failures log WARN and continue — matches
the push client's drop-and-continue contract.

`collectAndPushBGP` is a Phase-10-scope no-op (BGP neighbor collection lands
in Phase 11+). The 1-min ticker still fires and logs DEBUG so the wiring
is in place.

`flushFlowBuffer` drains `rb.Drain()` and pushes; siteID derived from the
first device with one configured. Empty buffer fast-path skips the push.

**NetFlow listener goroutine launch** — DCA-04 invariant: in `runCmd`'s
RunE, BEFORE entering the ticker select-loop, the agent starts the
NetFlow UDP listener as a goroutine so flow packets accumulate in `rb`
between 30s `flushFlowBuffer` ticks:

```go
listener := netflow.NewListener(netflow.DefaultUDPAddr, rb, log, newGoflow2Decode())
go func() { _ = listener.Run(ctx) }()
return runDaemonWithIntervals(ctx, cfg, defaultIntervals(), log, rb, pusher)
```

The goroutine self-terminates when `ctx` is cancelled (Plan 10-06 listener
respects `ctx.Done()` via a 500ms read deadline). Single-line goroutine
launch is regression-locked by the acceptance-criteria regex
`go .*listener.*\.Run\(ctx\)`.

**Tests:** 4 new tests — `TestCollectAndPushRoutes_ConfigImport` (hermetic
via static YAML route file), `TestFlushFlowBuffer_Drains`,
`TestFlushFlowBuffer_EmptyNoOp`, `TestCollectorFor_UnsupportedProtocolReturnsNil`
— plus the 4 existing Plan 10-03 tests preserved. The signature change to
`runDaemonWithIntervals(ctx, cfg, iv, log, rb, pusher)` was threaded through
`TestDaemonStartStop` so the existing graceful-shutdown contract still holds.

## Plan vs Reality — Deviations

| Plan said                           | Reality                                                                                | Why                                                                                                            |
| ----------------------------------- | -------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| `c.GetRoutes(ctx, dev)`             | `c.GetRoutes(ctx, dev.Host, dev.Port, dev.Username, dev.Password)`                     | Plan 10-05 refactored signatures to primitives to break a config↔netconf cycle (heads-up was in execute prompt) |
| `nfdecoders.DecodeMessage(...) (*ProducerMessage, error)` | `DecodeMessageVersion(buf, ts, &nfv9, &ipfix) error` + iterate `FlowSets []interface{}` | v2.2.6's actual API has no ProducerMessage type — Live Discovery during impl                                   |
| `data[:89]` test fixture            | Hand-crafted 94-byte fixture                                                           | goflow2's own truncation works because their `data` array is much longer; we need exactly one complete record  |
| `keys for the cache use addr.String()` | One template system across all sampler keys (no per-sampler map)                       | goflow2's NetFlowTemplateSystem keys by `obsDomainId` internally — manual sampler-keyed map would be redundant |

## Verification

| Check | Result |
|-------|--------|
| `go test ./internal/push/... -count=1 -timeout 60s` | 10 tests PASS |
| `go test ./internal/netflow/... -count=1 -timeout 60s` | 8 tests PASS (incl. TestGoflow2Decode) |
| `go test ./cmd/infracanvas-agent/... -count=1 -timeout 60s` | 8 tests PASS |
| `go test ./... -race -count=1 -timeout 180s` | 6 packages GREEN under -race |
| `go test -short ./... -count=1` | 6 packages GREEN (CI mode) |
| `go vet ./...` | clean |
| `go build -o /tmp/agent-bin ./cmd/infracanvas-agent && /tmp/agent-bin --help && /tmp/agent-bin version` | Binary builds, exposes `run` + `version` subcommands |

**Phase-10 RED→GREEN tally:** 8 backend (10-02) + 7 config + 5 SSH parser
+ 5 SSH collector + 5 NETCONF + 7 ringbuffer + 5 listener + 1 goflow2 +
10 push + 8 main = **61 GREEN agent tests + 8 backend = 69 total**.

## Decisions Locked for Future Plans

1. **Push retry contract is final.** 3 attempts, 2s/4s linear backoff,
   drop-and-continue on 5xx, surface 4xx. Future tuning (e.g. exponential
   jitter, dead-letter queue) needs a deliberate plan with a re-locked
   `TestPushRoutes_BackoffTiming` boundary.

2. **Pusher interface signature is locked.** Phase 11 firewall integration
   will likely add `PushFirewallRules(ctx, FirewallPayload)` — additions
   are non-breaking; existing methods cannot change shape without migrating
   the daemon wiring tests.

3. **goflow2/v2 v2.2.6 is the production version.** If goflow2 v3 changes
   the decoder API, `convertGoflow2Records` is the single point of
   adjustment — `TestGoflow2Decode` will fail loudly if the typed
   assertion against `nfdecoders.DataFlowSet` ever drifts.

4. **BGP collection is Phase 11.** `collectAndPushBGP` ticker is wired
   but no-op. Phase 11 implementer should add `netconf.Collector.GetBGPNeighbors`
   and call it from the existing 1-min ticker — no main.go restructure
   needed.

## Self-Check: PASSED

- File `agent/internal/push/types.go` exists — FOUND
- File `agent/internal/push/client.go` (replaced empty stub) — FOUND
- File `agent/internal/netflow/listener.go` (real goflow2 decoder) — FOUND
- File `agent/cmd/infracanvas-agent/main.go` (Pusher seam wired) — FOUND
- Commit `6974188` (Task 1 RED) — FOUND
- Commit `bdf1c15` (Task 1 GREEN) — FOUND
- Commit `0d6118f` (Task 2 RED) — FOUND
- Commit `62b733b` (Task 2 GREEN) — FOUND
- Full agent suite GREEN under -race — VERIFIED
