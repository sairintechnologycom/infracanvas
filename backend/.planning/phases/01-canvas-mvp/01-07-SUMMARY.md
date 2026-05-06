---
phase: 01-canvas-mvp
plan: "07"
subsystem: release-packaging
tags: [pypi, homebrew, release, readme, show-hn, licensing]
dependency_graph:
  requires: [01-06]
  provides: [REL-01, REL-02, REL-03, REL-04]
  affects: []
tech_stack:
  added: []
  patterns: [PyPI Trusted Publisher (OIDC), Homebrew formula source-build, Hatchling wheel artifacts]
key_files:
  created:
    - LICENSE
    - SHOW_HN_DRAFT.md
  modified:
    - cli/pyproject.toml
    - .github/workflows/cli-release.yml
    - Formula/infracanvas.rb
    - README.md
decisions:
  - "Homebrew formula uses virtualenv_install_with_resources (source-build) instead of pip install from PyPI to avoid chicken-and-egg on first release"
  - "GHA workflow already correct — only added PyPI Trusted Publisher setup comment, no structural changes needed"
  - "README kept at 151 lines (well under 250 limit) to stay scannable for HN audience"
metrics:
  duration: "~12 minutes"
  completed: "2026-04-16"
  tasks_completed: 3
  files_changed: 6
---

# Phase 01 Plan 07: Release Packaging Summary

**One-liner:** PyPI wheel with viewer template + YAML rules, GHA Trusted Publisher workflow, Homebrew source-build formula, MIT license, Show HN README and submission draft.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | PyPI packaging + GHA workflow + Homebrew formula + LICENSE | 35c0144 | cli/pyproject.toml, .github/workflows/cli-release.yml, Formula/infracanvas.rb, LICENSE |
| 2 | README with installation, quick start, Show HN framing | b59b40c | README.md |
| 3 | Show HN submission draft (REL-04) | cc65606 | SHOW_HN_DRAFT.md |
| 4 | Checkpoint: Visual verification | — | APPROVED 2026-04-16 |

## What Was Built

### cli/pyproject.toml
Added `[tool.hatch.build.targets.wheel]` and `[tool.hatch.build]` artifacts sections so the wheel includes `infracanvas/export/viewer_template.html` and `infracanvas/security/rules/**/*.yaml`. Without this, `pip install infracanvas` would produce a broken CLI that can't export HTML.

### .github/workflows/cli-release.yml
Already had correct structure (`id-token: write`, `pypa/gh-action-pypi-publish`, viewer build step). Added a comment block at the top explaining how to configure PyPI Trusted Publisher at pypi.org before first publish.

### Formula/infracanvas.rb
Replaced the simple `pip install infracanvas==0.1.0` stub with a proper source-build formula: builds viewer (`npm ci && npm run build`), copies `dist/index.html` to `cli/infracanvas/export/viewer_template.html`, then runs `virtualenv_install_with_resources` from the `cli/` directory. Added `depends_on "node" => :build`.

### LICENSE
Created MIT License at repo root (Copyright 2026 InfraCanvas).

### README.md
Rewrote to lead with Report Card mechanic (A–F letter grade, 5 dimensions, credit score framing). Sections: Quick Start (3 steps), Report Card, What You Get, Installation (PyPI/Homebrew/source), Commands table, 15 AWS resource types, 10 security rules table, CI/CD integration, configuration, founding member mention. 151 lines.

### SHOW_HN_DRAFT.md
Show HN submission copy with title "A report card for your Terraform infrastructure". Body opens with credit score metaphor, explains the problem (5-tool correlation fatigue), describes the Report Card mechanic, technical details, and next steps. 242 words (under 300 limit).

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — no UI components or data paths with placeholder values.

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema changes introduced. PyPI Trusted Publisher (OIDC) mitigation for T-01-18 is documented in the workflow comment.

## Self-Check

- [x] `LICENSE` exists: /Users/bhushan/Documents/Projects/Infracanvas/LICENSE
- [x] `SHOW_HN_DRAFT.md` exists: /Users/bhushan/Documents/Projects/Infracanvas/SHOW_HN_DRAFT.md
- [x] `README.md` under 250 lines: 151 lines
- [x] `infracanvas --version` succeeds via .venv12
- [x] Commits 35c0144, b59b40c, cc65606 all exist in git log
- [x] GHA workflow contains `pypa/gh-action-pypi-publish`
- [x] pyproject.toml contains `viewer_template.html` in artifacts

## Self-Check: PASSED
