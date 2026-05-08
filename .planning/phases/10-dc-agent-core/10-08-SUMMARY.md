---
phase: 10
plan: "08"
subsystem: dc-agent-ci
tags: [go, gha, ci, release, cross-compile]
dependency_graph:
  requires: [10-01, 10-03]
  provides: [DCA-08]
  affects: [.github/workflows/ci.yml, .github/workflows/release.yml, agent/Makefile]
tech_stack:
  added: [actions/setup-go@v6]
  patterns: [CGO_ENABLED=0 cross-compile, go test -race, -ldflags version injection via env var]
key_files:
  created:
    - agent/Makefile
  modified:
    - .github/workflows/ci.yml
    - .github/workflows/release.yml
decisions:
  - "AGENT_VERSION env var holds github.ref_name rather than inline expression in run: — secure pattern per GHA injection prevention guide"
  - "Explicit per-artifact download-artifact steps in create-release (instead of wildcard path: artifacts/) — keeps artifact scope explicit"
  - "if-no-files-found: error on upload-artifact@v4 — fail-loud-on-empty-binary, T-10-08-05 mitigation"
  - "Smoke test uses $GITHUB_REF_NAME (env var set by runner) not ${{ github.ref_name }} in shell — same value, no injection risk"
metrics:
  duration: "3 minutes"
  completed: "2026-05-08T07:03:15Z"
  tasks_completed: 2
  tasks_total: 3
  files_modified: 3
---

# Phase 10 Plan 08: GHA CI + Cross-Compile Matrix Summary

Wire the Go agent into the existing CI + release workflows. `test-agent` job in ci.yml runs `go test -race` on every push/PR; `build-agent` matrix job in release.yml cross-compiles `linux/amd64` + `darwin/arm64` with `CGO_ENABLED=0` on `v*` tag push and attaches both binaries to the GitHub Release.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | test-agent job to ci.yml + agent/Makefile | 9326070 | .github/workflows/ci.yml, agent/Makefile |
| 2 | build-agent matrix job to release.yml + extend create-release | 39a6b96 | .github/workflows/release.yml |

**Task 3 (checkpoint:human-verify):** Not executed — requires pushing a real `v*` tag to GitHub Actions. See checkpoint details below.

## Release Job Graph (after additive changes)

```
build-binaries ──┐
build-agent     ──┤──► create-release
build-docker    ──┤
publish-pypi    ──┘
```

`build-agent` runs in parallel with the existing 3 jobs. `create-release.needs` now lists all four.

## Version String Format

The `-ldflags` injection uses:
```yaml
env:
  AGENT_VERSION: ${{ github.ref_name }}
run: |
  go build -ldflags="-s -w -X main.version=${AGENT_VERSION}" \
    -o ../dist/${{ matrix.artifact }} \
    ./cmd/infracanvas-agent
```

When pushing tag `v0.0.0-test10`, `github.ref_name` = `v0.0.0-test10`, `AGENT_VERSION` = `v0.0.0-test10`, and the binary's `version` subcommand will print `v0.0.0-test10`.

**Security deviation from plan spec:** The plan interface spec showed `${{ github.ref_name }}` directly in the `run:` shell string. This was refactored to use an env var `AGENT_VERSION` per the project's GHA security hook requirement (avoid inline `${{ }}` expressions in run: blocks). Functionally identical.

## Deltas from RESEARCH Pattern 7

1. **`if-no-files-found: error` added** to `upload-artifact@v4` — not in Pattern 7 but recommended in plan interfaces spec. Implements T-10-08-05 fail-loud mitigation.
2. **`retention-days: 7` added** — not in Pattern 7. Prevents artifact accumulation on pre-releases.
3. **`fail-fast: false` on matrix** — not in Pattern 7. Allows darwin/arm64 to upload even if linux/amd64 smoke test fails (both binaries independent).
4. **Secure version injection via env var** — Pattern 7 spec used inline expression; env var approach is safer against injection.
5. **Explicit per-artifact download steps** in `create-release` — original release.yml used `path: artifacts/` wildcard to download all. Switched to explicit named downloads for clarity and to avoid any artifact name collision if future plans add more artifacts.

## Operator Notes for Next Real Release

1. Before cutting `v0.X.Y`, push test tag `v0.0.0-test10` (or similar) and verify both agent binaries appear in the release assets.
2. The `v0.0.0-test10` prerelease tag will NOT show as "latest" (semver pre-release suffix) — safe to leave or clean up with `gh release delete v0.0.0-test10 --yes && git push origin --delete v0.0.0-test10 && git tag -d v0.0.0-test10`.
3. The linux/amd64 smoke test (`./dist/infracanvas-agent-linux-amd64 version`) runs automatically in CI to validate the version string. The darwin/arm64 binary cannot be run on `ubuntu-latest` — its correctness is inferred from identical build flags.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Security] Version injection via env var instead of inline expression**
- **Found during:** Task 2
- **Issue:** Project GHA security hook (pre-write hook) blocks workflow files that use `${{ github.context.* }}` inline in `run:` shell strings. The plan interface spec showed `${{ github.ref_name }}` directly in the `go build` shell command.
- **Fix:** Moved `github.ref_name` to an `env: AGENT_VERSION:` block; shell command uses `${AGENT_VERSION}`. `GITHUB_REF_NAME` (runner-set env var) used in smoke test for the same reason.
- **Files modified:** .github/workflows/release.yml
- **Commit:** 39a6b96

## Known Stubs

None. This plan is CI/release configuration only — no data-rendering UI stubs applicable.

## Threat Flags

None. The new surface is a GHA workflow triggered by `push: tags: v*` (push-by-owner only). All threat register items T-10-08-01..05 were addressed:
- T-10-08-01: `go mod verify` step present in both ci.yml and release.yml
- T-10-08-03: TLS-only binary distribution via github.com; SHA-256 SBOM deferred to Plan 10-09
- T-10-08-05: `CGO_ENABLED: 0` literal locked in release.yml (grep gate in acceptance criteria)

## Self-Check: PASSED

| Check | Result |
|-------|--------|
| .github/workflows/ci.yml exists | FOUND |
| .github/workflows/release.yml exists | FOUND |
| agent/Makefile exists | FOUND |
| 10-08-SUMMARY.md exists | FOUND |
| commit 9326070 (ci.yml + Makefile) | FOUND |
| commit 39a6b96 (release.yml) | FOUND |
