---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: Hardening + SaaS Dashboard + CostLens + FlowMap 3b
status: executing
last_updated: "2026-04-21T10:23:42.666Z"
last_activity: 2026-04-21
progress:
  total_phases: 17
  completed_phases: 8
  total_plans: 43
  completed_plans: 43
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-20 — v1.1 started)

**Core value:** One command gives you a complete, annotated picture of your hybrid infrastructure — security blind spots, network path asymmetry, drift, and shared cost — across AWS, Azure, and physical data centres.
**Current focus:** Phase 05.1 — Parser Realism + CLI UX

## Current Position

Milestone: v1.1 — started 2026-04-20
Phase: 05.1 (Parser Realism + CLI UX) — EXECUTING
Plan: 4 of 4
Status: Ready to execute
Last activity: 2026-04-21

## Accumulated Context

### Roadmap Evolution

- 2026-04-20: Milestone v1.1 opened (continuing phase numbering from v1.0's 3.5)
- 2026-04-20: v1.0 post-ship E2E wiring review surfaced 4 fixes → added as WRG-01..04, scoped as first hardening phase of v1.1
- 2026-04-21: Phase 5.1 inserted after Phase 5: Parser realism + CLI UX (URGENT — local `module {}` resolution gap and noisy CLI output surfaced during Phase 5 manual testing; pre-Phase 6)
- 2026-04-21: Phase 7.5 inserted after Phase 7: GitHub Repo Connector (fills the "connect a repo + pick branch + scan" UX gap before Phase 8 webhooks — GitHub-only MVP, multi-provider deferred to v1.2)

### Decisions

Decisions carried from v1.0 (see PROJECT.md Key Decisions table). Open items affecting v1.1:

- [Phase 3b]: Cisco NETCONF compatibility research needed BEFORE planning DCA-02
- [Phase 3b]: DC Agent enterprise CAB approval takes 4–12 weeks; DCA-09 security packet must be ready early
- [Phase 4]: Extract viewer to shared dual-build package BEFORE any Next.js dashboard work
- [Phase 4]: Use Neon session-mode pooler + dedicated `infracanvas_app` role (no BYPASSRLS) to prevent RLS leakage
- [Phase 4]: Next.js 15 (not 14); taskiq (not arq); Stripe Billing Meters only; netsampler/goflow2/v2 (not goflow)
- [v1.1]: Wiring fixes run BEFORE SaaS work so Phase 4+ builds on a known-good CLI core
- 05.1-02: Committed producer + consumer (hcl.py + module.py + graph/builder.py) in a single atomic commit (de149a8) to preserve the coordinated-edit contract — no intermediate tree state has a consumer reading an unemitted field
- 05.1-02: COUNT_EXPANSION_CAP=1000 — DoS guard applied BEFORE range expansion in _expand_count/_expand_for_each; oversized literals collapse to 1 unresolved node + synthetic parse_errors note (T-05.1-05 mitigation)
- 05.1-03: Three orthogonal output-shape flags (--quiet / --json / --ci) on scan/plan, plus --open on scan/plan/export, resolving PATTERNS.md note 1 --quiet semantic collision without breaking existing --ci contract
- 05.1-03: export command's unconditional webbrowser.open replaced with explicit --open opt-in — minor breaking change, documented in future release notes

### Pending Todos

- Run `/gsd-plan-phase 4` once REQUIREMENTS.md + ROADMAP.md are written

### Blockers/Concerns (carried into v1.1)

- [Phase 3b]: DC Agent CAB approval timeline (4–12 weeks) is critical path
- [Phase 3b]: Cisco NETCONF compatibility matrix unknown
- [Phase 4]: Viewer extraction to shared package is load-bearing; divergence creates long-term maintenance liability

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| v1.0 close (human-gated) | VAL-01..05 Phase 0 campaign (Stripe setup, Typeform live, Reddit/LinkedIn posts, 20 customer conversations, Go/No-Go decision) | Pending human execution — 4–8 week campaign per D-05 | v1.0 close (2026-04-19) |
| v1.0 close (pre-release) | REL-01..04 first PyPI publish + Homebrew tap sync + GHA workflow validation + Show HN submission | Configured, execution pending first semver tag | v1.0 close (2026-04-19) |
| v2 | GCP support (HRZ-05) | Deferred to Year 2 | Init |
| v2 | Pulumi/CDK/Bicep (HRZ-03) | Deferred to Year 2 | Init |
| v2 | Live cloud import (HRZ-01) | Deferred to Year 2 | Init |
| v2 | AI natural language queries (HRZ-02) | Deferred to Year 2 | Init |

## Session Continuity

Last session: 2026-04-21T10:23:35.613Z
Milestone: v1.1 started
Resume: Define REQUIREMENTS.md then spawn gsd-roadmapper to create ROADMAP.md

**Planned Phase:** 5.1 (Parser realism + CLI UX) — 4 plans — 2026-04-21T09:29:39.098Z
