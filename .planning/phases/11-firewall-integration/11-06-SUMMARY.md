---
phase: 11-firewall-integration
plan: 06
subsystem: agent/internal/config
tags: [agent, config, protocol-enum, validation, firewall, phase-11, wave-1]
requires:
  - phase-10/agent-config-loader
  - phase-10/config-import-precedent
provides:
  - protocol-enum/asa-rest
  - protocol-enum/asa-ssh
  - protocol-enum/fmc
  - protocol-enum/checkpoint
  - protocol-enum/checkpoint-import
  - validation/checkpoint-import-config-file-guard
  - validation/checkpoint-import-host-exemption
affects:
  - plan-11-07/main-loop-collector-dispatch
  - plan-11-08/asa-rest-collector
  - plan-11-09/asa-ssh-collector
  - plan-11-10/fmc-collector
  - plan-11-11/checkpoint-live-collector
  - plan-11-12/checkpoint-import-loader
tech-stack:
  added: []
  patterns:
    - "Phase 10 protocol-enum extension: const block + switch arm + per-protocol guard"
    - "config-import → checkpoint-import file-based protocol precedent (D-16, D-12)"
key-files:
  created: []
  modified:
    - agent/internal/config/config.go
    - agent/internal/config/config_test.go
decisions:
  - "D-16 strict: ZERO new fields on Device struct — checkpoint-import reuses ConfigFile (same as config-import); ASA REST/SSH/FMC/Checkpoint reuse Host/Port/Username/Password"
  - "checkpoint-import error message format pinned verbatim — `device[%d]: config_file required when protocol=checkpoint-import` (mirrors Phase 10 config-import wording so backend log-greps stay portable)"
  - "Host-exemption arm uses compound `!= ProtocolConfigImport && != ProtocolCheckpointImport` rather than a slice/loop — matches the existing 2-branch idiom and stays grep-friendly for the next file-based protocol to drop in"
  - "Const ordering: file protocols (config-import, checkpoint-import) grouped semantically with their network siblings (asa-*, fmc, checkpoint) under a single Phase 11 comment band — keeps the test that locks string values (`TestValidate_FirewallProtocolConsts_Values`) on one declaration block"
metrics:
  duration: "~2 minutes"
  completed: "2026-05-12T07:25:22Z"
  commits: 2
  tasks: 1
  files-modified: 2
  tests-added: 2 (11 sub-cases)
  tests-passing: "all 16 config tests green (`go test -race ./internal/config/...`)"
---

# Phase 11 Plan 06: Firewall Protocol Enum Extension Summary

**One-liner:** Extend `agent/internal/config/config.go` with the 5 firewall protocols (`asa-rest`, `asa-ssh`, `fmc`, `checkpoint`, `checkpoint-import`) and add a `checkpoint-import` file-based guard pair that mirrors the Phase 10 `config-import` precedent — ZERO new fields on the Device struct (D-16).

## What Landed

Two atomic commits on `dev/local-no-auth`, in TDD order:

| Commit    | Type   | Files                                       | Net Lines | Role             |
| --------- | ------ | ------------------------------------------- | --------- | ---------------- |
| `a4d43c1` | `test` | `agent/internal/config/config_test.go`      | +86       | RED              |
| `0bc6822` | `feat` | `agent/internal/config/config.go`           | +15 / -2  | GREEN            |

No `refactor` commit — the GREEN implementation is already at the minimal shape (5 const decls + 5 case-statement tokens + 1 new guard + 1 amended guard).

### `agent/internal/config/config.go` (+15 / -2)

1. **5 new protocol consts** appended to the existing `const ( ... )` block under a Phase 11 comment band citing D-16, D-04, D-05, D-12:
   ```go
   ProtocolASARest          = "asa-rest"
   ProtocolASASSH           = "asa-ssh"
   ProtocolFMC              = "fmc"
   ProtocolCheckpoint       = "checkpoint"
   ProtocolCheckpointImport = "checkpoint-import"
   ```
2. **Validation switch arm extended** with the 5 new const tokens — default branch unchanged so unknown protocols still fail loud at config-load time (T-11-06-01 mitigation: agent exits before any goroutine starts).
3. **New `checkpoint-import` config_file guard** mirroring the existing `config-import` guard tag-for-tag:
   ```go
   if d.Protocol == ProtocolCheckpointImport && d.ConfigFile == "" {
       return fmt.Errorf("device[%d]: config_file required when protocol=checkpoint-import", i)
   }
   ```
4. **Host-required guard extended** with a second exemption arm so file-based imports don't trip on the host check (compound `!= ProtocolConfigImport && != ProtocolCheckpointImport`).

### `agent/internal/config/config_test.go` (+86)

Two new tests, both following the project's existing `testify/require` style:

- **`TestValidate_AcceptsFirewallProtocols`** — 10 parameterized sub-cases:
  - 5 positive: each new protocol accepts a well-formed entry (the 4 network protocols with a `host`; `checkpoint-import` with `config_file` and NO host).
  - 1 negative: `checkpoint-import` without `config_file` triggers the new guard with the exact `config_file required when protocol=checkpoint-import` message.
  - 4 negative: each network firewall protocol (`asa-rest`, `asa-ssh`, `fmc`, `checkpoint`) still fails with `host required when protocol=<p>` when host is empty, regression-locking the host-exemption to file-based protocols only.
- **`TestValidate_FirewallProtocolConsts_Values`** — asserts the 5 const values match the agent.yaml strings operators declare verbatim, decoupling a future const-rename from the wire contract.

The pre-existing 9 Phase 10 config tests are untouched and still green.

## Deviations from Plan

**None.** The plan was executed exactly as written:
- `<action>` step 1 (const block extension): verbatim.
- `<action>` step 2 (switch-arm extension): verbatim.
- `<action>` step 3 (config_file guard for checkpoint-import): verbatim — exact error message format preserved.
- `<action>` step 4 (compound host-exemption): verbatim.
- `<action>` step 5 (test addition): expanded slightly — the plan suggested a 7-row table; the executor used a named-subtest pattern (`t.Run`) with 10 cases for clearer test output. Same coverage scope, no scope drift.
- D-16 (zero new Device fields): respected — Device struct field count grep returns exactly 7 (Host, Port, Protocol, Username, Password, ConfigFile, SiteID).

## Verification Evidence

All acceptance criteria from the plan executed and matched exactly:

| Acceptance check                                                                                              | Expected | Actual |
| ------------------------------------------------------------------------------------------------------------- | -------- | ------ |
| `grep -c 'ProtocolASARest\b\|ProtocolASASSH\b\|ProtocolFMC\b\|ProtocolCheckpoint\b\|ProtocolCheckpointImport\b' config.go` | ≥ 10     | 10     |
| `grep -c '"asa-rest"\|"asa-ssh"\|"fmc"\|"checkpoint"\|"checkpoint-import"' config.go`                         | == 5     | 5      |
| `grep -c 'config_file required when protocol=checkpoint-import' config.go`                                    | == 1     | 1      |
| `grep -c 'host required when protocol' config.go`                                                             | == 1     | 1      |
| `grep -c 'd.Protocol != ProtocolConfigImport && d.Protocol != ProtocolCheckpointImport' config.go`            | == 1     | 1      |
| `grep -c 'type Device struct' config.go`                                                                       | == 1     | 1      |
| Device-struct field count (D-16)                                                                              | ≤ 7      | 7      |

Test commands run and outcomes:

```
$ go vet ./internal/config/...                                  # clean
$ go test -race ./internal/config/...                           # ok 1.748s
$ go test -race -v -run TestValidate_AcceptsFirewallProtocols   # 10/10 PASS
$ go test -race -v -run TestValidate_FirewallProtocolConsts_Values  # 1/1 PASS
$ go build ./...                                                # clean (no cascading breakage)
```

## TDD Gate Compliance

- **RED:** `a4d43c1` — 2 test functions added; package fails to compile with 5 `undefined: Protocol*` errors. RED gate satisfied.
- **GREEN:** `0bc6822` — minimal implementation: 5 const decls + 5-token switch arm + 1 new guard + 1 amended guard. All 11 new sub-tests + 9 preserved Phase 10 tests pass.
- **REFACTOR:** not needed — implementation is already at the minimal shape.

Gate sequence in `git log`:
```
0bc6822 feat(11-06): ...    ← GREEN
a4d43c1 test(11-06): ...    ← RED
```

## Threat Surface Scan

No new external surface introduced. The plan's `<threat_model>` covers exactly what this commit adds:

- **T-11-06-01 (Tampering — operator misconfigures protocol → agent crashes):** mitigated by the extended switch arm — the default branch returns `device[%d]: invalid protocol: %s` at config-load time so the agent exits before any goroutine starts.
- **T-11-06-02 (Information Disclosure — crafted config_file path):** accept-posture inherited from Phase 10 `ProtocolConfigImport` — operator-controlled config, `chmod 600 agent.yaml` is the trust boundary. Plan 11-11 / 11-12 implement the loader and apply the same `os.ReadFile` discipline.

No new threat-register entries needed beyond what the plan declared.

## Forward Feed for Downstream Plans

Plans that consume these consts:
- **11-07** (`agent/cmd/infracanvas-agent/main.go` ticker + collector dispatch) — adds `case config.ProtocolASARest:`, etc. in `firewallCollectorFor`.
- **11-08..11-11** (`agent/internal/{asa,fmc,checkpoint}/` collectors) — import the consts when wiring their `Pull` entry points.
- **11-12** (`agent/internal/checkpoint/import.go`) — exercised under `ProtocolCheckpointImport` in the hermetic main-loop test (Pattern I: hermetic file-read protocol).

The wire contract is now locked: operators can write `protocol: asa-rest` (etc.) in `agent.yaml` today and the loader will accept the structure even before the collectors land — devices simply won't be polled until 11-07 wires the 4th ticker.

## Self-Check: PASSED

- `agent/internal/config/config.go` — modified, contains all 5 new consts and both guards (verified by grep counts above).
- `agent/internal/config/config_test.go` — modified, contains both new test functions (verified — 11 sub-cases pass).
- Commit `a4d43c1` exists on `dev/local-no-auth` (RED).
- Commit `0bc6822` exists on `dev/local-no-auth` (GREEN).
- `go test -race ./internal/config/...` exits 0.
- `go build ./...` exits 0.

---

*Plan: 11-06 — Firewall Protocol Enum Extension*
*Completed: 2026-05-12*
*Wave: 1 (along with 11-02 ✅ and 11-05 ✅)*
*Phase 11 progress after this plan: 4/13 plans complete (11-01, 11-02, 11-05, 11-06)*
