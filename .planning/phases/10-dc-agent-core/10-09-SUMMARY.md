---
phase: 10
plan: "09"
subsystem: dc-agent-core
tags: [cab, security, docs, sbom, stride, dca-09, enterprise]
dependency_graph:
  requires: ["10-02", "10-03", "10-04", "10-05", "10-06", "10-07", "10-08"]
  provides:
    - "agent/docs/cab/README.md (packet index + reading order)"
    - "agent/docs/cab/architecture.md (Mermaid system diagram + systemd unit + outbound-only network statement)"
    - "agent/docs/cab/dataflow.md (per-datum trust boundary classification)"
    - "agent/docs/cab/threat-model.md (43 STRIDE entries consolidating T-10-NN-MM IDs)"
    - "agent/docs/cab/sbom.cyclonedx.json (CycloneDX 1.6, 8 components, SHA-256 hashes)"
    - "agent/docs/cab/known-limitations.md (L-1..L-N with severity + remediation paths)"
    - "agent/docs/cab/operator-runbook.md (chmod 600 + systemd + firewalld/iptables + proxy)"
  affects:
    - "Phase 11+ (FlowMap path computation) — CAB packet sets baseline; new threats added to existing register"
    - "Release tagging — SBOM regeneration belongs in release.yml after every git tag"
tech_stack:
  added:
    - "cyclonedx-gomod v1.10.0 (developer tool — installed via GOBIN, not vendored)"
  patterns:
    - "Single-doc-per-concern packet structure (architecture / dataflow / threat / SBOM / limitations / runbook)"
    - "STRIDE register table with one row per consolidated T-10-NN-MM threat ID"
    - "Mermaid system diagrams embedded in markdown so reviewers see structure without external tools"
    - "Severity-rated risk-acceptance table at end of known-limitations.md (CISO-view summary)"
key_files:
  created:
    - "agent/docs/cab/README.md (70 lines)"
    - "agent/docs/cab/architecture.md (119 lines)"
    - "agent/docs/cab/dataflow.md (107 lines)"
    - "agent/docs/cab/threat-model.md (162 lines)"
    - "agent/docs/cab/sbom.cyclonedx.json (~9.7 KB)"
    - "agent/docs/cab/known-limitations.md (201 lines)"
    - "agent/docs/cab/operator-runbook.md (259 lines)"
decisions:
  - "Used cyclonedx-gomod `app` mode (not `mod`) — produces an SBOM scoped to the actual binary's transitive closure (8 components), excluding test-only deps like testify. `mod` mode would have inflated the SBOM with build-time-only dependencies, which is wrong for what an enterprise reviewer is approving."
  - "cyclonedx-gomod v1.10.0 invocation differs from Plan 10-08's release.yml example: the working form is `cyclonedx-gomod app -licenses -json -output ... -main cmd/infracanvas-agent .` (positional is module path; main is relative). Plan 10-08's release.yml + agent/Makefile must be updated before the next tag — tracked as a follow-up below."
  - "InsecureIgnoreHostKey (L-1) documented honestly with v1.2 known_hosts upgrade path rather than hidden. Trust-assumption language is 'no untrusted hosts on the management VLAN' — some Fortune-500 CISOs may reject this baseline; v1.2 is the gating ramp before broad deployment."
  - "Risk-severity ratings in known-limitations.md (Medium / Medium-High / Low-Medium / Low) are CISO-view editorial judgments, not derived from a formal risk-scoring framework. Reviewers will likely re-rate per their own framework — that's expected; we're providing a starting position, not a final score."
  - "Mermaid diagrams chosen over PNG/SVG attachments — markdown-native, version-controllable, regeneratable. GitHub renders them in the web UI, and most procurement portals accept markdown. SVG-export remains an option if a reviewer demands it."
  - "Packet does not include a vulnerability-disclosure timeline or external pen-test results — those belong with v1.0 GA, not Phase 10. README explicitly notes this is a Phase 10 baseline packet."
metrics:
  duration: "~10m subagent draft + orchestrator review"
  completed_date: "2026-05-10"
  tasks_completed: 1
  tasks_total: 1
  files_created: 7
  files_modified: 0
  tests_green: 0
  commits: 2
---

# Phase 10 Plan 09: CAB Security Review Packet (DCA-09) Summary

The InfraCanvas DC Agent CAB packet shipped with Phase 10. Six markdown documents and one CycloneDX 1.6 SBOM in `agent/docs/cab/` give Fortune-500 procurement security reviewers everything they need to assess a DC site agent installation: architecture, data classification, STRIDE threat register, software bill of materials, known limitations with remediation paths, and a step-by-step deployment runbook.

## What Was Built

### Single artifact group commit

**Commit:** `ea3b8ad` — six markdown documents + SBOM written and committed atomically.

| Path | Lines | Purpose |
|------|------:|---------|
| `agent/docs/cab/README.md` | 70 | Packet index + reading order for reviewers |
| `agent/docs/cab/architecture.md` | 119 | Mermaid system diagram, component descriptions, systemd unit template, outbound-only network statement |
| `agent/docs/cab/dataflow.md` | 107 | Trust-boundary classification of every datum (device creds, routes, flows, site_token) |
| `agent/docs/cab/threat-model.md` | 162 | STRIDE register consolidating 43 `T-10-NN-MM` threat IDs from plans 10-02..10-08 |
| `agent/docs/cab/sbom.cyclonedx.json` | 9.7 KB | CycloneDX 1.6, 8 components, SHA-256 hashes per component |
| `agent/docs/cab/known-limitations.md` | 201 | L-1..L-N limitations with severity + remediation paths (InsecureIgnoreHostKey, plaintext credentials, no token rotation) |
| `agent/docs/cab/operator-runbook.md` | 259 | Step-by-step deploy: `chmod 600`, systemd unit, firewalld/iptables rules, HTTPS_PROXY troubleshooting |

**Markdown total: 918 lines.** Mermaid diagrams in architecture.md and dataflow.md render natively in GitHub.

### SBOM generation

Generated with `cyclonedx-gomod v1.10.0 app` mode targeting `agent/cmd/infracanvas-agent`. The `app` mode produces an SBOM scoped to the actual binary's transitive closure (excluding test-only deps like `testify`).

**Working invocation** (run from `agent/`):

```bash
$HOME/go/bin/cyclonedx-gomod app -licenses -json \
  -output docs/cab/sbom.cyclonedx.json \
  -main cmd/infracanvas-agent .
```

Plan 10-08's `release.yml` and `agent/Makefile` reference an older invocation (`cyclonedx-gomod app ./cmd/infracanvas-agent`) that no longer works on v1.10.0 — see follow-ups below.

## Reviewer hotspots flagged

The drafting agent flagged five places where an enterprise reviewer should focus first. These are documented here so future sessions can pick up review feedback without rediscovering them:

1. **threat-model.md T-10-02-07 repudiation disposition** — relies on "Phase 11+ adds DB persistence." Disposition will need re-evaluation once Phase 11 is roadmapped.
2. **known-limitations.md L-1 (InsecureIgnoreHostKey)** — single biggest reviewer-stopper. Language is "trust assumption is no untrusted hosts on the management VLAN." Some CISOs will reject and demand `known_hosts` before pilot, not before v1.2.
3. **operator-runbook.md Step 5 systemd hardening flags** — `RestrictAddressFamilies=AF_INET AF_INET6` and `LockPersonality=true` were added by the drafting agent (beyond plan scope). Match these against the actual syscall surface in production smoke tests before first external circulation.
4. **threat-model.md T-10-08-05 (CGO_ENABLED grep gate)** — text describes the 10-08 release.yml control. Confirm wording matches the gate that actually shipped.
5. **sbom.cyclonedx.json metadata.component.version** — currently a pseudo-version (`v1.0.1-0.20260419161329-d51d3d5b9c80`) because the agent module is untagged. Regenerate after `git tag v0.1.0` so the metadata version is real semver.

## Editorial liberty (beyond plan scope)

Items the drafting agent added that Plan 10-09 did not specify:

- **architecture.md:** `RestrictAddressFamilies` and `LockPersonality` systemd hardening flags.
- **known-limitations.md:** CISO-view severity table at the bottom (Medium / Medium-High / Low-Medium / Low ratings).
- **operator-runbook.md:** firewalld rich-rule example (alongside iptables) and HTTPS_PROXY/corporate-trust-store troubleshooting row.
- **threat-model.md:** "Future-Phase Threats" closer section mapping accepted residuals to future tiers.
- **README.md:** explicit "How to review this packet" reading order.

All accepted as-is by the user during this session.

## Verification

The CAB packet is a docs/SBOM artifact set — there are no tests to add. Verification is structural:

```bash
$ ls agent/docs/cab/
README.md  architecture.md  dataflow.md  known-limitations.md
operator-runbook.md  sbom.cyclonedx.json  threat-model.md

$ jq -r '.bomFormat, .specVersion, (.components | length)' agent/docs/cab/sbom.cyclonedx.json
CycloneDX
1.6
8

$ grep -c "T-10-" agent/docs/cab/threat-model.md  # consolidates plans 10-02..10-08 threat IDs
43

$ grep -c "mermaid" agent/docs/cab/architecture.md
1

$ grep -c "InsecureIgnoreHostKey" agent/docs/cab/known-limitations.md
≥1

$ grep -c "chmod 600" agent/docs/cab/operator-runbook.md
≥1
```

## Follow-ups (tracked outside Phase 10)

1. **Update Plan 10-08's `release.yml` and `agent/Makefile`** to use the working `cyclonedx-gomod v1.10.0 app` invocation. Plan 10-08 Task 3 (smoke test tag push to GHA) is already deferred — bundle this fix into that work before cutting v0.1.0.
2. **Add a `LICENSE` file at `agent/LICENSE`** so cyclonedx-gomod's `WRN no licenses detected` warning goes away. The umbrella InfraCanvas repo has a license at root; the agent module needs its own copy or symlink.
3. **Regenerate SBOM after `git tag v0.1.0`** so `metadata.component.version` reflects a real semver, not a pseudo-version.
4. **Address the 5 reviewer hotspots above** before circulating the packet to the first Fortune-500 prospect.

## Phase 10 closes here

With Plan 10-09 drafted, accepted by the user, and SUMMARY-closed, all 9 plans in Phase 10 (DC Agent Core) are complete:

| Plan | Status |
|------|--------|
| 10-01 Go module scaffold + Nyquist stubs | ✓ |
| 10-02 Backend dc_sites + site-token auth | ✓ |
| 10-03 Cobra CLI + config loader + daemon harness | ✓ |
| 10-04 NETCONF collector | ✓ |
| 10-05 SSH + config-import collectors | ✓ |
| 10-06 NetFlow ring buffer + UDP listener | ✓ |
| 10-07 Push client + goflow2/v2 + main.go wiring | ✓ |
| 10-08 GHA CI + cross-compile matrix | ✓ (Task 3 tag-push smoke test deferred) |
| 10-09 CAB security packet | ✓ (this plan) |

DC Agent Core is feature-complete. Next: phase verification (gsd-verifier or inline), STATE update to mark Phase 10 closed, and routing to Phase 11 planning when ready.
