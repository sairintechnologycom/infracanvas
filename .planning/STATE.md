---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: Hardening + SaaS Dashboard + CostLens + FlowMap 3b
status: ready
last_updated: "2026-05-03T09:10:00.000Z"
last_activity: 2026-05-03 -- Phase 7.5 Plan 01 complete (Wave 0 foundation: git in Dockerfile, httpx/redis/fakeredis pins, GitHub App settings fields + conftest stubs, shadcn Command primitive)
progress:
  total_phases: 19
  completed_phases: 12
  total_plans: 102
  completed_plans: 82
  percent: 80
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-20 — v1.1 started)

**Core value:** One command gives you a complete, annotated picture of your hybrid infrastructure — security blind spots, network path asymmetry, drift, and shared cost — across AWS, Azure, and physical data centres.
**Current focus:** Phase 7.5 — github-repo-connector (planned; ready to execute)

## Current Position

Milestone: v1.1 — started 2026-04-20
Phase: 7.5 — 11 PLAN.md files written across 7 waves; plan-checker PASSED (iter 1)
Plan: 1/11 (07.5-01 complete; 07.5-02 next)
Status: In progress (Wave 0 partially complete — Plan 02 next)
Last activity: 2026-05-03 -- Phase 7.5 Plan 01 closed (4 commits: 033fc9b chore deps+Dockerfile, bb841c3 RED settings tests, 260cf6d GREEN settings + conftest stubs, 6bd29f4 shadcn command primitive). 7/7 settings tests pass; 95 tests collected clean; 183/183 dashboard tests pass.

## Accumulated Context

### Roadmap Evolution

- 2026-04-20: Milestone v1.1 opened (continuing phase numbering from v1.0's 3.5)
- 2026-04-20: v1.0 post-ship E2E wiring review surfaced 4 fixes → added as WRG-01..04, scoped as first hardening phase of v1.1
- 2026-04-21: Phase 5.1 inserted after Phase 5: Parser realism + CLI UX (URGENT — local `module {}` resolution gap and noisy CLI output surfaced during Phase 5 manual testing; pre-Phase 6)
- 2026-04-21: Phase 7.5 inserted after Phase 7: GitHub Repo Connector (fills the "connect a repo + pick branch + scan" UX gap before Phase 8 webhooks — GitHub-only MVP, multi-provider deferred to v1.2)
- Phase 7.1 inserted after Phase 7: Phase 7 UI Contract Remediation — close UI-SPEC gaps from 07-UI-REVIEW.md (shadcn init, compare diff list, share toasts/revoke, polish drift) (URGENT)
- 2026-05-02: Phase 7.2 inserted after Phase 7.1: UI Contract Remediation — Live (live audit 07.1-LIVE-UI-REVIEW.md scored 10/24; 14 fixes covering viewer h-screen embed break, singleton store leak in 4 viewer components, /settings 404, sparkline ovals, grade-threshold split, sidebar dead zone) (URGENT — blocks Phase 7.5)

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
- 06-04: Replaced `INSERT ... ON CONFLICT DO NOTHING` with probe-via-`team_by_clerk_org()`-then-INSERT in the Clerk webhook handler. PG's INSERT...ON CONFLICT executor evaluates UPDATE policy WITH CHECK even with DO NOTHING — incompatible with strict per-team UPDATE policy. Probe pattern preserves Svix-replay idempotency without weakening RLS.
- 06-04: Switched `SET LOCAL app.current_team_id = :t` → `SELECT set_config('app.current_team_id', :t, true)` in webhook handlers. asyncpg's wire protocol cannot bind parameters to SET LOCAL. set_config() is the parameter-safe equivalent. (Plan 03's session.py still uses SET LOCAL syntax; will fail when first exercised under bind params — Plan 06-05 follow-up.)
- 06-04: Added psycopg2-binary~=2.9.0 to backend dev extras — Plan 01's conftest needs sync driver for one-shot setup DDL on the testcontainer; was missing.
- Plan 06-05: Stripe-python v15 routes V2 endpoints via StripeClient (not module-level stripe.v2.billing.meter_events.create); switched to client.v2.billing.meter_events.create(params, options).
- Plan 06-05: respx-based Stripe mocking can't intercept v15 V2 calls (uses requests not httpx); use SDK-boundary mocking by replacing stripe_meter._client.
- Plan 06-05: TestClient + production async pool causes 'Future attached to a different loop' on second request; tests use NullPool engine to avoid cross-loop reuse.
- Plan 06-05: Two-step R2 layout — pending/{id}.json (PUT target, no team_id) → server-side copy to teams/{team_id}/scans/{id}.json on commit, then DELETE pending; lifecycle rule GCs abandoned pending/ after 7d (T-06-04 + T-06-05 mitigation).
- Plan 07.1-01: shadcn/ui v4 emits both `@import "tw-animate-css"` AND `@import "shadcn/tailwind.css"` — kept both (legitimate package exports, latter ships data-* custom variants + accordion keyframes from `node_modules/shadcn/dist/tailwind.css`).
- Plan 07.1-01: shadcn init's `add` step overwrites the entire `lib/utils.ts` to land `cn()`; pre-existing helpers (`isUUID()` for T-07-08-01 mitigation) must be re-merged manually after init. Documented for future shadcn version bumps.
- Plan 07.1-01: dashboard/app/layout.tsx unused-import for `Inter` (post Geist migration) blocks `next build` typecheck — out of plan 01 scope, deferred via .planning/phases/07.1-phase-7-ui-contract-remediation/deferred-items.md to a layout-owning plan or the phase verifier cleanup pass.
- Plan 07.5-01: GitHub App settings fields use empty-string defaults (not Optional[str]) — matches existing string-field convention in Settings (stripe_meter_event_name, git_sha) and avoids None-coercion in downstream auth helpers. Real values come from Fly secrets in dev/prod; tests override via conftest.py env-stub block.
- Plan 07.5-01: shadcn `add command` did NOT overwrite lib/utils.ts (cn helper already present from Phase 7.1-01) — different from the 07.1-01 init step which DID overwrite. Documented for future shadcn add invocations: `add` only overwrites when the file is missing or differs structurally.
- Plan 07.5-01: pre-existing `TS6133: 'screen' unused` in dashboard/__tests__/scan-filters.test.tsx (introduced 90852b6 / Phase 7.1-03) deferred via .planning/phases/07.5-github-repo-connector/deferred-items.md — out-of-scope for Plan 07.5-01 per executor SCOPE BOUNDARY rule.

### Pending Todos

- Run `/gsd-plan-phase 4` once REQUIREMENTS.md + ROADMAP.md are written

### Blockers/Concerns (carried into v1.1)

- [Phase 3b]: DC Agent CAB approval timeline (4–12 weeks) is critical path
- [Phase 3b]: Cisco NETCONF compatibility matrix unknown
- [Phase 4]: Viewer extraction to shared package is load-bearing; divergence creates long-term maintenance liability

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260501-aw7 | Fix React Flow zustand provider error on scan detail page | 2026-05-01 | 4cfd658 | [260501-aw7-fix-react-flow-zustand-provider-error-on](./quick/260501-aw7-fix-react-flow-zustand-provider-error-on/) |
| 260502-tra | Fix sparkline width bug — wrapper div in Sparkline.tsx | 2026-05-02 | 373b0d9 | [260502-tra-fix-sparkline-width-bug-wrapper-div-in-s](./quick/260502-tra-fix-sparkline-width-bug-wrapper-div-in-s/) |

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

Last session: 2026-05-03T09:10:00.000Z
Milestone: v1.1 in flight
Resume: Phase 07.5 Plan 02 (Wave 0 schema: github_installations table + scans columns + ORM + test fixtures + alembic upgrade — depends on Plan 01's settings fields and fakeredis dev dep)

**Planned Phase:** 7.5 (GitHub Repo Connector) — 11 plans — 2026-05-03
**Plan 07.5-01 closed:** 2026-05-03T09:10Z (4 commits: 033fc9b chore deps+Dockerfile, bb841c3 RED settings tests, 260cf6d GREEN settings + conftest stubs, 6bd29f4 shadcn command primitive). 7/7 settings tests pass; 95 tests collected clean; 183/183 dashboard tests pass. Pre-existing scan-filters.test.tsx tsc warning deferred (out-of-scope).
