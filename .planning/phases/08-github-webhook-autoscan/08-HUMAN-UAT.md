---
status: partial
phase: 08-github-webhook-autoscan
source: [08-VERIFICATION.md]
started: 2026-05-05T13:15:00Z
updated: 2026-05-05T13:15:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Live push triggers scan within 30 s (SC-1)
expected: Push a commit to a connected GitHub repo → GitHub App delivers webhook to `/v1/webhooks/github` → `scan_repo` taskiq job queues → scan completes and scan row appears in DB within 30 seconds of the push
result: [pending]

### 2. Slack alert fires in real channel on Critical finding (SC-3)
expected: When a scan triggered by a webhook push produces ≥ 1 Critical finding AND the team has a valid `slack_webhook_url` configured → httpx POST to `slack_webhook_url` fires → Slack message appears in the configured channel
result: [pending]

## Summary

total: 2
passed: 0
issues: 0
pending: 2
skipped: 0
blocked: 0

## Gaps
