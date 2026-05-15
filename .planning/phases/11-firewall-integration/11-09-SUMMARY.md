---
phase: 11-firewall-integration
plan: 09
subsystem: agent/asa-ssh
tags: [asa, ssh, parser, firewall, collector, wave-3]
dependency_graph:
  requires:
    - "11-01: Wave 0 RED ssh_test.go + testdata/show-running-config.txt"
    - "11-05: agent.yaml schema with asa-ssh protocol token"
    - "11-07: 4th-ticker firewall scaffold in agent main loop"
    - "11-08: ASA REST collector + internal types.go + ssh_stub.go compile shim"
    - "Phase 10: agent/internal/ssh package (Dialer/Session pattern, DefaultDialer with InsecureIgnoreHostKey + PTY ECHO=0)"
  provides:
    - "agent/internal/asa.SSHCollector — Pull(ctx, host, port, user, pass) over SSH (ASA-03)"
    - "agent/internal/asa.ParseRunningConfig — pure-function ASA show-running-config parser"
    - "agent/internal/asa.SSHSession / SSHDialer — local test-seam interfaces"
  affects:
    - "agent main.go dispatcher (Plan 11-12): can now route protocol: asa-ssh devices to asa.SSHCollector.Pull"
tech-stack:
  added:
    - "go.uber.org/zap (already in go.mod) — INFO-level pull-complete logging on SSHCollector"
  patterns:
    - "Linear-time regex parser (Phase 10 ssh/parser.go inheritance)"
    - "Dialer/Session test-seam (Phase 10 ssh/collector.go inheritance, declared local to asa package per Wave 0 contract)"
    - "Pattern G — log only host + counts, never user/pass"
    - "Pattern H — Pull takes primitives, not config.Device, to break import cycle"
key-files:
  created:
    - "agent/internal/asa/ssh_parser.go (340 lines): ParseRunningConfig + 7 compiled regexes + helpers"
    - "agent/internal/asa/ssh.go (175 lines): SSHCollector + Pull + default dialer adapter"
  modified: []
  deleted:
    - "agent/internal/asa/ssh_stub.go (62 lines): Plan 11-08 compile shim, handed off as planned"
decisions:
  - "Local SSHSession/SSHDialer interfaces — kept the Wave 0 locked names instead of importing xssh.Session/Dialer directly, because ssh_test.go's fakeDialer.Dial returns SSHSession (the local nominal type) and Go's nominal type system would have rejected a swap to xssh.Session. Adapter (xsshSessionAdapter) bridges to the production xssh.DefaultDialer at the single defaultSSHDialer.Dial seam — Phase 10 transport security still has exactly one source of truth."
  - "Parser name = ParseRunningConfig (NOT ParseShowRunningConfig as the plan body proposed) — Wave 0 ssh_test.go and ssh_stub.go both reference ParseRunningConfig; renaming would have broken the locked Wave 0 contract."
  - "NewSSHCollector(d) — single argument, NOT (d, log) — locked by Wave 0 test signature. Logger wired via fluent SetLogger() setter instead; main.go dispatcher will call NewSSHCollector(nil).SetLogger(log) for production."
  - "Pull(ctx, host, port, user, pass) — 5 args (no siteID) and 4 returns (rules, nats, objs, error) — locked by Wave 0 test signature. SiteID is held by the caller (firewall ticker in 11-07) and stamped onto the push payload after Pull returns."
  - "raw_blob shape = {\"line\": \"<original config line>\"} JSON for rules/nats and {\"line\", \"name\", \"block\", \"values\"} for objects — single-line ACL/NAT entries naturally serialize to a single original-line blob; multi-line object blocks capture the full block context. D-08 hybrid preserved on both."
  - "bufio.Scanner buffer bumped to 1 MiB (vs. default 64 KiB) — T-11-09-05 mitigation for pathologically long config lines without unbounded memory growth."
metrics:
  duration: "10 minutes"
  completed: "2026-05-15"
  tasks: 2
  files_changed: 3
  commits: 2
---

# Phase 11 Plan 09: ASA SSH Collector + Parser Summary

**ASA-03 implemented:** Cisco ASA running-config pulls over SSH, parsed into rules + NAT + objects with a pure-function regex parser; Wave 0 RED tests (`ssh_test.go`) flipped GREEN against real types.

## What Was Built

Two new files in `agent/internal/asa/`:

1. **`ssh_parser.go`** — `ParseRunningConfig(text)` pure function. Line-by-line `bufio.Scanner` over the ASA `show running-config` dump, seven compiled regexes (acl, nat, object-start, object-group-start, host, subnet, network-object), a small state machine for multi-line object blocks. Emits `push.FirewallRule` / `push.FirewallNATRule` / `push.FirewallObject` slices with `raw_blob` preserving the original config line (D-08 hybrid). Non-matching lines are silently dropped (T-10-05-03 inheritance). All regexes are bounded — no backreferences, no unbounded `.*` quantifiers.

2. **`ssh.go`** — `SSHCollector` wraps an injected `SSHDialer`. `Pull(ctx, host, port, user, pass)` dials once, issues `"terminal pager 0\nshow running-config"` in a single Run call, parses the result, and logs `asa_ssh_pull_complete` with host + counts only (Pattern G). Production callers get the Phase 10 transport security posture for free: when `d == nil`, the collector falls back to `defaultSSHDialer`, which adapts `xssh.DefaultDialer()` (InsecureIgnoreHostKey + ECHO=0 + PTY pager mitigation) to the local `SSHSession` interface.

`ssh_stub.go` — the Plan 11-08 compile shim — was deleted as the plan explicitly mandated. The Wave 0 test contract (`SSHSession`, `SSHDialer`, `NewSSHCollector`, `ParseRunningConfig`) is now backed by real implementations.

## Acceptance Status

- `cd agent && go build ./...` — clean (no broken imports anywhere in the module)
- `cd agent && go vet ./internal/asa/...` — clean
- `cd agent && go test -race ./internal/asa/...` — **GREEN** (`TestSSHCollector_DisablesPager` + `TestSSHParser_RealConfig` + the Plan 11-08 REST tests all pass under `-race`)
- Acceptance grep counts on `ssh.go`: `NewSSHCollector`=1, `type SSHCollector`=1, `Pull` method=1, `show running-config`=3 references (doc + code), `ParseRunningConfig` call sites=4 (doc + code), `asa-ssh:` error prefix=4, xssh import=1, `zap.String("user|pass|password"`=0 (Pattern G clean).
- Acceptance grep counts on `ssh_parser.go`: `ParseRunningConfig`=1 func decl, `regexp.MustCompile`=7, `bufio.NewScanner`=1, `(?P=` / `\1` / `\2` backreferences in non-comment code=0.

## Threat Model Compliance

All five `<threat_model>` rows from the plan are honored:

- **T-11-09-01 (Spoofing — SSH MITM):** `accept` — InsecureIgnoreHostKey inherited from `xssh.DefaultDialer` (CAB-documented Phase 10 posture). No new attack surface introduced by Plan 11-09.
- **T-11-09-02 (Information Disclosure — password via PTY echo):** `mitigate` — ECHO=0 set by underlying `xssh.DefaultDialer`. Pattern G enforced in `Pull` (only host + counts logged).
- **T-11-09-03 (DoS — adversarial running-config):** `mitigate` — all seven regexes in `ssh_parser.go` use bounded character classes (`\S+`, `\s+`, `[a-z]+`); no backreferences; non-matching lines silently skipped; verified by grep acceptance check.
- **T-11-09-04 (Tampering — crafted line injection):** `accept` — raw_blob preserves the original line text so downstream consumers see the actual config; misclassification surface is bounded by regex specificity.
- **T-11-09-05 (DoS — oversized running-config):** `mitigate` — `bufio.Scanner.Buffer(make([]byte, 0, 64*1024), 1024*1024)` lifts the per-line cap to 1 MiB.

## Deviations from Plan

### [Rule 3 — Blocking Issue] Honored Wave 0 locked symbol names over plan body

- **Found during:** Task 1 read-first phase (reading `ssh_test.go` and `ssh_stub.go`)
- **Issue:** Plan body proposed `ParseShowRunningConfig`, `NewSSHCollector(d, log)`, and `Pull(ctx, host, port, user, pass, siteID)`. The locked Wave 0 RED test (`ssh_test.go`, already on `feat(11-01)` commit) uses `ParseRunningConfig`, `NewSSHCollector(d)`, and `Pull(ctx, host, port, user, pass)` — different names and arities. Renaming would have left the test compiling against a different surface than the implementation.
- **Fix:** Implemented against the Wave 0 contract verbatim. Logger wired via a separate `SetLogger()` fluent setter so production callers can still attach a `*zap.Logger`. SiteID is the caller's responsibility (firewall ticker in Plan 11-07 already holds it and stamps the push payload).
- **Files modified:** `agent/internal/asa/ssh.go`, `agent/internal/asa/ssh_parser.go`
- **Commits:** `8a5deb6`, `4c05901`

### [Rule 3 — Blocking Issue] Local SSHSession / SSHDialer interfaces (vs. plan's "REUSE xssh package interfaces")

- **Found during:** Task 2 read-first phase (cross-checking `ssh_test.go` `fakeDialer` signature)
- **Issue:** Plan said "REUSE ssh package interfaces — DO NOT define new ones". But `ssh_test.go` declares `fakeDialer.Dial(...) (SSHSession, error)` returning the local nominal type. Go's nominal type system rejects passing `(xssh.Session, error)` where `(SSHSession, error)` is expected, and vice versa — even though the methodsets are identical. The Wave 0 locked contract is the local types.
- **Fix:** Kept the local `SSHSession` / `SSHDialer` interfaces (the same ones `ssh_stub.go` had) and added a single `xsshSessionAdapter` at the production-dialer boundary so the real `xssh.DefaultDialer()` transport security still flows through. The result is what the plan's *intent* asked for: **exactly one place** (Phase 10's `xssh` package) configures SSH security. There are now zero duplicated cryptossh / PTY / ECHO=0 / InsecureIgnoreHostKey call sites in the agent.
- **Files modified:** `agent/internal/asa/ssh.go`
- **Commits:** `4c05901`

## Out-of-Scope Failures Noted (not fixed)

`go test ./agent/...` shows build failures in `agent/internal/checkpoint` and `agent/internal/fmc` packages. These are Wave 0 RED test stubs for Plans 11-10 (FMC) and 11-11 (Checkpoint) — sibling Wave 3 plans whose implementations land in their own worktrees. Per parallel-execution scope boundary, Plan 11-09 does not touch them. Once Plans 11-10 and 11-11 merge into the wave, the full module will go GREEN.

## Self-Check: PASSED

- `agent/internal/asa/ssh_parser.go` — present (340 lines)
- `agent/internal/asa/ssh.go` — present (175 lines)
- `agent/internal/asa/ssh_stub.go` — deleted (confirmed `ls` returns "No such file")
- Commit `8a5deb6` (Task 1 — parser) — present in `git log`
- Commit `4c05901` (Task 2 — collector + stub deletion) — present in `git log`
- `go test -race ./internal/asa/...` — GREEN
- `go vet ./internal/asa/...` — exit 0
- `go build ./...` (full agent module) — exit 0
