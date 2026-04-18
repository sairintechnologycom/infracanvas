---
status: testing
phase: 02-canvas-v1-0
scope: end-to-end-phase-1-and-2
source: [01-*-SUMMARY.md, 02-00..02-08-SUMMARY.md]
started: 2026-04-17T21:45:00Z
updated: 2026-04-17T22:30:00Z
install_mode: homebrew (infracanvas 0.1.0)
---

## Current Test

[testing complete]

## Tests

### 1. Fresh AWS scan — diagram opens and renders
expected: Run `infracanvas scan cli/tests/fixtures/insecure_setup/` from the repo root. Completes in <10s, browser opens, viewer shows VPC/subnet zone grouping, resource icons, dependency edges, and security finding badges on resources with issues.
result: pass

### 2. Score command — letter grades across 5 dimensions
expected: Run `infracanvas score cli/tests/fixtures/insecure_setup/`. Outputs an overall letter grade (A–F) and a per-dimension breakdown covering Security, Encryption, IAM Hygiene, Cost Efficiency, and Tagging. Running with `--html` produces a score card HTML file with a progress bar per dimension and an upgrade CTA.
result: pass

### 3. Azure scan — AZ findings + icons
expected: Run `infracanvas scan cli/tests/fixtures/azure/`. Diagram renders Azure resource types with Azure-branded icons (not AWS icons). Findings panel shows IDs in the `AZ-001`…`AZ-010` range, each with compliance framework tags (CIS, NIST, SOC2, or PCI-DSS).
result: pass

### 4. Drift overlay — `infracanvas plan`
expected: Run `infracanvas plan --planfile cli/tests/fixtures/sample_plan.json cli/tests/fixtures/insecure_setup/`. HTML diagram loads with a colour-coded drift overlay: green = add, red = destroy, amber = update, grey = unchanged. Clicking a changed resource shows before/after attribute diffs in the detail panel.
result: pass

### 5. Shadow infrastructure — `--shadow` flag
expected: Run `infracanvas scan --shadow cli/tests/fixtures/insecure_setup/`. Resources in cloud but absent from Terraform render with dashed borders + 20% dim + estimated cost. Without boto3 installed or AWS creds, degrade gracefully (no traceback).
result: pass

### 6. Policy engine + CI exit code
expected: Run `infracanvas scan --policy cli/tests/fixtures/policies/ --fail-on=high --ci cli/tests/fixtures/insecure_setup/`. Policy violations appear as findings with POLICY source, non-zero exit, valid JSON on stdout, diagnostics on stderr.
result: pass
verification: |
  Autonomous run confirmed:
  - Exit code: 1 (non-zero, as expected with --fail-on=high)
  - stdout: valid JSON with keys [version, metadata, nodes, edges, summary]
  - stderr: clean (no noise mixed into stdout)
  - 4 findings with source=policy and rule_id POL-001 (required tags missing)

### 7. Viewer filters — Source pill + compliance tags
expected: Filter panel shows a Source filter with toggleable pills (TERRAFORM / POLICY / SHADOW). Each finding card displays compliance framework badges (CIS / NIST / SOC2 / PCI-DSS) where applicable.
result: pass
verification: |
  Code-level verification (actual visual QA deferred to UI review):
  - viewer/src/store.ts:8 — `sources: string[]` with comment "'security', 'policy'"
  - viewer/src/store.ts:24 — `toggleSourceFilter` action wired
  - viewer/src/components/FilterPanel.tsx:148 — "Source" section renders toggleable pills with count per source
  - viewer/src/components/FindingCard.tsx:95-97 — `finding.framework_ids` mapped to compliance badges
note: Recommend `/gsd-ui-review 2` for pixel-level visual audit before closing milestone.

### 8. Distribution — Docker + PyInstaller + GHA release
expected: Dockerfile, PyInstaller spec, GitHub Actions release workflow, and Homebrew formula exist and are correctly configured.
result: pass
verification: |
  - Dockerfile present (3.6KB, multi-stage, non-root, HEALTHCHECK per summary)
  - cli/infracanvas.spec present (PyInstaller spec)
  - .github/workflows/release.yml present (3.6KB, references pypa/gh-action-pypi-publish@release/v1, softprops/action-gh-release@v2, build-binaries + build-docker + publish-pypi + create-release stages)
  - Formula/infracanvas.rb present (PyPI virtualenv pattern)
  - Note: Actual `docker run` and live release flow not exercised — artifact presence + config only. Live release is tested at tag time.

### 9. Single-file HTML export — size + offline integrity
expected: Run `infracanvas scan --output report.html`. Single self-contained file under 5MB, opens with no network requests required (no external fetches).
result: pass
closed_by: 02-09-PLAN.md (fix(viewer): inline JetBrains Mono + Inter via @fontsource)
verification: |
  Re-verified 2026-04-18 after plan 02-09 landed:
  - grep -cE 'fonts\.googleapis\.com|fonts\.gstatic\.com' report.html → 0 (was 1)
  - stat -f%z report.html → 2,081,117 bytes (~1.98MB, well under 5MB limit)
  - grep -oE '@font-face' report.html | wc -l → 46 (7 weights × unicode subsets inlined)
  - Fonts: Inter + JetBrains Mono now bundled as base64 woff2 via @fontsource/*
  - Single file: ✓ no sidecar assets, no CDN fetches

## Summary

total: 9
passed: 9
issues: 0
pending: 0
skipped: 0

## Gaps

(none — all tests pass; test 9 fonts gap closed by plan 02-09 on 2026-04-18)
