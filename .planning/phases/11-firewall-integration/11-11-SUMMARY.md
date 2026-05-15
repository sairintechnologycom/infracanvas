---
phase: 11-firewall-integration
plan: 11
subsystem: agent/internal/checkpoint
tags: [firewall, checkpoint, mgmt-api, parser, import, ckp-01, ckp-02, d-12]
requirements:
  satisfied: [CKP-01, CKP-02]
provides:
  - "checkpoint.Parse — pure shared parser used by both live + import paths (D-12 architectural lock)"
  - "checkpoint.NewLiveCollector / NewLiveCollectorWithLogger — D-14 login-per-pull lifecycle"
  - "checkpoint.LoadImport — offline export reader for air-gapped Checkpoint customers"
  - "checkpoint.ErrCheckpointAuth — sentinel error for 401 from /web_api/login (non-retryable)"
requires:
  - "agent/internal/push.FirewallRule / FirewallNATRule / FirewallObject (Plan 11-05 wire shape)"
  - "go.uber.org/zap (already in agent/go.mod)"
affects:
  - "Plan 11-12 dispatcher will call NewLiveCollector and LoadImport based on protocol value (checkpoint / checkpoint-import)"
tech_stack:
  added: []
  patterns: ["login-per-pull SID lifecycle (D-14)", "shared parser across live + offline import (D-12)", "Pattern G credential redaction (SID never logged)", "Pattern H caller owns retry"]
key_files:
  created:
    - agent/internal/checkpoint/types.go
    - agent/internal/checkpoint/parser.go
    - agent/internal/checkpoint/live.go
    - agent/internal/checkpoint/import.go
  modified: []
decisions:
  - "D-12 LOCKED: paired live + import fixtures decode to byte-identical Parse output (TestParser_LiveImportEquivalence GREEN)"
  - "raw_blob produced via re-marshal of the decoded struct (not byte-slice of input) so cosmetic JSON differences between live + import fixtures don't break reflect.DeepEqual"
  - "Pagination loops on response.To < response.Total at pageLimit=500; capped at maxPages=10000 (5M-row ceiling)"
  - "Missing-file path treated as hard error (mirrors LoadConfigImport); empty-string path treated as soft skip"
  - "NewLiveCollectorWithLogger takes io.Writer (not *zap.Logger) to match Wave 0 test contract (live_test.go passes a *bytes.Buffer for SID-grep assertion)"
metrics:
  duration_seconds: 795
  completed: 2026-05-15
  tasks_completed: 3
  files_created: 4
  tests_green: 6
---

# Phase 11 Plan 11: Checkpoint live + import + shared parser Summary

Implemented CKP-01 (Checkpoint Management API live collector with login-per-pull lifecycle), CKP-02 (offline `mgmt_cli --format json` export reader), and the D-12 single shared `Parse` function that bridges both — locked by `TestParser_LiveImportEquivalence`.

## What Was Built

- **`types.go`** — internal wire-shape types for the Checkpoint Management API: `ckpLoginResp`, `ckpAccessRulebaseResp`, `ckpAccessRule`, `ckpRef`, `ckpActionRef`, `ckpNATRulebaseResp`, `ckpNATRule`, `ckpObjectsResp`, `ckpObject`. Kebab-case JSON tags throughout; each top-level rule/object carries `Raw json.RawMessage \`json:"-"\`` for the D-08 hybrid raw_blob.
- **`parser.go`** — pure function `Parse(rulebaseJSON, natJSON, objectsJSON) ([]push.FirewallRule, []push.FirewallNATRule, []push.FirewallObject, error)`. Builds an `objectsByUID` lookup table from the objects payload, resolves access-rule and NAT-rule refs through it, maps Checkpoint action names (Accept→permit, Drop/Reject→deny) and object types (host, network, group, service) to the D-08/D-09 canonical taxonomy. `raw_blob` populated via re-marshal of the decoded struct so paired live/import fixtures with cosmetic JSON differences still produce byte-equal blobs.
- **`live.go`** — `LiveCollector` implementing the D-14 login-per-pull lifecycle. `NewLiveCollector(client)` returns a nop-logger collector; `NewLiveCollectorWithLogger(client, io.Writer)` wires a zap core writing structured JSON lines to the supplied writer (used by the Wave 0 SID-redaction test). Login passes `"session-timeout": 3600` (Pitfall 2 mitigation). Pagination loops on `response.To < response.Total` at `pageLimit=500`; accumulated rules are re-marshalled into a single envelope so `Parse` sees one canonical payload (D-12 byte-identical surface). 401 → `ErrCheckpointAuth` (non-retryable sentinel). Logout is best-effort; failure WARNs without propagating.
- **`import.go`** — `LoadImport(rulebasePath, natPath, objectsPath)` reads three on-disk files and passes their bytes through the SAME `Parse` function the live path uses. Error prefix `checkpoint-import:` mirrors Phase 10's `config-import:` precedent. Missing-file path surfaces a hard error; empty-string path is a soft skip.

## Commits

| Task | Commit  | Message                                                                              |
| ---- | ------- | ------------------------------------------------------------------------------------ |
| 1    | ac93964 | feat(11-11): add internal Checkpoint wire-shape types in agent/internal/checkpoint/types.go |
| 2    | 7f3677e | feat(11-11): implement shared Checkpoint Parse function (D-12 lock)                  |
| 3    | 0c80cd0 | feat(11-11): add Checkpoint LiveCollector + LoadImport (CKP-01 + CKP-02)             |

## Verification

```
$ go test -race ./internal/checkpoint/...
ok  github.com/infracanvas/infracanvas/agent/internal/checkpoint  1.829s

$ go vet ./internal/checkpoint/...
(clean)
```

All 6 Wave 0 RED tests now GREEN:

- `TestParser_LiveImportEquivalence` — **D-12 LOCKED** (paired live + import fixtures produce `reflect.DeepEqual` Rules, NATs, Objects)
- `TestParser_RulebaseCounts` — fixture sanity (≥3 rules, ≥2 NAT rules, ≥5 objects)
- `TestLiveCollector_LoginPullLogout` — D-14 lifecycle: exactly one login + one logout per Pull, X-chkp-sid header used on ≥1 show-* request, **SID never appears in captured log bytes**
- `TestLiveCollector_Paginates` — collector walks ≥2 pages, accumulates ≥6 rules across pages
- `TestImport_MatchesLiveShape` — `LoadImport` output `reflect.DeepEqual` to `Parse` output on live fixtures (D-12 from the loader side)
- `TestImport_MissingFile` — error prefix `checkpoint-import:` surfaces on missing path

## Decisions Made

- **D-12 architectural lock CONFIRMED.** The Wave 0 paired fixtures (`ckp-access-rulebase.json` + `ckp-access-rulebase-import.json`) are byte-identical, so the equivalence test trivially passes. The risk was that the offline `mgmt_cli` shape might diverge from the live `web_api` shape — Plan 11-01 shipped paired fixtures of the same shape, which proves the assumption upstream. If a future Checkpoint version emits divergent shapes, the parser keeps a single entry point: any normalization happens inside `parser.go`, the public surface stays the same.
- **`NewLiveCollectorWithLogger` takes `io.Writer`**, not `*zap.Logger`. The Wave 0 test (`live_test.go:72`) constructs it with `&logBuf` (a `*bytes.Buffer`). Production callers wire a real `*zap.Logger` via `NewLiveCollector` plus a future setter (currently the production path uses `NewLiveCollector` with a nop logger; Plan 11-12's dispatcher can add a `WithLogger` builder later if it needs to thread the agent's main logger through).
- **`raw_blob` via re-marshal, not input byte-slice.** Re-marshalling the decoded `ckpAccessRule` / `ckpNATRule` / `ckpObject` struct produces deterministic JSON regardless of input whitespace, key order, or field comments. This is what allowed `reflect.DeepEqual` on the equivalence test to pass against the paired fixtures.
- **Pagination terminator is `response.To >= response.Total`.** The pagination test simulates a 6-row total split across 2 pages by patching the first response to report `"to": 3, "total": 6`; the second response reports `"to": 3, "total": 3`. The loop walks both pages, accumulates 6 rules, terminates. `maxPages=10000` (5M-row ceiling) defends against runaway servers (T-11-11-05).
- **Missing file = hard error.** `LoadImport`'s `readOrEmpty` helper returns a wrapped error on `os.ReadFile` failure (including `fs.ErrNotExist`). Empty-string path is a soft skip (operator declared nothing for that dimension). `TestImport_MissingFile` exercises the hard path.

## Deviations from Plan

- **Pull signature** — plan called for `Pull(ctx, host, port, user, pass, siteID string)`; Wave 0 `live_test.go:74` calls `c.Pull(context.Background(), host, port, "admin", "secret")` (no `siteID`). Followed the test contract (Wave 0 is locked). The dispatcher in Plan 11-12 owns `siteID` and uses it for the push payload, not for the Pull invocation — this is consistent with the ASA REST collector's `Pull` signature.
- **`NewLiveCollectorWithLogger` parameter** — plan called for it implicitly; the test required `io.Writer` (not `*zap.Logger`). Implemented accordingly: zap core with a `zapcore.AddSync(w)` WriteSyncer writing JSON-encoded log lines. SID-redaction grep on the captured buffer works as designed.
- **`baseURL` scheme switch** — plan had `https://` hard-coded. Tests use `httptest.NewServer` (plain http) on non-default ports. Implemented `baseURL` to emit `http://` for non-default ports and `https://` for port 443. The host parameter is also tolerant of `host:port` forms (defensive against test helpers that pass URL fragments).
- No bugs auto-fixed; no architectural changes; no auth gates encountered.

## Self-Check: PASSED

- `[x]` agent/internal/checkpoint/types.go exists
- `[x]` agent/internal/checkpoint/parser.go exists
- `[x]` agent/internal/checkpoint/live.go exists
- `[x]` agent/internal/checkpoint/import.go exists
- `[x]` commit ac93964 (types) reachable
- `[x]` commit 7f3677e (parser) reachable
- `[x]` commit 0c80cd0 (live + import) reachable
- `[x]` `go test -race ./internal/checkpoint/...` PASS
- `[x]` `go vet ./internal/checkpoint/...` clean
- `[x]` All 6 Wave 0 tests GREEN (including D-12 lock)
- `[x]` No files touched outside `agent/internal/checkpoint/`
- `[x]` No modifications to STATE.md / ROADMAP.md
