---
status: complete
phase: 11-firewall-integration
source:
  - 11-01-SUMMARY.md
  - 11-02-SUMMARY.md
  - 11-03-SUMMARY.md
  - 11-04-SUMMARY.md
  - 11-05-SUMMARY.md
  - 11-06-SUMMARY.md
  - 11-07-SUMMARY.md
  - 11-08-SUMMARY.md
  - 11-09-SUMMARY.md
  - 11-10-SUMMARY.md
  - 11-11-SUMMARY.md
  - 11-12-SUMMARY.md
  - 11-13-SUMMARY.md
started: 2026-05-15T12:11:16Z
updated: 2026-05-15T17:10:13Z
---

## Current Test

[testing complete]

## Tests

### 1. Cold Start Smoke Test
expected: Build and start the agent binary with a minimal agent.yaml (zero devices). All four tickers initialize (Routes/BGP/Flow/Firewall), daemon boots without panic, SIGTERM drains cleanly. Backend `alembic upgrade head` completes through `011_firewall_tables` without errors.
result: pass

### 2. agent.yaml protocol validation
expected: Adding a device with `protocol: asa-rest`, `asa-ssh`, `fmc`, `checkpoint`, or `checkpoint-import` is accepted by config loader. An unknown firewall protocol (e.g. `asa-restful`) fails validation with a clear error naming the bad protocol. `checkpoint-import` requires a `config_path` and rejects the config if missing.
result: pass

### 3. Backend push round-trip (firewall-rules)
expected: A `POST /v1/agent/firewall-rules` with a valid site_token Bearer and a payload of {snapshot_id, site_id, firewall_id, vendor, source, snapshot_ts, rules: [...]} returns 2xx. Re-posting the same payload (same snapshot_id) is idempotent — no duplicate parent row. DB has a `firewall_ruleset_snapshots` row plus the child `firewall_rules` rows under the caller's team_id.
result: pass

### 4. Backend read endpoint returns latest per device
expected: `GET /v1/sites/{site_id}/firewall-rules` with a Clerk JWT for the owning team returns the latest snapshot per firewall_id (D-11) with attached rules, nat_rules, and objects. `snapshot_ts` round-trips as RFC3339 with trailing `Z`. If two snapshots exist for the same firewall_id, only the newest is returned.
result: pass

### 5. Cross-team RLS isolation
expected: A Clerk JWT for Team B requesting `GET /v1/sites/{site_id}/firewall-rules` where `site_id` belongs to Team A returns 404 (not 403). The response body matches the existing site-not-found shape (mirrors `github.py:144-152`). No `firewall_ruleset_snapshots` scan happens — the site-membership probe short-circuits.
result: pass

### 6. Checkpoint live ↔ import parser equivalence
expected: Running the shared Checkpoint parser against a live API JSON response and against an offline `mgmt_cli show access-rulebase --format json` export of the same rule base produces byte-identical parser output (`reflect.DeepEqual` on Rules/NATs/Objects). Air-gapped customers using `checkpoint-import` see the same backend rows as live-API customers.
result: pass

### 7. CAB packet operator runbook coverage
expected: `agent/docs/cab/operator-runbook.md` has a Phase 11 section with Steps F1-F7 covering: agent.yaml shape for each of the 5 firewall protocols, how to generate the checkpoint-import JSON files (`mgmt_cli show ... --format json > path`), credential rotation procedure, and a troubleshooting matrix. `agent/docs/cab/threat-model.md` has Phase 11 T-11-NN-MM rows appended to the existing T-10-* register (additive, not replacing).
result: pass

## Summary

total: 7
passed: 7
issues: 0
pending: 0
skipped: 0

## Gaps

[none yet]
