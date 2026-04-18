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
result: pass
closed_by: 02-09-PLAN.md (fix(viewer): inline JetBrains Mono + Inter via @fontsource)
verification: |
  Re-verified 2026-04-18 after plan 02-09 landed:
  - grep -cE 'fonts\.googleapis\.com|fonts\.gstatic\.com' report.html → 0 (was 1)
  - stat -f%z report.html → 2,081,117 bytes (~1.98MB, well under 5MB limit)
  - grep -oE '@font-face' report.html | wc -l → 46 (Inter + JetBrains Mono weights/subsets inlined as woff2 base64)
  - vite-plugin-singlefile now inlines @fontsource/* CSS via the module graph; no CDN fetch remains.

## Summary

total: 7
passed: 7
issues: 0
pending: 0
skipped: 0

## Gaps

(none — all tests pass; test 7 fonts gap closed by plan 02-09 on 2026-04-18 using option 2 from fix_hint: @fontsource/inter + @fontsource/jetbrains-mono inlined via vite-plugin-singlefile)
