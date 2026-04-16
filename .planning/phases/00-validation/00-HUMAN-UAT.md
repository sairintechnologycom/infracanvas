---
status: partial
phase: 00-validation
source: [00-VERIFICATION.md]
started: 2026-04-16T00:00:00.000Z
updated: 2026-04-16T00:00:00.000Z
---

## Current Test

[awaiting human execution — 4-8 week outreach campaign]

## Tests

### 1. Deploy landing page to Vercel
expected: infracanvas.dev loads in browser with all 7 sections, Stripe CTA links to $49/mo checkout, Typeform CTA opens 7-question survey, demo video plays in embed
result: [pending]

### 2. Create Stripe founding member product
expected: "InfraCanvas Founding Member" product at $49/mo recurring USD with a Payment Link created; URL set as NEXT_PUBLIC_STRIPE_PAYMENT_LINK in Vercel env vars
result: [pending]

### 3. Create and publish Typeform survey
expected: Typeform with 7 questions from validation/typeform/questions.md is live; Basic plan ($25/mo) activated before any post goes live; URL set as NEXT_PUBLIC_TYPEFORM_URL in Vercel env vars
result: [pending]

### 4. Record and publish demo video
expected: 2-3 min video following validation/demo/video-script.md with text callouts; uploaded to Loom or YouTube; embed URL set as NEXT_PUBLIC_DEMO_VIDEO_URL in Vercel env vars
result: [pending]

### 5. Execute Reddit warm-up (VAL-01 prerequisite)
expected: Reddit account has 30+ day age and 50+ karma before demo post; 2-4 helpful comments/week in r/devops and r/Terraform with zero InfraCanvas mentions during warm-up
result: [pending]

### 6. Post to community platforms (VAL-01)
expected: Posts live on r/devops (primary), r/Terraform, Terraform Discord, and LinkedIn per D-05 stagger; posts link to infracanvas.dev only
result: [pending]

### 7. Conduct 20 customer conversations (VAL-04)
expected: validation/conversations/tracker.csv has 20+ data rows with all 12 D-13 columns populated; strong_signal scoring applied per scoring-guide.md
result: [pending]

### 8. Document Go/No-Go decision (VAL-05)
expected: Decision documented per validation/go-no-go/decision-framework.md with credit card count and strong signal count; one of: GO (10+ credit cards), GO (50+ signals + 5+ cards), CONDITIONAL GO (50+ signals + 0 cards), EXTEND, or NO-GO
result: [pending]

## Summary

total: 8
passed: 0
issues: 0
pending: 8
skipped: 0
blocked: 0

## Gaps
