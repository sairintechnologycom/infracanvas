---
phase: 8
plan: "08-06"
subsystem: dashboard
tags: [slack, integrations, proxy-route, tdd, form-wiring]
dependency_graph:
  requires: ["08-04"]
  provides: ["PATCH /api/integrations/slack proxy", "Wired Slack form with save/error state"]
  affects: ["dashboard/app/(dashboard)/settings/integrations/page.tsx"]
tech_stack:
  added: []
  patterns: ["Next.js proxy route via backendFetch", "React form state with slackSaving/slackSaved/slackError"]
key_files:
  created:
    - dashboard/app/api/integrations/slack/route.ts
    - dashboard/app/api/integrations/slack/route.test.ts
    - dashboard/app/(dashboard)/settings/integrations/IntegrationsPage.test.tsx
  modified:
    - dashboard/app/(dashboard)/settings/integrations/page.tsx
decisions:
  - Used fireEvent instead of userEvent (user-event not in package.json) — equivalent for this interaction pattern
  - Wired global.fetch mock in form tests with URL-based dispatch to handle concurrent /api/github/installations call
  - Kept `res.json().catch(() => ({}))` in error path to gracefully handle non-JSON error bodies
metrics:
  duration: "~15 minutes"
  completed: "2026-05-05"
  tasks_completed: 2
  files_changed: 4
---

# Phase 8 Plan 06: Slack Proxy Route + Form Wiring Summary

PATCH proxy route forwarding Slack webhook URL to backend, with wired integrations form showing Saving/Saved!/error states.

## What Was Built

**`dashboard/app/api/integrations/slack/route.ts`** — New Next.js route handler that proxies `PATCH /api/integrations/slack` to the backend's `PATCH /v1/integrations/slack` via `backendFetch`. Follows the exact pattern of `from-github/route.ts`: JSON body parse with 400 fallback, status mapping (401/422 preserved, everything else → 500).

**`dashboard/app/(dashboard)/settings/integrations/page.tsx`** — Replaced the `// TODO Phase 8` stub form with a typed `async onSubmit` handler. Three new state variables (`slackSaving`, `slackSaved`, `slackError`) drive button text (`Save webhook URL` → `Saving…` → `Saved!`) and an inline error paragraph with `data-testid="slack-error"`.

**Test coverage:**
- `route.test.ts`: 2 tests — 200 with message on success, 422 preserved from backend throw
- `IntegrationsPage.test.tsx`: 2 tests — submit dispatches correct fetch call + shows Saved!, shows slack-error on 422

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 (TDD RED) | c18871e | test(08-06): add 4 failing tests for Slack proxy route and form behavior |
| 2 (TDD GREEN) | 86205ba | feat(08-06): create Slack proxy route and wire integrations form |

## Verification

All acceptance criteria met:

- `route.ts` exports `PATCH`, calls `backendFetch('/v1/integrations/slack', ...)` — confirmed
- `page.tsx` has no `TODO Phase 8` comment — confirmed (grep returns 0)
- `slackSaving|slackSaved|slackError` count = 8 — confirmed
- `slack-error` testid = 1 — confirmed
- 4/4 vitest tests pass — confirmed
- TypeScript: only pre-existing `scan-filters.test.tsx` TS6133 error (deferred from Plan 01, out of scope)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Replaced userEvent with fireEvent in IntegrationsPage.test.tsx**
- **Found during:** Task 1
- **Issue:** `@testing-library/user-event` is not in `package.json` devDependencies; importing it would fail
- **Fix:** Used `fireEvent.change` + `fireEvent.click` from `@testing-library/react` which is installed. Semantically equivalent for these non-pointer-capture interactions.
- **Files modified:** `dashboard/app/(dashboard)/settings/integrations/IntegrationsPage.test.tsx`
- **Commit:** c18871e

**2. [Rule 2 - Correctness] Added URL-dispatch in form test fetch mock**
- **Found during:** Task 1
- **Issue:** The page also fetches `/api/github/installations` on mount; a single `global.fetch` mock would conflict
- **Fix:** Mock dispatches by URL — installations endpoint returns empty list, slack endpoint returns test response
- **Files modified:** `dashboard/app/(dashboard)/settings/integrations/IntegrationsPage.test.tsx`
- **Commit:** c18871e

## TDD Gate Compliance

- RED gate commit (`test(08-06)`): c18871e — both test files FAIL before implementation
- GREEN gate commit (`feat(08-06)`): 86205ba — all 4 tests PASS

## Known Stubs

None — the Slack form is fully wired. The backend endpoint (`PATCH /v1/integrations/slack`) was created in plan 04 and is not a stub.

## Threat Flags

None — route follows the existing authenticated `backendFetch` pattern (Clerk token forwarded to backend). No new unauthenticated surface introduced.

## Self-Check: PASSED

- `dashboard/app/api/integrations/slack/route.ts` — FOUND
- `dashboard/app/api/integrations/slack/route.test.ts` — FOUND
- `dashboard/app/(dashboard)/settings/integrations/IntegrationsPage.test.tsx` — FOUND
- Commit c18871e — FOUND
- Commit 86205ba — FOUND
