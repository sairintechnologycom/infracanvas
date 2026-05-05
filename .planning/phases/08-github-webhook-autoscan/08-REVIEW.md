---
phase: 08-github-webhook-autoscan
reviewed: 2026-05-05T13:10:00Z
depth: standard
files_reviewed: 13
files_reviewed_list:
  - backend/app/main.py
  - backend/app/routes/integrations.py
  - backend/tests/api/test_integrations.py
  - dashboard/app/(dashboard)/settings/integrations/IntegrationsPage.test.tsx
  - dashboard/app/(dashboard)/settings/integrations/page.tsx
  - dashboard/app/api/integrations/slack/route.test.ts
  - dashboard/app/api/integrations/slack/route.ts
  - dashboard/components/scans/MetadataHeader.test.tsx
  - dashboard/components/scans/MetadataHeader.tsx
  - dashboard/components/scans/ScansTable.test.tsx
  - dashboard/components/scans/ScansTable.tsx
  - dashboard/lib/types.ts
  - dashboard/vitest.config.ts
findings:
  critical: 0
  warning: 5
  info: 4
  total: 9
status: issues_found
---

# Phase 08: Code Review Report

**Reviewed:** 2026-05-05T13:10:00Z
**Depth:** standard
**Files Reviewed:** 13
**Status:** issues_found

## Summary

Phase 8 adds: (1) a `PATCH /v1/integrations/slack` backend route that saves a Slack webhook URL per team, (2) a Next.js proxy route (`/api/integrations/slack`), (3) a wired Slack form in the integrations settings page, and (4) `Auto-scan` source badges in `MetadataHeader` and `ScansTable`.

The security boundary — SSRF prefix guard + RLS GUC + `require_role` auth gate — is correctly implemented. No blockers were found. However, five warnings were identified ranging from a polling loop whose attempt-cap is silently bypassed on every empty response to a `null` Clerk token reaching the backend as the literal string `"null"`. Four informational findings cover type inconsistencies and duplication.

---

## Warnings

### WR-01: Polling attempt cap is bypassed — backend hang can pin the page indefinitely

**File:** `dashboard/app/(dashboard)/settings/integrations/page.tsx:69-100`

**Issue:** The second `useEffect` (post-install hydration poll) declares `[installSuccess, installations]` as its dependency array. Every time `fetchInstallations()` returns an empty list, it calls `setInstallations(data)` where `data` is a freshly allocated `[]`. Because `useState` uses referential equality, a new `[]` reference always triggers a React re-render, which in turn cleans up the effect (cancelling the interval and resetting the closure over `attempts`) and immediately re-creates it with `attempts = 0`. The result: the `POLL_MAX_ATTEMPTS = 5` cap is never reached so long as the backend keeps returning an empty list — the page polls indefinitely.

**Fix:** Move the interval-with-cap logic out of the reactive effect, or use a `useRef` to persist the attempts count across re-renders so it is not reset on each empty response:

```tsx
const pollAttemptsRef = useRef(0)

useEffect(() => {
  if (!installSuccess) return
  if (installations === null) return
  if (installations.length > 0) return

  // Do NOT start a new interval if already at cap
  if (pollAttemptsRef.current >= POLL_MAX_ATTEMPTS) return

  let cancelled = false
  const id = setInterval(() => {
    if (cancelled) return
    pollAttemptsRef.current += 1
    if (pollAttemptsRef.current > POLL_MAX_ATTEMPTS) {
      clearInterval(id)
      return
    }
    fetchInstallations()
      .then((data) => {
        if (cancelled) return
        setInstallations(data)
        if (data.length > 0) clearInterval(id)
      })
      .catch(() => {})
  }, POLL_INTERVAL_MS)

  return () => {
    cancelled = true
    clearInterval(id)
  }
}, [installSuccess, installations])
```

---

### WR-02: Clerk `getToken()` returns `string | null`; null sent as literal `"Bearer null"` to backend

**File:** `dashboard/lib/backend.ts:25-33`

**Issue:** `getToken()` returns `Promise<string | null>`. When the Clerk session has no active token (e.g. just after sign-out, during SSR without a session, or in certain middleware configurations), `token` is `null`. The header is then constructed as `` `Bearer ${null}` `` which evaluates to `"Bearer null"`. This string passes the `h.lower().startswith("bearer ")` check in `clerk.py` and reaches the JWKS decode path, which raises `InvalidTokenError` and returns 401 — but the error appears as `invalid_token` rather than `missing_bearer`. Callers cannot distinguish "token is absent" from "token is corrupt".

**Fix:** Guard before constructing the header:

```ts
const token = await getToken()
if (!token) {
  throw new Error('401') // triggers the 401 mapping in callers
}
```

---

### WR-03: Silent 200 on UPDATE that matches zero rows (deleted team race)

**File:** `backend/app/routes/integrations.py:48-59`

**Issue:** After the RLS GUC is set, the `UPDATE teams SET slack_webhook_url = :url WHERE id = :id` is executed but the result's rowcount is never checked. If the team row was deleted between `resolve_team_from_clerk_org` (which reads from the DB) and the UPDATE (a TOCTOU window), the UPDATE affects zero rows and the endpoint still returns `200 {"message": "Slack webhook saved"}`. The caller believes the URL was saved when it was silently discarded.

**Fix:** Check the rowcount and raise on zero:

```python
result = await session.execute(
    text("UPDATE teams SET slack_webhook_url = :url WHERE id = :id"),
    {"url": body.webhook_url, "id": str(team.id)},
)
if result.rowcount == 0:
    raise HTTPException(status.HTTP_404_NOT_FOUND, "team_not_found")
```

---

### WR-04: `route.test.ts` never asserts backendFetch is called with the correct path or body

**File:** `dashboard/app/api/integrations/slack/route.test.ts:14-36`

**Issue:** Both tests mock `backendFetch` to control the return value but never assert what arguments it was called with. The test therefore passes even if `route.ts` calls `backendFetch('/v1/wrong/path', { method: 'GET' })`. The proxy's contract (forwarding to `/v1/integrations/slack` via PATCH with the original body) is untested.

**Fix:** Add a call assertion in the happy-path test:

```ts
it('returns 200 with message on backend success', async () => {
  vi.mocked(backendFetch).mockResolvedValueOnce({ message: 'Slack webhook saved' })
  const req = new Request('http://localhost/api/integrations/slack', {
    method: 'PATCH',
    body: JSON.stringify({ webhook_url: 'https://hooks.slack.com/services/T/B/x' }),
    headers: { 'Content-Type': 'application/json' },
  })
  const res = await PATCH(req)
  expect(res.status).toBe(200)
  expect(vi.mocked(backendFetch)).toHaveBeenCalledWith(
    '/v1/integrations/slack',
    expect.objectContaining({ method: 'PATCH' }),
  )
  const data = await res.json()
  expect(data.message).toBe('Slack webhook saved')
})
```

---

### WR-05: Slack form input missing `required` attribute — empty URL silently reaches the backend

**File:** `dashboard/app/(dashboard)/settings/integrations/page.tsx:142-147`

**Issue:** The `<input type="url" name="slack_webhook" ...>` element has no `required` attribute and no client-side empty-string check. Clicking "Save webhook URL" with a blank input submits `{ webhook_url: "" }` to the proxy, which forwards it to the backend. The backend rejects it with 422 (empty string fails the `startswith` guard), but the UX is poor — the user sees a generic error rather than "please enter a URL". The correct fix is a client-side guard, not relying on the server round-trip.

**Fix:**

```tsx
<input
  type="url"
  name="slack_webhook"
  required
  placeholder="https://hooks.slack.com/..."
  ...
/>
```

Or add an explicit check before the `fetch` call:

```ts
const webhookUrl = (formData.get('slack_webhook') as string).trim()
if (!webhookUrl) {
  setSlackError('Please enter a Slack webhook URL')
  setSlackSaving(false)
  return
}
```

---

## Info

### IN-01: `ScanListItem.source` includes phantom value `'github_webhook'` never emitted by backend

**File:** `dashboard/lib/types.ts:26`

**Issue:** `source` is typed as `'cli' | 'manual' | 'github_webhook' | 'github' | 'webhook' | null`. A search of all backend code finds no path that writes `'github_webhook'`; push-triggered scans always write `'webhook'` (see `backend/app/routes/webhooks.py:193`). The phantom value was presumably added defensively but it clutters the discriminated union, and `ScansTable.SourceCell` handles `'github_webhook'` by rendering the GitHub icon (line 56) rather than the Auto-scan badge — inconsistent with `MetadataHeader` which only checks `=== 'webhook'` (line 77). If the backend ever does start writing `'github_webhook'`, the Auto-scan badge will silently fail to appear.

**Fix:** Either remove `'github_webhook'` from the union if the backend never emits it, or ensure both `MetadataHeader` and `SourceCell` treat it identically:

```ts
source: 'cli' | 'manual' | 'github' | 'webhook' | null
```

---

### IN-02: `ScanGetResp.source` is typed `string | null` — loses discriminated union narrowing

**File:** `dashboard/lib/types.ts:51`

**Issue:** `ScanGetResp.source` is `string | null` while `ScanListItem.source` is the narrow union. `MetadataHeader` receives a `ScanGetResp` and compares `scan.source === 'webhook'` — this compiles but TypeScript cannot catch a typo like `'Webhook'` or a future refactor that renames the value. The type should be the same union as `ScanListItem.source`.

**Fix:**

```ts
source: ScanListItem['source']
```

---

### IN-03: `ScoreGradePill` component is duplicated verbatim across two files

**File:** `dashboard/components/scans/ScansTable.tsx:14-29` and `dashboard/components/scans/MetadataHeader.tsx:10-25`

**Issue:** `ScoreGradePill` is defined identically in both `ScansTable.tsx` and `MetadataHeader.tsx` — same props, same grade-to-class mapping, same JSX. Any future change to grade thresholds or color classes must be applied in two places.

**Fix:** Extract to a shared module, e.g. `dashboard/components/scans/ScoreGradePill.tsx`, and import from both consumers.

---

### IN-04: `backendFetch` comment says "client-import-safe" but dynamic import of `@clerk/nextjs/server` is server-only

**File:** `dashboard/lib/backend.ts:11-15`

**Issue:** The doc comment claims the module is "client-import-safe" because `@clerk/nextjs/server` is dynamically imported. However, a dynamic `import()` in a `'use client'` component running in the browser will fail at runtime with a module-not-found error because `@clerk/nextjs/server` is not browser-compatible code — dynamic imports do not neutralize the server-only constraint. The comment creates a false sense of safety. `backendFetch` is only safe to call from Next.js Route Handlers and Server Components.

**Fix:** Remove the misleading claim from the comment, or add a server-only guard:

```ts
// At top of file:
import 'server-only'
```

This causes a clear build error if the module is ever imported in a client component, rather than a runtime failure.

---

_Reviewed: 2026-05-05T13:10:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
