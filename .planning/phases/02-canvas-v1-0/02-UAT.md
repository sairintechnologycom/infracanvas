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
result: issue
reported: "Exported HTML fetches https://fonts.googleapis.com at load time (Google Fonts CDN). Violates 'zero external fetches' criterion. File size 469KB (well under 5MB). All other URLs in the bundle are either SVG/XML namespaces (not fetched), comment/attribution text inside bundled JS (reactflow.dev, tailwindcss.com, pro.reactflow.dev), React error-decoder URLs (only hit on error), or the infracanvas.dev founding CTA (loaded only on user click)."
severity: minor
verification: |
  - Size: 469KB (✓ well under 5MB limit)
  - Single file: ✓ no sidecar assets
  - Network dependency found: `<link href='https://fonts.googleapis.com/css2?family=JetBrains+Mono...&family=Inter...' rel='stylesheet'>` — loaded unconditionally at page load
  - Impact: Offline viewing falls back to system fonts (still functional, looks different). Air-gapped / secure envs may block the request entirely. Counts against "zero deps" marketing.

## Summary

total: 9
passed: 8
issues: 1
pending: 0
skipped: 0

## Gaps

- truth: "Exported HTML must be self-contained with no external network fetches (Phase 1 success criterion: 'opens in any browser with zero dependencies')"
  status: failed
  reason: "User reported: Exported HTML fetches https://fonts.googleapis.com CDN at load — viewer/index.html or build pipeline injects a Google Fonts <link> tag (JetBrains Mono + Inter)"
  severity: minor
  test: 9
  artifacts:
    - /tmp/uat_report.html (repro: infracanvas scan --output /tmp/uat_report.html cli/tests/fixtures/prod_infra/)
    - viewer/index.html (likely source of Google Fonts <link>)
    - viewer/src/index.css (may reference font-family: Inter, JetBrains Mono)
  missing:
    - Inline self-hosted font files in the bundle, OR fallback to system-font stack only (font-family: -apple-system, 'Segoe UI', ...), OR a build flag `--no-fonts` for offline mode.
  fix_hint: |
    Options ranked by cost:
    1. (cheapest) Remove Google Fonts <link> from viewer/index.html; update CSS font-family to system-font stack. Marketing-accurate, loses JetBrains Mono/Inter aesthetic.
    2. Inline fonts as base64 in the bundled CSS via vite-plugin-singlefile or similar — keeps aesthetic, slightly larger bundle (+~200KB likely), fully offline.
    3. Use @fontsource/inter + @fontsource/jetbrains-mono npm packages so Vite bundles the woff2 files instead of fetching from CDN.
