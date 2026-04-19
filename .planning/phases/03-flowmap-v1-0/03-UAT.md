---
status: diagnosed
phase: 03-flowmap-v1-0
source: [03-01-SUMMARY.md, 03-02-SUMMARY.md, 03-03-SUMMARY.md, 03-04-SUMMARY.md, 03-05-SUMMARY.md, 03-06-SUMMARY.md, 03-07-SUMMARY.md, 03-08-SUMMARY.md]
started: 2026-04-19T10:22:43Z
updated: 2026-04-19T11:16:34Z
---

## Current Test

[testing complete]

## Tests

### 1. Cold Start Smoke Test
expected: Run `infracanvas scan cli/tests/fixtures/simple_vpc --output /tmp/uat-3a.html`. CLI exits 0, produces HTML, and JSON output has top-level `version: "2.1"` with `network_paths: []` and `dc_sites: []`.
result: pass
note: Verified via `--format json --quiet`. Top-level keys include version=2.1, network_paths=[], dc_sites=[].

### 2. --flowmap flag advertised in CLI help
expected: `infracanvas scan --help` lists `--flowmap` with help text containing "Beta, free during preview".
result: pass
note: Help output shows "Collect cloud network topology (AWS TGW + Azure vWAN + Direct Connect/ExpressRoute). Beta, free during preview." verbatim.

### 3. Scan WITHOUT --flowmap unchanged (zero regression)
expected: `infracanvas scan cli/tests/fixtures/simple_vpc` behaves identically to Phase 2 — no yellow warnings, produces v2.1 JSON with empty network_paths/dc_sites.
result: pass
note: Clean scan, no flowmap-related output. JSON shape preserved.

### 4. Scan WITH --flowmap, no AWS/Azure creds
expected: `infracanvas scan … --flowmap` with no creds prints yellow "Warning: … Skipping {cloud} network collection." and continues; final JSON produced with empty network_paths.
result: pass
note: Observed `Warning: boto3 not installed. … Skipping AWS network collection.` and `Warning: azure-mgmt-network not installed. … Skipping Azure network collection.` Exit 0, HTML produced. (Flowmap extras not installed in venv, so ImportError surfaces as the gated RuntimeError message — orchestrator's warn-and-continue behaviour is correct per D-05.)

### 5. AWS collector against real AWS account
expected: With AWS creds + TGW/VPC resources, --flowmap adds `aws_ec2_transit_gateway` / `aws_vpc_flow_log` / `aws_dx_connection` nodes.
result: blocked
blocked_by: third-party
reason: No live AWS account/creds available in current environment. Unit-level placebo coverage (12 tests, commit c7a53be) validates the collector surface; live verification deferred.

### 6. Azure collector against real Azure subscription
expected: With ARM_* env vars + vWAN/vNet, --flowmap adds `azurerm_virtual_wan` / `azurerm_virtual_hub` / `azurerm_virtual_network` nodes.
result: blocked
blocked_by: third-party
reason: No live Azure subscription/creds available. Unit-level mock-SDK coverage (16 tests, commit ed19638) validates collector. Live verification deferred.

### 7. NET-* network security rules surface in viewer
expected: Scan a fixture that triggers at least one NET rule; the viewer's Findings tab on the affected node shows a NET-xxx finding card with title + remediation + framework_ids.
result: pass
note: `simple_vpc` fixture triggers NET-004 (VPC Without Flow Logs Enabled, severity medium) on `aws_vpc.main`. Finding is present in JSON output under the node's findings[] array. Visual rendering in Findings tab is gated on Issue-1 (stale viewer template) but data-layer verification is positive.

### 8. Viewer TabBar shows Canvas + FlowMap tabs
expected: Exported HTML shows Canvas (active) + FlowMap tabs below SummaryBar, BETA pill on FlowMap, arrow-key nav.
result: issue
reported: "HTML bundled by `infracanvas scan` does not contain TabBar/FlowMap/BETA tokens. `grep -oE '(FlowMap|BETA|activeTab)' /tmp/uat-3a.html` returns only 'Flow Logs' (false match)."
severity: blocker

### 9. Switching to FlowMap swaps the 3-column shell
expected: Click FlowMap tab → left becomes FlowMapFilterPanel, centre FlowMapCanvas, right PathDetailPanel.
result: issue
reported: "Gated on Issue-1. FlowMap components are not bundled into the CLI-shipped viewer template, so there is no FlowMap tab to click."
severity: blocker

### 10. Empty-state card on FlowMap tab
expected: FlowMap canvas area shows "No network topology collected yet" card with CLI block + Copy button + Beta pill.
result: issue
reported: "String 'No network topology collected yet' not found in /tmp/uat-3a.html. Component exists in viewer/src/components/flowmap/FlowMapEmptyState.tsx but is absent from the CLI-embedded template."
severity: blocker

### 11. Copy button copies scan command
expected: Click Copy → button shows "Copied ✓" for ~2s; clipboard contains `infracanvas scan ./terraform --flowmap`.
result: issue
reported: "Gated on Issue-1 — empty-state card is not rendered at all in the shipped viewer; Copy button unreachable."
severity: blocker

### 12. FlowMapFilterPanel clear + cloud filter
expected: AWS pill click → aws-only filter; Clear button reveals/hides based on filter activity.
result: issue
reported: "Gated on Issue-1 — FlowMapFilterPanel component not present in shipped HTML."
severity: blocker

### 13. Escape clears FlowMap selection
expected: Click a network node → right panel populates; Escape clears it back to 'Select a node'.
result: issue
reported: "Gated on Issue-1 — FlowMapCanvas/PathDetailPanel not present in shipped HTML."
severity: blocker

## Summary

total: 13
passed: 5
issues: 6
pending: 0
skipped: 0
blocked: 2

## Gaps

- truth: "Bundled viewer template served by `infracanvas scan` must include Phase 3 FlowMap UI (TabBar, FlowMapCanvas, FlowMapFilterPanel, PathDetailPanel, FlowMapEmptyState, BETA pill, empty-state Copy button)"
  status: failed
  reason: "User reported: HTML bundled by infracanvas scan does not contain TabBar/FlowMap/BETA tokens"
  severity: blocker
  test: 8
  root_cause: "cli/infracanvas/export/viewer_template.html (2069895 bytes, mtime Apr 18 10:54) is the pre-Phase-3 Phase-2 bundle. All eight Phase 3 UI commits (Plans 03-06 TabBar, 03-07 FlowMapCanvas + nodes + edges, 03-08 panels + empty-state) landed Apr 19 in viewer/src/ but the built single-file HTML was never re-copied into cli/infracanvas/export/. `grep -c FlowMap` on the template = 0. A fresh `cd viewer && npm run build` (ran during UAT) produces viewer/dist/index.html (3557 KB) that DOES contain all FlowMap tokens — proving the source is fine and the gap is purely a missing build → sync step."
  artifacts:
    - path: "cli/infracanvas/export/viewer_template.html"
      issue: "Stale Phase-2 bundle; needs replacement with newly-built viewer/dist/index.html"
    - path: "viewer/package.json"
      issue: "`build` script does not copy dist/index.html into cli/infracanvas/export/viewer_template.html — no automated sync"
    - path: "cli/pyproject.toml"
      issue: "package-data entry references viewer_template.html but no pre-build hook ensures it matches viewer/src/ HEAD"
  missing:
    - "Run `cd viewer && npm run build` and copy `viewer/dist/index.html` → `cli/infracanvas/export/viewer_template.html` (one-time fix for current UAT)"
    - "Add a post-build sync step (e.g. `postbuild` npm script OR a Makefile target OR a pre-commit hook) that copies viewer/dist/index.html into cli/infracanvas/export/viewer_template.html so this gap cannot recur"
    - "Add a CLI-level smoke test that asserts `grep -c 'activeTab' cli/infracanvas/export/viewer_template.html > 0` to catch future stale-template regressions at CI time"
  debug_session: ""
  tests_blocked: [9, 10, 11, 12, 13]
