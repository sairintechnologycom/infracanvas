---
phase: 03-flowmap-v1-0
plan: 03
subsystem: infra
tags: [aws, boto3, tgw, vpc, direct-connect, vpc-flow-logs, collector, placebo]

requires:
  - phase: 03-flowmap-v1-0/plan-01
    provides: NetworkPath, PathHop, NetworkFinding, ResourceGraph v2.1 Pydantic models
  - phase: 03-flowmap-v1-0/plan-02
    provides: run_flowmap_collection orchestrator — AWS seam that calls collect_aws_network
provides:
  - collect_aws_network(graph, *, region) — reads TGW + TGW attachments + TGW route tables + VPN connections + VPC route tables + Network ACLs + Direct Connect + VPC Flow Logs metadata via boto3
  - AWS cloud resource-type strings emitted on the graph: aws_ec2_transit_gateway, aws_ec2_transit_gateway_attachment, aws_ec2_transit_gateway_route_table, aws_vpn_connection, aws_route_table, aws_network_acl, aws_dx_connection, aws_dx_virtual_interface, aws_vpc_flow_log (field-name parity with Plan 03-05's rule YAML and Plan 03-07's NETWORK_TYPES set)
affects: [03-05 NET rules — rules reference the verbatim resource_type strings this collector emits; 03-07 viewer — NETWORK_TYPES set expects these strings]

tech-stack:
  added: [boto3, placebo (dev dep)]
  patterns: [boto3 session with explicit region param, placebo fixture replay for credential-free tests, pytest.importorskip gating when flowmap extras are absent]

key-files:
  created:
    - cli/infracanvas/flowmap/aws.py
    - cli/tests/test_flowmap_aws.py
    - cli/tests/fixtures/flowmap/aws/placebo_tgw.json
    - cli/tests/fixtures/flowmap/aws/placebo_dx.json

key-decisions:
  - "Placebo fixtures (not moto) for AWS tests — matches RESEARCH.md + plan guidance. Placebo replay is simpler, deterministic, and records real API shapes."
  - "All boto3 client creation goes through boto3.Session(region_name=region) — the orchestrator (Plan 03-02) infers region from .tf files when not supplied, matching the existing --shadow idiom"
  - "IAM scope is describe-only (ec2:Describe*, directconnect:Describe*, logs:DescribeLogGroups/Streams) — no ec2:GetFlowLogs or similar read-data calls. Metadata only, mirrors shadow/ scope."
  - "pytest.importorskip('boto3') at the top of test_flowmap_aws.py — tests skip cleanly when the flowmap extras are not installed in the default CI environment"

patterns-established:
  - "collect_<cloud>_network(graph, *, region) signature: mutates the graph with NetworkPaths/PathHops/cloud network nodes, returns the same ResourceGraph for method-chain compatibility with the orchestrator"
  - "Private _collect_* helpers per boto3 service surface (one per API family) — keeps each function small and independently testable"

requirements-completed: [AWS-01, AWS-02, AWS-03]

duration: ~40 min (sub-agent through Task 2 + Task 3 test file) + ~5 min (orchestrator: commit orphaned test file + write SUMMARY after rate-limit interruption)
completed: 2026-04-19
---

# Phase 03-flowmap-v1-0 / Plan 03: AWS Cloud-Network Collector

**collect_aws_network uses boto3 to describe TGW, VPC, Direct Connect, and VPC Flow Logs metadata, appending NetworkPath + PathHop + cloud node entries to the ResourceGraph that Plan 03-02's orchestrator hands in. 12 placebo-replay tests cover the full surface — no live AWS creds needed.**

## Performance

- **Duration:** ~45 min total (sub-agent committed placebo fixtures + aws.py implementation + wrote the test file; rate-limit hit before `git add` + SUMMARY commit. Orchestrator finished both inline.)
- **Tasks:** 3/3 complete
- **Files created:** 4

## Accomplishments
- `collect_aws_network(graph, *, region) -> ResourceGraph` public entry point, called from Plan 03-02's `run_flowmap_collection` AWS seam
- 10 private `_collect_*` helpers: transit gateways, TGW attachments, TGW route tables, VPN connections, VPC route tables, Network ACLs, Direct Connect (connections + virtual interfaces), VPC Flow Logs metadata
- Emits 9 `aws_*` resource_type strings that Plan 03-05's NET-* rule YAML files target verbatim
- Placebo fixtures for TGW + Direct Connect (`cli/tests/fixtures/flowmap/aws/placebo_{tgw,dx}.json`)
- 12 pytest cases covering positive paths (describe returns data → nodes/paths appended), defensive cases (missing creds, missing region, empty account), and the node-type contract (emitted resource_type strings match Plan 03-05 + 03-07 expectations)
- `pytest cli/tests/ -x` stays green: **268 pass** (240 Wave-2 baseline + 16 Azure from 03-04 + 12 AWS from this plan)

## Task Commits

1. **Task 2 prep / Task 3 red:** `196a25c` — test(03-03): add placebo fixtures for TGW + Direct Connect
2. **Task 2 impl:** `49a2b86` — feat(03-03): implement AWS cloud-network collector (TGW + DX + VPC Flow Log metadata)
3. **Task 3 impl (orchestrator rescue):** `c7a53be` — test(03-03): pytest coverage for collect_aws_network

## Files Created
- `cli/infracanvas/flowmap/aws.py` — 305 lines, 1 public + 9 private functions
- `cli/tests/test_flowmap_aws.py` — 215 lines, 12 test cases
- `cli/tests/fixtures/flowmap/aws/placebo_tgw.json` — recorded describe_transit_gateways / describe_transit_gateway_attachments / describe_transit_gateway_route_tables response shapes
- `cli/tests/fixtures/flowmap/aws/placebo_dx.json` — recorded describe_connections / describe_virtual_interfaces response shapes

## Decisions Made
- Sub-agent bypassed worktree isolation and committed to main directly (visible in `git log --all` showing all 03-03 commits on main before the worktree-merge step). The work itself is clean and passes tests, but this is a worktree-discipline failure in the sub-agent's flow. Noted as a process issue for the harness.
- Orchestrator rescued the final task by committing the already-written test file (left as uncommitted WIP when the rate limit fired) and writing this SUMMARY. No code changes were made.

## Deviations from Plan
**1. [Rule 3 — Blocking] Sub-agent bypassed worktree isolation**
- **Found during:** post-wave spot-check
- **Issue:** Agent committed all 03-03 work directly to `main` in the main repo clone instead of to its assigned worktree (`.claude/worktrees/agent-ac231fe0/`). The worktree stayed at its branch head (`2c7bfff`) with no new commits; the actual work landed on main.
- **Fix:** No code change needed — the commits are already on main in the correct linear order and tests pass. The worktree branch is empty and will be cleaned up during post-wave teardown.
- **Verification:** `git log --oneline --grep="03-03"` shows `196a25c` + `49a2b86` on main; `git -C <worktree> log 2c7bfff..HEAD` returns empty.
- **Committed in:** those same commits

**2. [Rule 2 — Necessary] Rate-limit interruption before SUMMARY + final test commit**
- **Found during:** task-notification reported "You've hit your limit · resets 3:30pm"
- **Issue:** Agent wrote `test_flowmap_aws.py` but was killed by Anthropic rate-limit before `git add` + `git commit`. No SUMMARY.md was written.
- **Fix:** Orchestrator verified the uncommitted test file passes (`pytest tests/ -x` → 268 pass), committed it as `test(03-03)`, and wrote this SUMMARY.
- **Verification:** 268 tests pass; file is committed at `c7a53be`.

## Issues Encountered
- Sub-agent worktree bypass (see Deviation 1) — not a test or code issue, but worth flagging as a harness process concern. The same thing happened with Plan 03-04 (both Wave 3 agents committed to main directly).
- Rate-limit hit at token ~1800 before SUMMARY — second time in this phase (first was Plan 03-01). Suggests Wave 3 was run near the daily quota ceiling.

## User Setup Required
For actual `--flowmap` network collection against live AWS:
- **AWS credentials** via standard chain (env vars, `~/.aws/credentials`, or instance profile)
- **IAM scope:** describe-only — `ec2:Describe*`, `directconnect:Describe*`, `logs:DescribeLogGroups`, `logs:DescribeLogStreams`
- **Region:** inferred from `.tf` files if not supplied; override with `AWS_DEFAULT_REGION`

No user action needed for tests — placebo fixtures replay without real AWS.

## Next Phase Readiness
- Plan 03-02's AWS seam (`collect_aws_network`) now has a real implementation
- Plan 03-05's AWS NET rules (NET-001..NET-006) fire against the exact resource_type strings this collector emits — cross-plan contract verified by `test_node_types_use_aws_prefix`-style tests
- Plan 03-07's `NETWORK_TYPES` set includes all resource types this collector emits — viewer canvas correctly filters to FlowMap nodes
- With Plan 03-04 (Azure) also landing in the same wave, Phase 3a cloud-only FlowMap foundation is feature-complete

---
*Phase: 03-flowmap-v1-0*
*Completed: 2026-04-19*
