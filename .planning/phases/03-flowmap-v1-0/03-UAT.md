---
status: complete
phase: 03-flowmap-v1-0
source: [03-01-SUMMARY.md, 03-02-SUMMARY.md, 03-03-SUMMARY.md, 03-04-SUMMARY.md, 03-05-SUMMARY.md, 03-06-SUMMARY.md, 03-07-SUMMARY.md, 03-08-SUMMARY.md, 03-09-SUMMARY.md]
started: 2026-04-19T17:15:00Z
updated: 2026-04-19T17:35:00Z
verification_mode: end-to-end-automated
---

## Current Test

[testing complete]

## Tests

### 1. Cold Start Smoke Test
expected: Run `infracanvas scan cli/tests/fixtures/simple_vpc --output /tmp/uat-3.html`. CLI exits 0, produces HTML, and JSON output has top-level `version: "2.1"` with `network_paths: []` and `dc_sites: []`.
result: pass
evidence: |
  EXIT=0. HTML produced at /tmp/uat-3.html (3,564,825 bytes).
  JSON --format json --quiet: version=2.1, network_paths=[], dc_sites=[].
  Top-level keys: version, metadata, nodes, edges, summary, network_paths, dc_sites.

### 2. --flowmap flag advertised in CLI help
expected: `infracanvas scan --help` lists `--flowmap` with help text containing "Beta, free during preview".
result: pass
evidence: |
  Help text: "Collect cloud network topology (AWS TGW + Azure vWAN + Direct Connect/ExpressRoute). Beta, free during preview."

### 3. Scan WITHOUT --flowmap unchanged (zero regression)
expected: `infracanvas scan cli/tests/fixtures/simple_vpc` behaves identically to Phase 2 — no yellow warnings, produces v2.1 JSON with empty network_paths/dc_sites.
result: pass
evidence: |
  EXIT=0, empty stderr, no flowmap-related warnings. JSON shape preserved: version=2.1, network_paths=[], dc_sites=[].

### 4. Scan WITH --flowmap, no AWS/Azure creds
expected: `infracanvas scan … --flowmap` with no creds prints yellow "Warning: … Skipping {cloud} network collection." and continues; final JSON produced with empty network_paths.
result: pass
evidence: |
  EXIT=0. Warnings observed:
    "Warning: boto3 not installed. Install with: pip install 'infracanvas' Skipping ..."
    "Warning: --flowmap requires Azure credentials: ARM_CLIENT_ID, ARM_CLIENT_SECRET, ARM_TENANT_ID, ARM_SUBSCRIPTION_ID missing. Skipping Azure network collection."
  HTML produced at /tmp/uat-3-flowmap.html. Graceful warn-and-continue per D-05.

### 5. AWS collector against real AWS account
expected: With AWS creds + TGW/VPC resources, --flowmap adds `aws_ec2_transit_gateway` / `aws_vpc_flow_log` / `aws_dx_connection` nodes.
result: blocked
blocked_by: third-party
reason: |
  No live AWS account/creds available. Covered by unit-level placebo fixtures
  (cli/tests/fixtures/flowmap/aws/placebo_tgw.json, placebo_dx.json, 12 tests
  at commit c7a53be). Live verification deferred.

### 6. Azure collector against real Azure subscription
expected: With ARM_* env vars + vWAN/vNet, --flowmap adds `azurerm_virtual_wan` / `azurerm_virtual_hub` / `azurerm_virtual_network` nodes.
result: blocked
blocked_by: third-party
reason: |
  No live Azure subscription/creds available. Covered by unit-level mock-SDK
  fixtures (cli/tests/fixtures/flowmap/azure/vwan.json, vnet.json, expressroute.json,
  16 tests at commit ed19638). Live verification deferred.

### 7. NET-* network security rules surface in viewer
expected: Scan a fixture that triggers at least one NET rule; the viewer's Findings tab on the affected node shows a NET-xxx finding card with title + remediation + framework_ids.
result: pass
evidence: |
  simple_vpc scan triggers NET-004 "VPC Without Flow Logs Enabled" (severity=medium)
  on aws_vpc.main. Finding JSON:
    rule_id: NET-004, title: "VPC Without Flow Logs Enabled"
    remediation: 104 chars
    framework_ids: [CIS-3.9, NIST-AU-2, SOC2-CC7.2, PCI-DSS-10.1]
  CLI findings table in scan output also lists NET-004.

### 8. Viewer TabBar shows Canvas + FlowMap tabs
expected: Exported HTML shows Canvas (active) + FlowMap tabs below SummaryBar, BETA pill on FlowMap, arrow-key nav.
result: pass
evidence: |
  Headless Chromium snapshot of /tmp/uat-3.html:
    @e8 [tab] "Canvas" [selected]
    @e9 [tab] "FlowMap beta": FlowMap BETA
  HTML token counts: FlowMap=13, activeTab=4, BETA=1.

### 9. Switching to FlowMap swaps the 3-column shell
expected: Click FlowMap tab → left becomes FlowMapFilterPanel, centre FlowMapCanvas, right PathDetailPanel.
result: pass
evidence: |
  Clicking FlowMap tab via JS sets aria-selected=true on FlowMap, aria-selected=false on Canvas.
  Layout swap confirmed: Canvas content replaced by FlowMap content.
  Bundle tokens: FlowMapFilterPanel=2, FlowMapCanvas=2, PathDetailPanel=2.

### 10. Empty-state card on FlowMap tab
expected: FlowMap canvas area shows "No network topology collected yet" card with CLI block + Copy button + Beta pill.
result: pass
evidence: |
  document.body.textContent.includes('No network topology collected yet') === true.
  "Copy" button present in DOM after FlowMap tab active.
  BETA pill visible (textMatches.beta = true).

### 11. Copy button copies scan command
expected: Click Copy → button shows "Copied ✓" for ~2s; clipboard contains `infracanvas scan ./terraform --flowmap`.
result: pass
evidence: |
  With stubbed navigator.clipboard.writeText (headless can't write real clipboard):
    T=0ms:   button label = "Copy"
    T=100ms: button label = "Copied ✓", clipboard captured value = "infracanvas scan ./terraform --flowmap"
    T=400ms: button label still = "Copied ✓"
    T=3000ms: button label reverts to "Copy"
  Revert timing between 400ms and 3000ms matches "~2s" spec.
  Clipboard content exactly matches expected string.

### 12. FlowMapFilterPanel clear + cloud filter
expected: AWS pill click → aws-only filter; Clear button reveals/hides based on filter activity.
result: blocked
blocked_by: third-party
reason: |
  FlowMapFilterPanel pills only render when network_paths[] is non-empty.
  Same credential dependency as Tests 5/6 blocks live interactive verification.
  Behavior covered by viewer unit tests: vitest run src/__tests__/flowmap/FlowMapFilterPanel.test.tsx
  → 5/5 pass (clear button visibility, AWS-only filter, Azure-only filter, both-clouds filter, clear resets state).

### 13. Escape clears FlowMap selection
expected: Click a network node → right panel populates; Escape clears it back to 'Select a node'.
result: blocked
blocked_by: third-party
reason: |
  Requires non-empty network_paths to render network nodes. Same credential
  dependency as Tests 5/6, 12.
  Behavior covered by viewer unit tests: vitest run src/__tests__/flowmap/PathDetailPanel.test.tsx
  → 5/5 pass (selection populates panel, Escape clears selection, empty state message, keyboard handler scoping, unmount cleanup).

## Summary

total: 13
passed: 9
issues: 0
pending: 0
skipped: 0
blocked: 4

## Blocked Tests

Tests 5, 6, 12, 13 are blocked pending live AWS + Azure credentials.
Unit-test coverage cited for each. Live verification deferred to a
credentialed environment (staging or developer sandbox with read-only
TGW/vWAN/VPC/vNet access).

## Gaps

[none — all testable behaviors pass]

## Notes

Phase 03-09 fix landed successfully. Previous UAT (run 2026-04-19 morning) found
6 blocker issues (Tests 8-13) all tracing to a stale viewer_template.html. This
re-run confirms:
  - All 6 previously-failed tests now pass at every layer they can be exercised:
    * Token presence (Test 8, 9, 10): HTML contains all required FlowMap tokens
    * Live DOM (Test 8, 9, 10): interactive render verified via headless Chromium
    * Behavior (Test 11): Copy button label transition + clipboard content verified
    * Behavior (Test 12, 13): unit-test coverage cited, live blocked on creds
  - The postbuild sync hook (commit 8d98e71) + regression guard (commit e5ca3c5)
    prevent recurrence.
