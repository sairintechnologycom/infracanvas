---
phase: 02-canvas-v1-0
plan: "08"
subsystem: distribution
tags: [docker, pyinstaller, github-actions, homebrew, release-pipeline]
dependency_graph:
  requires: ["02-06", "02-07"]
  provides: [docker-image, standalone-binaries, homebrew-formula, release-workflow]
  affects: [dst-01, dst-02]
tech_stack:
  added: [PyInstaller, docker-buildx, pypa-gh-action-pypi-publish, softprops-action-gh-release]
  patterns: [multi-stage-docker-build, github-actions-matrix, pypi-virtualenv-formula]
key_files:
  created:
    - Dockerfile (multi-stage, non-root, HEALTHCHECK, OCI labels)
    - cli/infracanvas.spec (PyInstaller spec with hiddenimports + datas)
    - .github/workflows/release.yml (consolidated release workflow)
    - .github/update-homebrew.sh (release-time formula updater)
  modified:
    - Formula/infracanvas.rb (switched to PyPI virtualenv pattern)
decisions:
  - "Consolidated cli-release.yml + cli-binaries.yml into single release.yml — avoids workflow_run coupling and race conditions"
  - "Homebrew formula uses PyPI tarball (not GitHub tarball) — decoupled from repo structure, standard for pip-installable tools"
  - "publish-pypi job uses id-token:write for OIDC Trusted Publisher — no API token secret needed"
  - "macos-14 runner used for arm64 (Apple Silicon native) — PyInstaller cannot cross-compile"
metrics:
  duration: ~10min
  completed: "2026-04-16"
  tasks_completed: 3
  files_created: 4
  files_modified: 1
requirements: [DST-01, DST-02]
---

# Phase 02 Plan 08: Docker + Release Pipeline Summary

Docker image, PyInstaller spec, and GitHub Actions release workflow for multi-arch binary distribution across Linux amd64, macOS arm64, and Windows x64.

## Tasks Completed

| Task | Commit | Description |
|------|--------|-------------|
| Task 1: Dockerfile + PyInstaller spec | `1bd1929` | Multi-stage Dockerfile, non-root user, HEALTHCHECK; PyInstaller spec with all hiddenimports |
| Task 2: GitHub Actions release.yml | `6c79a4d` | Consolidated release workflow — 3-platform binary matrix, Docker buildx, PyPI OIDC publish |
| Task 2B: Homebrew formula | `7b79230` | Updated Formula/infracanvas.rb to PyPI virtualenv pattern; added update-homebrew.sh helper |

## What Was Built

### Dockerfile (updated)
- Multi-stage build: `builder` stage installs from local `./cli`, final stage copies site-packages + binary
- Copies `viewer/dist/` for HTML export template support
- Runs as non-root `infracanvas` user (T-02-17 mitigation)
- HEALTHCHECK via `infracanvas --version`
- OCI image labels (title, description, source, license)

### cli/infracanvas.spec (new)
- PyInstaller one-file spec for standalone binary
- Includes `infracanvas/security/rules` YAML in datas (required at runtime)
- Conditionally includes `viewer/dist` if built
- Full hiddenimports list covering all infracanvas submodules + dependencies
- UPX compression enabled

### .github/workflows/release.yml (new)
- Triggers on `v*` tag push
- `build-binaries` job: matrix of 3 platforms (ubuntu-latest/amd64, macos-14/arm64, windows-latest/x64)
  - Each platform: installs deps, builds viewer, runs `pyinstaller infracanvas.spec`, uploads artifact
- `build-docker` job: docker/setup-buildx + docker/build-push-action → GHCR (linux/amd64,linux/arm64)
- `publish-pypi` job: builds viewer, copies template, hatchling build, pypa publish with OIDC
- `create-release` job: downloads all 3 binary artifacts, creates GitHub Release with notes
- Replaces the two-workflow `cli-release.yml` + `cli-binaries.yml` pattern

### Formula/infracanvas.rb (updated)
- Switched from GitHub tarball approach to PyPI source distribution
- Uses `Language::Python::Virtualenv` + `virtualenv_install_with_resources`
- VERSION and SHA256_PLACEHOLDER markers for release-time substitution
- Test block verifies `--help` output

### .github/update-homebrew.sh (new)
- Helper script for release automation: `./update-homebrew.sh <version> <sha256>`
- `sed` substitution of VERSION and SHA256_PLACEHOLDER in formula

## Deviations from Plan

### Auto-decisions (no architectural impact)

**1. publish-pypi job adds id-token:write permission**
- Found during: Task 2
- Issue: `pypa/gh-action-pypi-publish` OIDC Trusted Publisher requires `id-token: write` permission at the job level (not just top-level `permissions`)
- Fix: Added `permissions: { contents: write, id-token: write }` to `publish-pypi` job to match existing `cli-release.yml` pattern
- Files modified: `.github/workflows/release.yml`
- Commit: `6c79a4d`

**2. Homebrew formula retains existing desc text**
- Found during: Task 2B
- Issue: Existing formula had a more descriptive `desc` than the plan template ("Scan Terraform code..." vs "Interactive Terraform architecture diagrams...")
- Fix: Used plan's desc text ("Interactive Terraform architecture diagrams with security scoring") to match PyPI package description
- Files modified: `Formula/infracanvas.rb`
- Commit: `7b79230`

**3. Existing cli-release.yml and cli-binaries.yml left in place**
- Found during: Task 2
- Issue: Project had two existing workflows. Plan calls for a new `release.yml` consolidation.
- Fix: Created new `release.yml` without deleting existing files — deletion is a human decision
- Impact: Three workflow files exist; human should disable/delete old ones after verifying new workflow

## Known Stubs

- `Formula/infracanvas.rb` — VERSION and SHA256_PLACEHOLDER are intentional release-time markers, not runtime stubs. The Homebrew formula cannot be installed until a PyPI release exists and these are substituted.

## Threat Surface

| Flag | File | Description |
|------|------|-------------|
| No new threats | — | T-02-16, T-02-17 mitigated as planned. No unplanned trust boundary changes. |

## Self-Check

- [x] `Dockerfile` exists at project root with multi-stage build
- [x] `cli/infracanvas.spec` exists with PyInstaller configuration
- [x] `.github/workflows/release.yml` exists with 3-platform matrix
- [x] `Formula/infracanvas.rb` exists with PyPI virtualenv pattern
- [x] `.github/update-homebrew.sh` exists and is executable
- [x] Commits `1bd1929`, `6c79a4d`, `7b79230` all present in git log

## Self-Check: PASSED
