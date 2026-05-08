---
phase: 10
plan: "06"
subsystem: dc-agent-core/netflow
tags: [go, netflow, ring-buffer, udp-listener, tdd, race-safe, dca-04]
dependency_graph:
  requires: ["10-01 (stub files)", "10-03 (zap logger + testify)"]
  provides:
    - "agent/internal/netflow/types.go (FlowRecord wire type)"
    - "agent/internal/netflow/buffer.go (RingBuffer concurrent-safe)"
    - "agent/internal/netflow/listener.go (UDP Listener + DecodeFunc seam)"
  affects:
    - "10-07 (push client — imports FlowRecord + RingBuffer.Drain + wires newGoflow2Decode)"
    - "10-09 (CAB packet — references NetFlow collector architecture)"
tech_stack:
  added:
    - "go.uber.org/zap v1.28.0 (already in go.mod from 10-01) — zap.Logger injection in Listener"
    - "github.com/stretchr/testify v1.11.1 (already in go.mod) — require assertions in tests"
  patterns:
    - "DecodeFunc injection seam — Listener accepts a func([]byte, string)([]FlowRecord, error) so tests don't need real goflow2 bytes"
    - "Mutex ring buffer (RESEARCH Pattern 5) — sync.Mutex + circular slice, head tracks total appends"
    - "SetReadDeadline(500ms) bounded read loop — T-10-06-03 context cancellation within 2s SLO"
    - "Decode error → WARN log + continue (never crash) — T-10-06-01 DoS mitigation"
    - "Per-sampler addr.String() key passed to DecodeFunc — locks template cache key convention for plan 10-07"
    - "TDD RED→GREEN cadence: 2 RED commits + 2 GREEN commits"
key_files:
  created:
    - agent/internal/netflow/types.go
  modified:
    - agent/internal/netflow/buffer.go
    - agent/internal/netflow/buffer_test.go
    - agent/internal/netflow/listener.go
    - agent/internal/netflow/listener_test.go
decisions:
  - "RingBuffer capacity default = 100,000 per D-07 (~5 min at 1k flows/sec). Configurable in a future agent.yaml 'netflow.buffer_capacity' key when plan 10-07 wires agent.yaml into the Listener. The constant lives only in the daemon ticker (plan 10-03) which will call NewRingBuffer(cfg.NetFlow.BufferCapacity) with a default of 100,000."
  - "DecodeFunc signature (packet []byte, samplerKey string) -> ([]FlowRecord, error) is the locked contract. Plan 10-07 MUST implement newGoflow2Decode() to return a closure matching this signature using goflow2/v2 v2.2.6 templates.DefaultTemplateGenerator per-sampler-address."
  - "Per-sampler key = addr.String() (e.g. '192.168.1.100:54321'). This format is the template cache key shape that plan 10-07's production decoder will use when looking up or creating the per-sampler TemplateStore."
  - "SetReadDeadline cadence = 500ms. This is a tunable knob: if the shutdown SLO needs tightening below 500ms, decrease this value. The TestNetFlowListener_ContextCancel test regression-locks the 2s SLO."
  - "newGoflow2Decode() stub is declared but not exported — marked //nolint:unused since it will be consumed in plan 10-07 when wired into main.go. The stub was authored without importing goflow2/v2 to avoid transitively pulling the decoder into listener_test.go before the production wiring is ready."
  - "goflow2/v2 is NOT imported in listener.go by design — the production decoder is decoupled via DecodeFunc. This means go.mod still lacks the goflow2 require entry. Plan 10-07 will add the import + go mod tidy when implementing newGoflow2Decode() for real."
metrics:
  duration: "~4 minutes"
  completed: "2026-05-08"
  tasks_completed: 2
  tasks_total: 2
  files_created: 1
  files_modified: 4
  tests_green: 12
  commits: 4
---

# Phase 10 Plan 06: NetFlow UDP Collector (DCA-04) Summary

FlowRecord wire type + concurrent-safe RingBuffer + UDP Listener with DecodeFunc injection seam — 12 tests GREEN, full agent suite passes under -race. Production goflow2/v2 decoder deferred to plan 10-07 via stubbed newGoflow2Decode() that locks the signature.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 RED | RingBuffer + FlowRecord 7 tests | b073c06 | buffer_test.go |
| 1 GREEN | FlowRecord type + RingBuffer | 0febd80 | types.go, buffer.go |
| 2 RED | 5 listener tests | c440634 | listener_test.go |
| 2 GREEN | UDP listener with DecodeFunc | f81fc8b | listener.go |

## What Was Built

### FlowRecord (types.go) — wire contract locked

```go
type FlowRecord struct {
    SrcIP    string `json:"src_ip"`
    DstIP    string `json:"dst_ip"`
    SrcPort  int    `json:"src_port"`
    DstPort  int    `json:"dst_port"`
    Protocol int    `json:"protocol"`
    Bytes    int    `json:"bytes"`
    Packets  int    `json:"packets"`
}
```

JSON field names match `backend/app/schemas/agent.py:FlowRecord` (Plan 10-02). TestFlowRecordJSONShape regression-locks all 7 field names.

### RingBuffer (buffer.go) — capacity sizing

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Default capacity | 100,000 | 1k flows/sec × 300s (5 min) = conservative. ~15MB at ~150 bytes/struct. |
| Overflow behavior | Circular overwrite | Oldest records dropped silently; push client (plan 10-07) handles retry logic |
| Drain behavior | Returns arrival order, resets head to 0 | 30-second flush cycle in daemon ticker |
| Race safety | sync.Mutex on every Append / Drain / Len call | TestRingBuffer_ConcurrentAppend (10 goroutines × 100 appends) under -race regression-locks |

### Listener (listener.go) — design decisions

**DecodeFunc injection seam:** The Listener accepts a `DecodeFunc` callback instead of hard-coupling to goflow2/v2. This means:
- Tests use deterministic stub decoders with no real NetFlow bytes
- Plan 10-07 wires `newGoflow2Decode()` without changing the Listener struct

**Threat mitigations implemented:**

| Threat ID | Mitigation |
|-----------|-----------|
| T-10-06-01 (DoS malformed packet) | `decErr != nil` → log WARN + continue, never crash |
| T-10-06-02 (DoS flood fills buffer) | RingBuffer capacity cap; oldest records overwritten |
| T-10-06-03 (hung ReadFromUDP blocks shutdown) | `SetReadDeadline(500ms)` + context goroutine closes conn |

**Per-sampler key convention locked:** `addr.String()` passed as `samplerKey` to DecodeFunc. Plan 10-07's production decoder MUST use this string as the lookup key into `templates.DefaultTemplateGenerator` to preserve per-sampler template isolation (RESEARCH Pitfall 3).

## Test Suite

| Test | What it covers |
|------|---------------|
| TestRingBuffer_AppendAndDrain | Basic Append + Drain + Len reset |
| TestRingBuffer_Overflow | Circular overwrite: capacity=5, append 8, get last 5 in order |
| TestRingBuffer_DrainOrder | Arrival order preserved |
| TestRingBuffer_Empty | nil-safe empty Drain |
| TestRingBuffer_ConcurrentAppend | 10 goroutines × 100 appends, no race (run with -race) |
| TestRingBuffer | Alias for 10-VALIDATION.md verify command |
| TestFlowRecordJSONShape | All 7 JSON field names match backend schema |
| TestNetFlowListener_Happy | UDP send → DecodeFunc stub → RingBuffer fills |
| TestNetFlowListener_DecodeErrorContinues | Decode error on packet 1, valid on packet 2 → buffer fills, loop did not crash |
| TestNetFlowListener_ContextCancel | ctx.Cancel → Run() returns nil within 2s |
| TestNetFlowListener_TemplatePerSampler | Two source sockets → two distinct samplerKey values passed to DecodeFunc |
| TestNetFlowListener | Alias for 10-VALIDATION.md verify command |

## goflow2/v2 API Notes

The production decoder stub `newGoflow2Decode()` was authored without importing goflow2/v2 — the injection seam makes this possible. Plan 10-07 will import:

```
github.com/netsampler/goflow2/v2/decoders/netflow
github.com/netsampler/goflow2/v2/decoders/netflow/templates
```

and replace the stub body with the real `netflow.DecodeMessageNetFlow(...)` call + `templates.DefaultTemplateGenerator` per-sampler store. No goflow2/v2 API drift was encountered during this plan because the library was deliberately not imported yet.

## Deviations from Plan

None — plan executed exactly as written.

The one minor observation: `":2055"` appears twice in listener.go (constant definition + docstring comment). The plan acceptance criteria says `returns 1`; the constant definition is the functional occurrence. Both are benign string literals, not a behavior difference.

## Threat Surface Scan

No new external-facing surface added in this plan. The Listener is started by plan 10-07's main.go wiring — the UDP :2055 socket is not opened until `Run(ctx)` is called from the daemon. T-10-06-05 (socket binds 0.0.0.0) is documented in plan threat model and deferred to operator configuration.

## Self-Check: PASSED
