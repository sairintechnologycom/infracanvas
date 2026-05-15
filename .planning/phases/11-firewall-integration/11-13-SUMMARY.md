---
phase: 11-firewall-integration
plan: 13
subsystem: agent/docs/cab
tags: [wave-5, cab, docs-only, autonomous-false, threat-model, dataflow, runbook, phase-closure]
requirements:
  satisfied: [ASA-01, ASA-02, ASA-03, CKP-01, CKP-02]   # documented in CAB; final smoke verifies end-to-end
requires:
  - phase-11-plan-01-summary  # Wave 0 test scaffold
  - phase-11-plan-02-summary  # Backend migration 011 + ORM + schemas + prune (T-11-02-*)
  - phase-11-plan-03-summary  # Push handlers (T-11-03-*)
  - phase-11-plan-04-summary  # Read endpoint (T-11-04-*)
  - phase-11-plan-05-summary  # Push client extensions (T-11-05-*)
  - phase-11-plan-06-summary  # Config validation (T-11-06-*)
  - phase-11-plan-07-summary  # 4th ticker + Pusher (T-11-07-*)
  - phase-11-plan-08-summary  # ASA REST collector (T-11-08-*)
  - phase-11-plan-09-summary  # ASA SSH collector (T-11-09-*)
  - phase-11-plan-10-summary  # FMC client (T-11-10-*)
  - phase-11-plan-11-summary  # Checkpoint live + import + shared parser (T-11-11-*)
  - phase-11-plan-12-summary  # Firewall dispatcher (T-11-12-*)
  - phase-10-summary           # CAB packet baseline (DCA-09) — Phase 11 extends, never replaces
provides:
  - "Extended CAB threat register with 49 T-11-NN-MM rows under TB-1 / TB-2 / TB-3"
  - "Phase 11 — Firewall Management Credential Storage section (5-point credential-storage charter from CONTEXT.md <specifics>)"
  - "Firewall data-flow diagram + 4th-ticker architecture documentation"
  - "Data Inventory extension covering rule-base / NAT / objects / SID / firewall mgmt creds (10 new rows)"
  - "Known-limitations rows L-11-01..L-11-05 surfacing all RESEARCH Pitfalls 1/2/6/7 + Risk Landmines 2/4 + Open Q3"
  - "Operator runbook Phase 11 section: agent.yaml shape × 5 protocols + checkpoint-import file generation + credential rotation + troubleshooting matrix"
affects:
  - "/gsd-verify-work 11 (final phase verification — smoke test pending)"
  - "STATE.md + ROADMAP.md (orchestrator-owned writes, NOT this plan)"
tech_stack:
  added: []   # docs-only; zero new dependencies, zero source-code changes
  patterns:
    - "EXTEND, do NOT replace — Phase 10 baseline preserved verbatim (43 T-10 rows untouched; existing TB tables / Steps 1-7 / L-1..L-7 unchanged)"
    - "Threat-ID convention T-PP-NN-MM with phase prefix for additivity"
    - "Reviewer-verifiable grep evidence for the read-only mgmt-account posture (POST/PATCH/PUT/DELETE structural absence outside auth)"
    - "Pattern G (token redaction) extended structurally to ASA/FMC/Checkpoint collectors with test-grep evidence"
key_files:
  created:
    - .planning/phases/11-firewall-integration/11-13-SUMMARY.md
  modified:
    - agent/docs/cab/threat-model.md
    - agent/docs/cab/architecture.md
    - agent/docs/cab/dataflow.md
    - agent/docs/cab/known-limitations.md
    - agent/docs/cab/operator-runbook.md
    - agent/docs/cab/README.md
decisions:
  - "Threat-ID convention generalized to T-PP-NN-MM (PP = phase number). Phase 10 baseline kept under T-10-*; Phase 11 additions are T-11-NN-MM where NN is the source plan number. Methodology section explicitly documents the additive-only contract."
  - "Phase 11 credential-storage section placed AFTER the Phase 10 Threat Register (not interleaved). Reviewers reading the packet linearly see the Phase 10 register, then the Phase 11 register additions, then the Phase 11 credential-storage charter. This keeps Phase 10 institutional history readable as a unit even after the extension."
  - "Reviewer-verifiable grep evidence included in threat-model.md AND operator-runbook.md for the read-only mgmt-account posture. Operators get an actionable check; reviewers get a structural proof. Same grep commands work in both contexts."
  - "Read-only command list documented per-vendor in the threat-model.md credential-storage section: ASA REST (POST /api/tokenservices + GETs + DELETE token only); ASA SSH (terminal pager 0 + show running-config only); FMC (generatetoken/refreshtoken + GETs only); Checkpoint (login + show-* + logout only). An empty grep on POST/PATCH/PUT/DELETE outside these paths is the structural read-only proof."
  - "L-11-01..L-11-05 chosen as five distinct surfaces (each maps to one RESEARCH artifact: Pitfall 1, Pitfall 2 / Risk Landmine 4, Open Q3, Pitfall 6, Risk Landmine 2 / Pitfall 7). All five include 'operator action available' yes-answers — no Phase 11 limitation is a security blocker by design."
  - "Operator runbook Phase 11 section is structured as Steps F1-F7 (Firewall steps) rather than re-numbering Steps 1-N. Preserves the Phase 10 Step 1-7 numbering an operator may have memorized, and gives Phase 11 a clear standalone path."
  - "agent.yaml shape in Step F1 includes inline comments per device explaining when to use each protocol (ASA REST EOL caveat, ASA SSH universal, FMC first-domain caveat, Checkpoint live vs import semantics) — reduces operator's lookup burden when configuring new devices."
  - "Smoke checkpoint deferred to operator (`/gsd-verify-work 11`). This plan ships the documentation; the smoke test belongs to the human operator per Plan 11-13 task 3 (`checkpoint:human-verify`, autonomous:false). Documented in this SUMMARY's 'Smoke Checkpoint Status' section."
  - "STATE.md + ROADMAP.md intentionally NOT modified by this plan — the Wave 5 orchestrator owns those writes after this SUMMARY lands and the smoke test is approved."
metrics:
  duration_seconds: 765
  duration_minutes: 13
  tasks_completed: 2   # Task 1: threat-model; Task 2: 4 supporting docs + README
  tasks_remaining: 1   # Task 3: human smoke-test checkpoint (deferred to operator)
  files_created: 1     # this SUMMARY
  files_modified: 6    # 5 CAB docs + README
  total_files: 7
  completed_date: "2026-05-15"
---

# Phase 11 Plan 13: CAB Packet Extension Summary

Phase 11 firewall integration material is now surfaced in the CAB packet across five documents. Phase 10 baseline preserved verbatim (43 T-10 rows untouched, existing TB tables / Steps 1-7 / L-1..L-7 unchanged); Phase 11 additions live in clearly-delimited new sections under each document's existing structure. Smoke-test checkpoint (Task 3 of the plan) is **PENDING — operator to run `/gsd-verify-work 11`**.

## What Was Built

### Commit 1 — `0ea6ff3` `docs(11-13): extend CAB threat-model.md with Phase 11 threat rows`

`agent/docs/cab/threat-model.md` extended additively:

| Trust Boundary | Phase 10 rows (preserved) | Phase 11 rows added |
|---|---|---|
| TB-1 (Network device → Agent) | 17 T-10 rows | 17 T-11 rows — T-11-08-01..05 (ASA REST), T-11-09-01..06 (ASA SSH), T-11-10-01..05 (FMC), T-11-11-01..06 (Checkpoint live + import) |
| TB-2 (Agent → Cloud backend) | 15 T-10 rows | 18 T-11 rows — T-11-02-01..05 (migration/RLS/TTL/forward-feed), T-11-03-01..05 (push handlers), T-11-04-01..04 (read endpoint), T-11-05-01..03 (push client), T-11-07-01..02 (ticker), T-11-12-01..04 (dispatcher) |
| TB-3 (Filesystem → Agent) | 11 T-10 rows | 4 T-11 rows — T-11-06-01..04 (config validation + protocol switch + checkpoint-import path) |
| **Totals** | **43 T-10 rows** | **49 T-11 rows** |

Threat-ID convention generalized to `T-PP-NN-MM` (PP = phase, NN = source plan, MM = local sequence). Methodology section explicitly documents the additive-only contract.

**New "Phase 11 — Firewall Management Credential Storage" subsection** carries the five CONTEXT.md credential-storage guarantees verbatim:

1. Firewall mgmt credentials never leave the agent host (T-10-03-01 inheritance via D-17).
2. Only rule-base + NAT + object metadata is transmitted to SaaS — never live traffic, never password material, never the Checkpoint SID / ASA `X-Auth-Token` / FMC `X-auth-access-token`.
3. Transmission is TLS-encrypted via the existing push client (D-19 Bearer-token + retry-twice-then-drop reused verbatim).
4. Site token is revocable per-site — one revocation lever kills all 5 ingest paths atomically.
5. Login-per-pull for Checkpoint = no SID at rest (D-14).

Plus the **read-only mgmt-account structural proof** with reviewer-verifiable grep commands per vendor (POST/PATCH/PUT/DELETE structural absence outside auth and `show-*`/`logout` paths).

Accepted Risks Summary extended with 5 Phase 11 entries (MITM acceptance on the 4 firewall mgmt channels, crafted-input residuals preserved via raw_blob, best-effort cleanup bounds, FMC single-domain residual).

### Commit 2 — `48c01aa` `docs(11-13): extend CAB architecture/dataflow/limitations/runbook with Phase 11`

**`architecture.md`** — new "Phase 11 — Firewall Integration" section covers:

- 5 protocol values + per-vendor collector mapping (asa-rest / asa-ssh / fmc / checkpoint / checkpoint-import)
- Updated Mermaid system diagram extended with 5 firewall mgmt-plane peers and 3 new HTTPS push endpoints
- 6-step firewall data flow: 4th ticker fires → dispatcher selects collector → mints ONE shared `snapshot_id` per device per tick (RESEARCH Pattern 2) → collector pulls rules+NAT+objects → fans out 3 idempotent POSTs sharing the same envelope → backend `INSERT ... ON CONFLICT DO NOTHING` on parent + bulk-insert children
- Hybrid storage model (D-08), snapshot-per-pull replace (D-10), TTL prune (14d default, env-overridable)
- RLS team_isolation on all 4 backend tables (Pattern B with parent-row policy on `team_id`, child-row policies via FK lookup)
- Updated component map (8 new agent files), process model (4th-ticker shutdown drain), network footprint (4 new outbound peers, zero new inbound), dependency footprint (google/uuid v1.6.0)

**`dataflow.md`** — Data Inventory table gains 10 Phase 11 rows: firewall rule-base / NAT / objects / shared snapshot_id (TB-2 to SaaS) + firewall mgmt username / password (NEVER transmitted) + ASA REST X-Auth-Token / FMC access+refresh tokens / FMC DOMAIN_UUID / Checkpoint SID (all in-memory only). 4 new "Data NOT Transmitted" hard-guarantee bullets. Encryption-in-transit table gains TLS 1.2+ posture for ASA REST / FMC / Checkpoint live; ASA SSH inherits Phase 10 SSH posture. Encryption-at-rest table gains 5 new Phase 11 rows.

**`known-limitations.md`** — title generalized; new "Phase 11 Firewall Integration" section with L-11-01..L-11-05:

| ID | Limitation | RESEARCH source |
|---|---|---|
| L-11-01 | ASA REST API EOL at 9.16 boundary | Pitfall 1 |
| L-11-02 | Checkpoint SID timeout on >50k-rule layers | Pitfall 2 / Risk Landmine 4 |
| L-11-03 | checkpoint-import sibling-file naming convention | Open Q3 (RESOLVED) |
| L-11-04 | FMC first-domain / first-policy simplification | Pitfall 6 |
| L-11-05 | 14-day snapshot retention default | Pitfall 7 / Risk Landmine 2 |

Each row has Impact + Operator Workaround. Phase-11 risk-acceptance summary table notes none of L-11-01..05 are security blockers.

**`operator-runbook.md`** — new "Firewall Devices (Phase 11)" section structured as Steps F1-F7 (preserves the Phase 10 Steps 1-7 an operator may have memorized):

- F1: `agent.yaml` shape with all 5 firewall protocol examples (verbatim from CONTEXT.md `<specifics>`)
- F2: Read-only mgmt-account guidance per vendor + reviewer-verifiable grep commands
- F3: `mgmt_cli` commands to produce the 3 sibling `.rulebase.json` / `.nat.json` / `.objects.json` files (resolves Open Q3)
- F4: Verification — agent log lines, backend log lines, Clerk-JWT read-API curl (with jq projection)
- F5: Credential rotation procedure (vendor mgmt → agent.yaml → reload → watch next tick)
- F6: Troubleshooting matrix — 401 on asa-rest → ASA version check (L-11-01); FMC mid-pull 401 → token TTL exceeded; Checkpoint 401 → SID timeout (L-11-02); checkpoint-import file not found → sibling naming (L-11-03); asa-ssh short parse → pager truncation; invalid protocol → T-11-06-01; missing config_file for checkpoint-import → T-11-06-03
- F7: Cadence notes (1h fixed; sub-minute typical pull duration; sync.WaitGroup shutdown drain)

**`README.md`** — front-matter updated from "Phase: 10" to "Phases covered: 10 + 11". "What the agent does NOT do" bullets extended additively to cover Phase 11 read-only posture, mgmt credential storage, and vendor session token transit.

## Commits

| Commit | Type | Summary | Files |
|---|---|---|---|
| `0ea6ff3` | docs | extend CAB threat-model.md with Phase 11 threat rows | 1 |
| `48c01aa` | docs | extend CAB architecture/dataflow/limitations/runbook with Phase 11 | 5 |

## Decisions Made

Captured in frontmatter `decisions:`. Highlights:

1. **Threat-ID convention generalized to `T-PP-NN-MM`.** Phase 10 keeps T-10-*; Phase 11 adds T-11-NN-MM where NN is the source plan number. Methodology section explicitly documents the additive-only contract so a future Phase 12 extension follows the same template.
2. **Phase 11 sections placed at end of each document.** Reviewers reading the packet linearly see the Phase 10 baseline as a complete unit, then the Phase 11 extension as a clearly-bounded addition. Avoids inter-leaving Phase 10 / Phase 11 content within a single section heading.
3. **Reviewer-verifiable grep evidence included in BOTH threat-model and operator-runbook.** Operators get an actionable check; reviewers get a structural proof; same grep commands work in both contexts. This is the v1.1 substitute for cryptographic attestation of the read-only posture (which the Phase 10 deferred-items list pushes to enterprise tier).
4. **L-11-01..L-11-05 chosen as five distinct surfaces.** Each row maps 1-to-1 to a RESEARCH artifact (Pitfall 1 / Pitfall 2 + Risk Landmine 4 / Open Q3 / Pitfall 6 / Risk Landmine 2 + Pitfall 7). All five have operator-actionable workarounds — no Phase 11 limitation is a security blocker by design.
5. **Operator runbook Step F1-F7 numbering** preserves Phase 10 Steps 1-7. Operators reading the runbook to add firewall devices to an existing Phase 10 deployment have a clear standalone path that does not re-shuffle the muscle-memory steps.
6. **agent.yaml example in F1 has inline per-device commentary.** Each of the 5 protocol blocks carries 1-2 lines of comment explaining when to use it (ASA REST EOL caveat, ASA SSH universal-version, FMC first-domain caveat, Checkpoint live vs import semantics). Reduces operator's documentation-lookup burden when configuring new devices.
7. **STATE.md + ROADMAP.md intentionally NOT modified.** Per the orchestrator's instructions, Wave 5 closure writes are orchestrator-owned and happen after this SUMMARY lands and the smoke test is approved.

## Deviations from Plan

**[Rule 2 — Auto-add missing critical functionality]** Touched `agent/docs/cab/README.md` (not in plan `files_modified`).

- **Found during:** Task 2 verification.
- **Issue:** The CAB packet's `README.md` front-matter declares `**Phase:** 10 (DC Agent Core).` and the "What the agent does NOT do" section is titled `(Phase 10 scope)`. Without updating these, a reviewer downloading the packet sees a Phase 11-extended threat-model + architecture + dataflow + known-limitations + operator-runbook, but a README claiming the packet covers Phase 10 only. That's a CAB-packet correctness defect (R-class — Repudiation residual: agent ships with Phase 11 functionality but the packet's table-of-contents disclaims Phase 11). The CAB plan's own threat row T-11-13-02 explicitly mitigates "CAB packet accidentally documents a credential leak vector that does not exist (over-disclosure)" — its dual (under-disclosure) is equally CAB-rejection-shaped.
- **Fix:** Two additive edits to `README.md`:
  - Front-matter `**Phase:** 10` → `**Phases covered:** 10 + 11`; `Last updated: 2026-05-10` → `2026-05-15 (Phase 11 extension landed; Phase 10 baseline preserved verbatim)`.
  - "What the agent does NOT do" section title → `(Phase 10 + Phase 11 scope)` and bullets extended additively to cover firewall mgmt credentials, vendor session tokens, and the read-only-collector posture.
- **Files modified:** `agent/docs/cab/README.md` (additive edits only; existing bullet language preserved).
- **Commit:** Folded into commit 2 (`48c01aa`).
- **Verification:** Phase 10 baseline (the Phase 10 component list, the outbound-only network posture, the "How to review this packet" enumerated workflow) is untouched.

No other deviations.

## Authentication Gates

None encountered (this is a docs-only plan; no credential prompts surfaced).

## Smoke Checkpoint Status

**Plan 11-13 Task 3 status: PENDING — operator to run `/gsd-verify-work 11`.**

Per Plan 11-13's `<task type="checkpoint:human-verify" gate="blocking">`, the final task is a human smoke test where the operator runs the agent against a fixture-backed (Option A — hermetic, recommended) or real-firewall (Option B) target and verifies data lands in the backend read API. The plan body explicitly delineates a 7-step hermetic procedure (Option A) using the Wave 0 `agent/internal/checkpoint/testdata/ckp-access-rulebase.json` fixture via `protocol: checkpoint-import`.

This executor agent (`/gsd-execute-phase` Wave 5 spawn) STOPS here per the plan's `autonomous: false` flag and the orchestrator dispatch contract:

> CRITICAL — STOP BEFORE the final human smoke checkpoint. The plan's final task is a human smoke test ... You MUST: Write all 5 doc extensions; Commit them atomically; Write SUMMARY.md marking the smoke checkpoint as "PENDING — operator to run /gsd-verify-work 11"; Then RETURN — do NOT attempt the smoke test yourself.

When the operator runs the smoke test:

- **Option A (recommended)** validates end-to-end functionality without requiring real-vendor lab hardware — local backend + Wave 0 fixture file + `protocol: checkpoint-import` + a fast `--firewall-interval 5s` flag (or temporary `defaultIntervals().Firewall` lowering for the smoke run). 6-7 backend log lines per tick with shared `snapshot_id` is the success signal.
- **Option B** is for sites with real ASA / FMC / Checkpoint lab hardware available.

Resume-signal language from the plan:

- `"approved"` — smoke passed cleanly; Phase 11 closure proceeds.
- `"approved-with-flags"` + description — smoke partially passed; Phase 11 can still close with the flagged residuals tracked.
- `"blocked"` + description — smoke failed; Plans 11-12 or earlier need re-work.

## Known Stubs

None introduced. This plan is docs-only; no source code touched. Phase 10 + Phase 11 production code is locked at HEAD = `48c01aa` and remains in the state Wave 4 left it (all 9 Go packages PASS `go test -race`; backend pytest suite GREEN for the 12 firewall-related tests).

## TDD Gate Compliance

This plan is `type: execute`, `tdd: false` (docs-only; no test-first / RED-GREEN cycle applies). All previous Phase 11 plans (11-01 through 11-12) carried their own TDD compliance attestations in their respective SUMMARY files; this plan does not regress any of them (zero source code modified, zero tests modified).

## Verification

### Automated checks performed

```bash
# Task 1 acceptance — threat-model.md
F=agent/docs/cab/threat-model.md
grep -c '^| T-11-' $F                    # 49 (>= 30 required)
grep -c '^| T-10-' $F                    # 43 (Phase 10 baseline preserved)
grep -c 'Firewall Mgmt Credential Storage\|Firewall Management Credential Storage' $F  # 1
grep -c 'login-per-pull' $F              # 1
grep -c -i 'site token is revocable' $F  # 1
grep -c 'firewall mgmt credentials\|firewall management credentials' $F  # 4
grep -c 'TLS-encrypted' $F               # 1
grep -c 'never leave the agent host' $F  # 1
grep -cE 'T-11-08-|T-11-09-|T-11-10-|T-11-11-' $F  # 30
grep -cE 'T-11-02-|T-11-03-|T-11-04-' $F           # 14

# Task 2 acceptance — architecture / dataflow / known-limitations / operator-runbook
grep -c '## Phase 11' agent/docs/cab/architecture.md                                  # 1
grep -cE 'asa-rest|asa-ssh|fmc|checkpoint|checkpoint-import' agent/docs/cab/architecture.md  # 21
grep -cE 'snapshot_id|UUIDv4|Pattern 2' agent/docs/cab/architecture.md                # 9
grep -cE 'Firewall rule-base|Firewall NAT|Firewall objects|Checkpoint SID' agent/docs/cab/dataflow.md  # 6
grep -c '^| L-11-' agent/docs/cab/known-limitations.md                                 # 10
grep -cE 'ASA REST.*9\.16|ASA REST.*9\.17|removed at ASA 9' agent/docs/cab/known-limitations.md  # 1
grep -cE 'session-timeout|SID timeout' agent/docs/cab/known-limitations.md             # 2
grep -c '## Firewall Devices\|Firewall Devices (Phase 11)' agent/docs/cab/operator-runbook.md  # 1
grep -c 'agent.yaml' agent/docs/cab/operator-runbook.md                                # 26
grep -cE 'mgmt_cli show access-rulebase|mgmt_cli show nat-rulebase|mgmt_cli show objects' agent/docs/cab/operator-runbook.md  # 3
grep -cE 'systemctl reload infracanvas-agent|SIGHUP' agent/docs/cab/operator-runbook.md  # 2
```

All Task 1 + Task 2 acceptance-criterion grep counts MET or EXCEEDED.

### Skipped due to plan scope

- Task 3 smoke-test (deferred to operator via `/gsd-verify-work 11`).
- STATE.md / ROADMAP.md updates (orchestrator-owned per Wave 5 dispatch contract).

## Self-Check: PASSED

- `agent/docs/cab/threat-model.md` modified — 49 T-11 rows present, 43 T-10 rows preserved ✓
- `agent/docs/cab/architecture.md` modified — `## Phase 11` section present with Mermaid diagram + 6-step data flow ✓
- `agent/docs/cab/dataflow.md` modified — 4 new firewall data rows + Phase 11 hard-guarantee bullets + TLS posture rows for ASA/FMC/Checkpoint ✓
- `agent/docs/cab/known-limitations.md` modified — L-11-01..L-11-05 present with operator workarounds ✓
- `agent/docs/cab/operator-runbook.md` modified — Steps F1-F7 present + agent.yaml shape for all 5 protocols + mgmt_cli commands + rotation procedure + 7-row troubleshooting table ✓
- `agent/docs/cab/README.md` modified — Phase 11 coverage declared in front-matter and read-only-collector posture surfaced in "What the agent does NOT do" ✓
- Both commits (`0ea6ff3`, `48c01aa`) reachable in `git log` ✓
- No deletions in either commit (verified `git diff --diff-filter=D --name-only HEAD~1 HEAD` → empty for both) ✓
- Phase 10 baseline (43 T-10 rows + Steps 1-7 + L-1..L-7 + Phase 10 dataflow tables) untouched — confirmed by row-count and section-heading invariance ✓
- STATE.md, ROADMAP.md, REQUIREMENTS.md NOT modified (orchestrator-owned) ✓
- No source code touched ✓
- Smoke checkpoint correctly marked PENDING with operator instructions ✓

## Next Step

Operator runs `/gsd-verify-work 11` (or the equivalent Phase 11 closure workflow). On `approved` resume-signal the Wave 5 orchestrator advances:

- STATE.md: Phase 11 plans complete 12 → 13; current phase advances if applicable.
- ROADMAP.md: Phase 11 status → COMPLETE; mark all 5 success criteria checked.
- REQUIREMENTS.md: ASA-01 / ASA-02 / ASA-03 / CKP-01 / CKP-02 marked complete with traceability to the corresponding Plan 11-NN summaries.
- Phase 11 retrospective (optional but recommended) to capture v1.2 follow-ups (FMC multi-domain, OS-keychain creds, long-lived Checkpoint SID with refresh — all carried forward on the deferred-items list).
