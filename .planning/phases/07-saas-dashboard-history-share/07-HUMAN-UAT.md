---
status: partial
phase: 07-saas-dashboard-history-share
source: [07-VERIFICATION.md]
started: 2026-04-29T07:00:00Z
updated: 2026-04-29T07:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Live Clerk sign-in to /scans
expected: Authenticated user lands on /scans, sees their team rows; unauthenticated request redirects to Clerk sign-in
result: [pending]

### 2. Open scan detail at /scans/{id}
expected: MetadataHeader renders branch/commit/score; embedded DiagramCanvas mounts and renders the resource graph from R2 JSON
result: [pending]

### 3. Compare flow from scan detail
expected: ScanPickerModal opens, lists recent scans; selecting one navigates to /scans/compare?a=&b= with diff summary + DiffNodeList rendered
result: [pending]

### 4. Share link round-trip (incognito)
expected: /share/{token} renders branded read-only viewer (no auth). If password is set, PasswordGate renders with zero scan metadata until password verified.
result: [pending]

### 5. Responsive viewports
expected: 1440px → full sidebar (220px), all columns. 1280–1080px → sidebar collapses to 48px icons. <768px → sidebar hidden behind hamburger; ScansTable Source column hidden below 1024px.
result: [pending]

### 6. alembic upgrade head against dev Neon DB
expected: Migrations 005 (scan metadata columns) and 006 (share_links table + share_link_by_token() SECURITY DEFINER fn) apply cleanly with no errors. **BLOCKING:** without this, share-link endpoints fail at runtime in dev/prod.
result: [pending]

### 7. Home dashboard with seeded scans
expected: ScoreCard, ScoreSparkline, TopFindings, RecentScansTable populate from /v1/scans?limit=10
result: [pending]

## Summary

total: 7
passed: 0
issues: 0
pending: 7
skipped: 0
blocked: 0

## Gaps
