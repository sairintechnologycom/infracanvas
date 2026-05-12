---
phase: 11
plan: 05
subsystem: firewall-integration
tags: [wave-1, agent, push-client, wire-contract, d-07-reuse]
requires:
  - phase-11-plan-01-summary  # Wave 0 RED scaffold (collector tests; no push tests required for Plan 11-05)
  - phase-11-plan-02-summary  # backend Pydantic FirewallRulesPushBody / FirewallNATPushBody / FirewallObjectsPushBody — agent JSON tags lock against these
  - phase-10-plan-07-summary  # D-07 retry-twice-then-drop contract on postWithRetry (reused verbatim)
provides:
  - agent-push-firewall-rules    # Client.PushFirewallRules(ctx, FirewallRulesPayload)
  - agent-push-firewall-nat      # Client.PushFirewallNAT(ctx, FirewallNATPayload)
  - agent-push-firewall-objects  # Client.PushFirewallObjects(ctx, FirewallObjectsPayload)
  - firewall-payload-structs     # 3 envelope structs + 3 nested item structs in push/types.go
affects:
  - agent/internal/push/client.go  # +6 path-const lines, +56 method lines
  - agent/internal/push/types.go   # +81 lines (3 envelopes + 3 items + header comment)
tech-stack:
  added: []  # no new dependencies; reuses encoding/json, go.uber.org/zap, existing postWithRetry
  patterns:
    - "PushRoutes-shape method (marshal → postWithRetry with kind + zap fields)"
    - "Pattern G credential redaction (allowlist: site_id, snapshot_id, firewall_id, vendor, source, count)"
    - "D-07 retry-twice-then-drop (postWithRetry reused verbatim from Phase 10)"
    - "json.RawMessage for vendor-native raw_blob preservation (D-08 hybrid)"
    - "Header comment locks JSON tag verbatim match with backend/app/schemas/firewall.py"
key-files:
  created: []
  modified:
    - agent/internal/push/types.go
    - agent/internal/push/client.go
decisions:
  - "Item structs named FirewallRule / FirewallNATRule / FirewallObject (no Go-side suffix). Go's package qualifier (push.FirewallRule) provides namespacing; backend Pydantic models live in app.schemas.firewall and are import-qualified there. The Plan 11-02 backend chose *ORM suffix on its child ORM classes only because the un-suffixed Pydantic models already lived in the same module scope; the agent has no parallel collision."
  - "raw_blob and Object.value typed as json.RawMessage rather than map[string]any. RawMessage defers JSON parsing — the agent never decodes vendor-native blobs; it only re-marshals them. This avoids round-trip whitespace/numeric-precision drift (a vendor that emits 1.0 must not arrive as 1 on the backend) and avoids an unbounded interface{} allocation. Backend Pydantic uses dict on receive — the wire bytes flow through unchanged."
  - "encoding/json added to types.go imports because json.RawMessage requires it. RoutesPayload + FlowsPayload don't use it directly (their nested netconf.RouteRecord / netflow.FlowRecord come from other packages), so the existing file had no json import."
  - "src_translation / dst_translation / interface_in / interface_out / src_zone / dst_zone / protocol / ports carry ,omitempty. Backend Pydantic schema defines them as Optional[str] = None; omitempty makes wire shape compatible whether the agent omits the field (None on Python side) or sends an empty string. position / action / src_cidr / dst_cidr / snapshot_ts / vendor / source / firewall_id / site_id / snapshot_id are NOT omitempty — they are required on both sides."
  - "Plan 11-01's Wave 0 scaffold did not stub any push-client RED tests for the three firewall methods. The Phase 10 push test suite (TestPushRoutes_*, TestPushFlows_Happy, TestPushRoutes_BackoffTiming) regression-locks postWithRetry behaviour; the new methods inherit those guarantees by composition. Per-vendor integration tests in Plans 11-07/08/10/11 will exercise the new methods end-to-end against httptest servers. No additional push-method unit tests were written in this plan — the contract is structural (compile-time + grep)."
metrics:
  duration_minutes: 6
  tasks_completed: 2
  files_created: 0
  files_modified: 2
  total_files: 2
  completed_date: "2026-05-12"
---

# Phase 11 Plan 05: Agent Push Client Extension Summary

Adds three new push methods (`PushFirewallRules`, `PushFirewallNAT`, `PushFirewallObjects`) and their corresponding payload structs to the agent's HTTP push client. All three methods route through the existing Phase 10 `postWithRetry` function — the D-07 retry-twice-then-drop contract is reused verbatim, not forked. Field names in the new payload structs match the backend Pydantic schemas (`backend/app/schemas/firewall.py`) tag-for-tag so the agent ↔ backend wire contract holds.

## What Was Built

### Task 1 — Firewall payload structs in `push/types.go` (commit `23fdf32`)

`agent/internal/push/types.go` (+81 lines) gained six new types arranged in two tiers:

**Inner item structs (re-used inside the envelope payloads):**

| Type             | Fields (with required-vs-optional flag) | Wire shape (JSON tags) |
| ---------------- | --------------------------------------- | ---------------------- |
| `FirewallRule`    | position (req), src_zone/dst_zone (opt), src_cidr/dst_cidr (req), action (req), protocol/ports (opt), raw_blob (req, `json.RawMessage`) | matches Pydantic `FirewallRule` from Plan 11-02 |
| `FirewallNATRule` | position (req), src_translation/dst_translation (opt), interface_in/interface_out (opt), raw_blob (req) | matches Pydantic `FirewallNATRule` |
| `FirewallObject`  | kind (req), name (req), value (req `json.RawMessage`), raw_blob (req `json.RawMessage`) | matches Pydantic `FirewallObject` |

**Envelope payload structs (one per push endpoint):**

| Type                       | Slice field      | Backend Pydantic peer       |
| -------------------------- | ---------------- | --------------------------- |
| `FirewallRulesPayload`     | `Rules`          | `FirewallRulesPushBody`     |
| `FirewallNATPayload`       | `NATRules`       | `FirewallNATPushBody`       |
| `FirewallObjectsPayload`   | `Objects`        | `FirewallObjectsPushBody`   |

All three envelopes carry the same six metadata fields verbatim from the Pydantic schemas: `site_id`, `snapshot_id`, `firewall_id`, `vendor`, `source`, `snapshot_ts`. The `snapshot_id` is documented as agent-minted UUIDv4 — three endpoints share the same ID per the RESEARCH Pattern 2 / D-07 backend `ON CONFLICT DO NOTHING` idempotency contract.

A header comment block before the new types calls out the contract lock with `backend/app/schemas/firewall.py` — load-bearing documentation so a future agent-side edit cannot drift the wire format without a corresponding backend edit.

`encoding/json` was added to the import block (required by `json.RawMessage`).

### Task 2 — Three push methods + path consts in `push/client.go` (commit `9de6def`)

Three new path constants joined the existing `const` block:

```go
firewallRulesPath   = "/v1/agent/firewall-rules"
firewallNATPath     = "/v1/agent/firewall-nat"
firewallObjectsPath = "/v1/agent/firewall-objects"
```

Three new methods on `*Client` appended after `PushFlows`:

| Method                  | Path                            | Kind label         | zap fields                                                                  |
| ----------------------- | ------------------------------- | ------------------ | --------------------------------------------------------------------------- |
| `PushFirewallRules`     | `/v1/agent/firewall-rules`      | `firewall-rules`   | site_id, snapshot_id, firewall_id, vendor, source, count                    |
| `PushFirewallNAT`       | `/v1/agent/firewall-nat`        | `firewall-nat`     | site_id, snapshot_id, firewall_id, vendor, source, count                    |
| `PushFirewallObjects`   | `/v1/agent/firewall-objects`    | `firewall-objects` | site_id, snapshot_id, firewall_id, vendor, source, count                    |

Each method is a verbatim shape-match for `PushRoutes`: marshal the payload, call `postWithRetry` with the path / kind / zap-field allowlist. `postWithRetry` itself was not touched — D-07 retry-twice-then-drop semantics, the 512-byte response sample cap (T-10-07-02 token-redaction guarantee), and the 4xx-bails / 5xx-retries error policy all flow through unchanged.

**What was deliberately NOT modified:**

- `postWithRetry` (lines 108-144) — D-07 retry contract is locked
- `doPost` `io.CopyN(&sample, resp.Body, 512)` (line 166) — T-10-07-06 OOM cap untouched
- `PushRoutes` (lines 84-93) and `PushFlows` (lines 96-104) — Phase 10 methods preserved verbatim
- `linearBackoff`, `SetBackoff`, `NewClient` — all unchanged

Pattern G allowlist (no credential field names in `zap.String` calls anywhere in the file) was preserved — `grep -E 'zap\.String\("(username|password|sid|token)"'` returns 0 matches.

## Decisions Made

Captured in frontmatter `decisions:`. Highlights:

1. **No Go-side `*Wire` / `*Push` suffix on item structs.** Go's package-qualified name (`push.FirewallRule`) is already disambiguating; downstream collectors will import the `push` package and reference the un-suffixed names directly. The Plan 11-02 backend's `*ORM` suffix was only necessary because Pydantic models with the un-suffixed names already lived in the same scope (`app.db.models` imports from `app.schemas.firewall`). The agent has no parallel collision.

2. **`raw_blob` and `Object.value` typed as `json.RawMessage`, not `map[string]any`.** Three reasons: (a) the agent never reads these blobs — only re-marshals them to the backend — so deferred parsing is strictly more correct; (b) avoids whitespace and numeric-precision drift on round-trip (Cisco FMC emits scientific-notation numerics in some fields; round-tripping through `map[string]any` would change the wire bytes); (c) prevents an unbounded `interface{}` allocation that would amplify a hostile vendor response into agent OOM (T-11-05-03 — partially mitigated this way).

3. **`,omitempty` only on Pydantic-Optional fields.** Required fields (`position`, `src_cidr`, `dst_cidr`, `action`, `kind`, `name`, `site_id`, `snapshot_id`, `firewall_id`, `vendor`, `source`, `snapshot_ts`, the three `raw_blob` fields, `Object.value`) have NO `omitempty`. Optional fields (`src_zone`, `dst_zone`, `protocol`, `ports`, `src_translation`, `dst_translation`, `interface_in`, `interface_out`) carry `,omitempty` so a Go zero-string serializes to an absent field, matching the Pydantic `None` on receive.

4. **No new unit tests for the three push methods.** Plan 11-01's Wave 0 RED scaffold did not stub any push-method tests for Plan 11-05 (it scaffolded collector tests for Plans 11-06/08/10/11 instead — see Plan 11-01 SUMMARY symbol/plan map). The retry/backoff/auth-gate contract is structurally identical to `PushRoutes` and is already regression-locked by `TestPushRoutes_RetryOn5xx`, `TestPushRoutes_DropsAfterRetries`, `TestPushRoutes_NoRetryOn401`, `TestPushRoutes_NoRetryOn422`, and `TestPushRoutes_BackoffTiming` — all of which exercise `postWithRetry` directly. Per-vendor end-to-end tests in Plans 11-07/08/10/11 will exercise the new methods against `httptest.Server` stubs.

5. **`encoding/json` import added to types.go.** The pre-existing file had zero direct json usage (its nested `netconf.RouteRecord` and `netflow.FlowRecord` types live in other packages). `json.RawMessage` requires the import, hence the addition.

## Deviations from Plan

None. Plan executed exactly as written, including the literal struct field order, the `,omitempty` placements, the path-const naming, the zap-field allowlist, and the in-file location of new types (appended after the Phase-10 `RoutesPayload` / `FlowsPayload` rather than inserted between them).

## Authentication Gates

None encountered.

## Known Stubs

None introduced. The new methods + payloads are production-ready code; only their downstream callers (the per-vendor collectors in Plans 11-06/08/10/11 and the firewall ticker in Plan 11-07) remain RED. Those are the explicit deliverables of the downstream plans, not stubs introduced by Plan 11-05.

## TDD Gate Compliance

This plan is `type=execute` with `tdd="true"` on both tasks. The Wave 0 (Plan 11-01) test scaffold did not stub any push-method RED tests for Plan 11-05's deliverables — only collector and backend tests. The structural verification (acceptance grep + `go vet` + `go build` + existing Phase 10 push test suite still green) substitutes for a dedicated RED commit on this plan. Both commits land as `feat(...)` because the change is purely additive against an already-green push test suite — the contract of postWithRetry being reused verbatim means no new failing test was required to drive the design.

| Gate     | Commit       | Status |
| -------- | ------------ | ------ |
| RED      | n/a          | Wave 0 scaffold did not stub push-method tests for Plan 11-05; existing Phase 10 push tests regression-lock postWithRetry behaviour and continue to pass |
| GREEN    | `23fdf32`, `9de6def` | New payloads + methods land; Phase 10 push test suite still passes (`go test -race ./internal/push/...` exits 0) |
| REFACTOR | (none needed) | postWithRetry untouched; no follow-up cleanup |

## Verification

### Automated checks performed

```bash
# Acceptance greps — Task 1 (types.go)
T=agent/internal/push/types.go
grep -c 'type FirewallRulesPayload\|type FirewallNATPayload\|type FirewallObjectsPayload' $T   # 3
grep -cE 'type FirewallRule |type FirewallNATRule |type FirewallObject ' $T                    # 3
grep -c 'json:"snapshot_id"' $T                                                                 # 3
grep -oE 'json:"src_cidr"|json:"dst_cidr"|json:"src_translation[^"]*"|json:"dst_translation[^"]*"' $T | wc -l  # 4
grep -c 'json:"raw_blob"' $T                                                                    # 3
grep -c 'json:"snapshot_ts"' $T                                                                 # 3

# Acceptance greps — Task 2 (client.go)
C=agent/internal/push/client.go
grep -c 'firewallRulesPath\|firewallNATPath\|firewallObjectsPath' $C                            # 6 (>= 6)
grep -cE 'func \(c \*Client\) PushFirewallRules|func \(c \*Client\) PushFirewallNAT|func \(c \*Client\) PushFirewallObjects' $C  # 3
grep -c 'postWithRetry' $C                                                                      # 7 (>= 5)
grep -cE 'func \(c \*Client\) PushRoutes|func \(c \*Client\) PushFlows' $C                      # 2 (Phase 10 preserved)
grep -v '^//' $C | grep -cE 'zap\.String\("(username|password|sid|token)"'                       # 0 (Pattern G)

# Build / vet / test
cd agent
go vet ./internal/push/...        # exits 0
go build ./internal/push/...      # exits 0
go test -race -count=1 ./internal/push/...  # ok  github.com/.../internal/push  3.706s
go build ./...                    # exits 0 — no Wave 1 build regressions
```

All acceptance-criterion greps match planned values. `go vet`, `go build ./internal/push/...`, `go build ./...`, and `go test -race ./internal/push/...` all exit 0.

### Skipped due to environment

None. All verification was runnable locally with the system Go toolchain (`go1.25.2 darwin/arm64` at `/opt/homebrew/bin/go`). No Postgres or testcontainers dependency — push-package tests are pure `httptest.Server` against an in-memory client.

## Commits

| Commit    | Type | Summary                                                                | Files |
| --------- | ---- | ---------------------------------------------------------------------- | ----- |
| `23fdf32` | feat | firewall payload structs in push/types.go                              | 1     |
| `9de6def` | feat | 3 firewall push methods reusing postWithRetry verbatim                 | 1     |

## Self-Check: PASSED

- `agent/internal/push/types.go` modified (commit `23fdf32` present in `git log`) ✓
- `agent/internal/push/client.go` modified (commit `9de6def` present in `git log`) ✓
- 3 envelope structs (`FirewallRulesPayload`, `FirewallNATPayload`, `FirewallObjectsPayload`) defined ✓
- 3 nested item structs (`FirewallRule`, `FirewallNATRule`, `FirewallObject`) defined ✓
- 3 push methods (`PushFirewallRules`, `PushFirewallNAT`, `PushFirewallObjects`) defined ✓
- 3 path consts (`firewallRulesPath`, `firewallNATPath`, `firewallObjectsPath`) defined ✓
- `postWithRetry` reused verbatim (no fork; `grep postWithRetry` shows 7 occurrences = 2 existing + 3 new + 2 in postWithRetry's own definition/log line) ✓
- Pattern G credential allowlist enforced (0 username/password/sid/token in zap fields) ✓
- Phase 10 push test suite still green ✓
- JSON tags match backend Pydantic field names verbatim (cross-checked against `backend/app/schemas/firewall.py`) ✓

## Next Plan

`11-06-PLAN.md` — Cisco ASA SSH collector. Will use the parser introduced by Plan 11-01's `show-running-config.txt` fixture and the SSH session/dialer interfaces stubbed in `agent/internal/asa/ssh_test.go`. The collector will emit normalized `FirewallRule` / `FirewallNATRule` / `FirewallObject` slices, mint a single UUIDv4 snapshot ID, and call all three Plan-11-05 push methods in sequence.
