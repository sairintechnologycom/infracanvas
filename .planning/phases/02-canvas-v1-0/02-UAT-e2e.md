---
status: complete
phase: 02-canvas-v1-0
scope: end-to-end-phase-1-and-2-rerun
source: [01-UAT.md, 02-UAT.md]
started: 2026-04-18T08:45:00Z
updated: 2026-04-18T09:55:00Z
install_mode: homebrew (infracanvas 0.1.0)
run_mode: autonomous (CI=1 to suppress browser, no user prompting)
---

## Current Test

[testing complete]

## Tests

### 1. Install & Boot — `infracanvas --version`
expected: CLI installed via Homebrew, version prints, no Python traceback.
result: pass
verification: |
  /opt/homebrew/bin/infracanvas → `infracanvas 0.1.0`

### 2. Scan Golden Path — HTML report on insecure_setup
expected: `infracanvas scan <dir> --output report.html` completes <10s, writes a single-file HTML under 5MB, surfaces critical/high findings.
result: pass
verification: |
  real 1.09s (<<10s budget).
  report.html = 458KB / 469337 bytes (<5MB ✓).
  Surfaced SEC-001/003/005/007 (CRITICAL), SEC-002/008 (HIGH), and 4 more MEDIUM/INFO across 7 resources.

### 3. Score Command — terminal + HTML
expected: Score card prints overall + 5 dimensions (Security, Encryption, IAM Hygiene, Cost Efficiency, Tagging) with letter grades. `--format html` writes a self-contained score card.
result: pass
verification: |
  Terminal: Overall 0/100 F; Security 30 F, Encryption 65 B, IAM Hygiene 70 B, Cost Efficiency 100 A, Tagging 94 A. Top issues + est. cost $58/mo rendered.
  HTML: score.html 5.2KB written.

### 4. Plan Overlay — drift diff
expected: `infracanvas plan --planfile sample_plan.json <dir>` overlays add/change/delete onto the diagram with cost delta.
result: pass
verification: |
  plan.html 459KB; summary line "+1 added · ~0 changed · -0 deleted · est. cost delta: +$72.56/mo" matches sample_plan.json intent.

### 5. Azure Support — AZ rules + icons
expected: Scanning the Azure fixture yields Azure resource types and AZ-* findings tagged with compliance frameworks.
result: pass
verification: |
  azure.json: 8 nodes, 6 AZ-* findings.
  Types include azurerm_network_security_group, azurerm_key_vault, azurerm_mssql_server, azurerm_kubernetes_cluster, azurerm_resource_group (and more).
  AZ-001 "NSG Allows Unrestricted Inbound Access" CRITICAL surfaced as expected.

### 6. Policy Engine + CI Mode — exit codes, stdout purity
expected: `--policy <dir> --fail-on=high --ci` → valid JSON to stdout, diagnostics to stderr, non-zero exit on matched policy.
result: pass
verification: |
  exit_code=1 (matches --fail-on=high with policy violations present).
  stdout: valid JSON with keys [version, metadata, nodes, edges, summary].
  stderr: clean.
  policy_findings: 4 (source=policy, POL-* rule_ids).

### 7. Single-file HTML — offline integrity
expected: The bundled report.html is fully self-contained — no external network fetches on load.
result: issue
reported: "report.html still contains <link href='https://fonts.googleapis.com/css2?family=JetBrains+Mono...&family=Inter...&display=swap' rel='stylesheet'>. Page works offline (falls back to system fonts) but violates 'zero external fetches' criterion and leaks a request to air-gapped or privacy-sensitive environments."
severity: minor
verification: |
  grep -cE 'fonts\.googleapis\.com|fonts\.gstatic\.com' report.html → 1 match.
  Matches Phase 2 UAT test 9 gap exactly — not yet remediated.

## Summary

total: 7
passed: 6
issues: 1
pending: 0
skipped: 0

## Gaps

- truth: "Exported HTML must be self-contained with no external network fetches (Phase 1 success criterion: 'opens in any browser with zero dependencies')"
  status: failed
  reason: "Re-confirmed on 2026-04-18: viewer bundle still injects `<link href='https://fonts.googleapis.com/...'>` into the exported HTML. Identical to the 02-UAT.md test 9 gap — no remediation landed between the two runs."
  severity: minor
  test: 7
  artifacts:
    - /tmp/e2e/report.html (repro: `CI=1 infracanvas scan cli/tests/fixtures/insecure_setup/ --output /tmp/e2e/report.html`)
    - viewer/index.html (likely source of Google Fonts <link>)
    - viewer/src/index.css (may reference font-family: Inter, JetBrains Mono)
    - viewer/vite.config.ts (singlefile bundler config — determines whether fonts get inlined)
  missing:
    - Remove the `<link rel="stylesheet" href="https://fonts.googleapis.com/...">` from viewer/index.html, OR inline fonts via @fontsource/inter + @fontsource/jetbrains-mono so Vite bundles the woff2 files, OR fall back to a system-font stack.
  fix_hint: |
    Ranked by cost:
    1. (cheapest) Swap viewer/index.html <link> for system-font stack in CSS. Loses the designer aesthetic but true-offline.
    2. (recommended) Add @fontsource/inter + @fontsource/jetbrains-mono; import in main.tsx; vite-plugin-singlefile will inline the woff2 base64. Slight bundle growth (~150–250KB), still <5MB, preserves aesthetic.
    3. Ship a `--no-fonts` build flag that strips the Google Fonts link at export time (opt-in).
