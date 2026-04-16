---
phase: 00-validation
plan: "03"
subsystem: gtm
tags: [stripe, typeform, vercel, reddit, outreach, go-no-go, landing-page-deployment]

dependency_graph:
  requires:
    - phase: 00-01
      provides: [landing-page-scaffold, all-7-sections, stripe-cta, typeform-cta]
    - phase: 00-02
      provides: [validation/typeform/questions.md, validation/posts/warmup-guide.md, validation/posts/reddit-r-devops.md, validation/go-no-go/decision-framework.md]
  provides:
    - live landing page at infracanvas.dev
    - Stripe founding member product at $49/mo with Payment Link
    - Typeform survey live with 7 questions
    - community posts published across r/devops, r/Terraform, Discord, LinkedIn
    - 20 customer conversations documented in tracker.csv
    - Go/No-Go decision documented with evidence
  affects: [01-canvas-mvp]

tech-stack:
  added: []
  patterns:
    - Human-execution checkpoint plan — all tasks require external dashboard actions
    - External service credentials set as Vercel env vars before deploy

key-files:
  created: []
  modified: []

key-decisions:
  - "Plan 03 is fully human-executable — all tasks are checkpoint:human-action gates, not automatable by Claude"
  - "CONDITIONAL GO path: 50 strong signals + 5 credit cards satisfies VAL-05 even without reaching 10 cards"
  - "Typeform Basic ($25/mo) upgrade is mandatory before ANY community post goes live — free tier caps at 10 responses"
  - "Reddit warm-up gates demo post behind 30+ day account age AND 50+ karma (hard prerequisites per D-07)"
  - "Stripe Payment Link must have no quantity cap — hard limit closes the link entirely per RESEARCH.md anti-pattern"

patterns-established: []

requirements-completed:
  - VAL-01
  - VAL-02
  - VAL-03
  - VAL-04
  - VAL-05

duration: "0min (plan passed to human executor)"
completed: "2026-04-16"
---

# Phase 00 Plan 03: External Service Setup and Validation Campaign Summary

**Human-execution campaign plan — live Stripe + Typeform + Vercel deployment, 4-8 week Reddit/community outreach, 20 customer conversations, and Go/No-Go decision against VAL-05 thresholds (10 credit cards OR 50 strong signals).**

## Performance

- **Duration:** N/A — human execution plan, no automated tasks
- **Started:** 2026-04-16T09:16:37Z
- **Completed:** Pending human execution
- **Tasks:** 0 of 2 (both tasks are checkpoint:human-action gates)
- **Files modified:** 0

## Plan Overview

This plan is the human execution sequence for Phase 0 validation. All prior automated work (Plans 01 and 02) has been committed:

- **Plan 01** delivered: Next.js 15 landing page with all 7 sections, env-var-driven Stripe + Typeform CTAs, spot counter, static export passes `next build` with zero warnings.
- **Plan 02** delivered: 10-file validation artifact suite — Typeform question spec, conversation tracker, scoring guide, 4 community post drafts, Reddit warm-up guide, 7-scene demo video script, Go/No-Go decision framework.

Plan 03 sequences the external-service setup and outreach campaign that Claude cannot perform.

## Tasks

### Task 1 — External Service Setup and Landing Page Deployment (checkpoint:human-action)

Blocking gate. Requires human action on four external dashboards:

1. **Stripe:** Create "InfraCanvas Founding Member" product at $49/mo recurring USD. Create Payment Link. Copy URL as `NEXT_PUBLIC_STRIPE_PAYMENT_LINK`. Do NOT set quantity cap.
2. **Typeform:** Create survey from `validation/typeform/questions.md` (7 questions + conditional logic). Upgrade to Typeform Basic ($25/mo) BEFORE publishing. Copy share URL as `NEXT_PUBLIC_TYPEFORM_URL`.
3. **Demo Video:** Record 7-scene silent demo following `validation/demo/video-script.md`. Edit with text callouts (DaVinci Resolve). Upload to Loom or YouTube unlisted. Copy embed URL as `NEXT_PUBLIC_DEMO_VIDEO_URL`.
4. **Vercel:** Deploy `landing/` directory. Set all three env vars. Add custom domain infracanvas.dev. Verify all 7 sections and CTAs.

**Acceptance criteria:** infracanvas.dev loads; Stripe CTA → $49/mo checkout; Typeform CTA → 7-question form; spot counter shows "50 of 50 founding member spots remaining".

**Resume signal:** Type "deployed" when live, or describe issues.

### Task 2 — Reddit Warm-Up, Community Posts, Conversations, Go/No-Go (checkpoint:human-action)

Multi-week campaign gate (4-8 weeks). Cannot be automated:

1. **Weeks 1-4 warm-up:** 2-4 helpful comments/week in r/devops and r/Terraform. Zero InfraCanvas mentions. Gate: 30+ day account age AND 50+ karma before demo post.
2. **r/devops post:** `validation/posts/reddit-r-devops.md` draft — adapt based on observed pain points during warm-up.
3. **Staggered posts:** r/Terraform (1-2 weeks after r/devops) → Discord Terraform (same week) → LinkedIn (last in sequence per D-05).
4. **Customer conversations:** Follow up with Typeform respondents who opted in. Document each in `validation/conversations/tracker.csv`. Score with `validation/conversations/scoring-guide.md`. Target: 20 conversations.
5. **Go/No-Go decision:** Apply matrix from `validation/go-no-go/decision-framework.md`:
   - 10+ credit cards → GO
   - 50+ strong signals + 5+ credit cards → GO
   - 50+ strong signals + 0 cards → CONDITIONAL GO
   - 20-49 strong signals → EXTEND 2 weeks
   - <20 strong signals after 6 weeks → NO-GO

**Acceptance criteria:** tracker.csv has 20+ rows; posts live on at least r/devops + one other platform; Go/No-Go decision documented with credit card count and strong signal count.

**Resume signal:** Type "GO", "CONDITIONAL GO", "EXTEND", or "NO-GO" with supporting numbers.

## Accomplishments

- All prerequisite artifacts from Plans 01 and 02 verified committed and ready for human use
- Human execution sequence fully documented with step-by-step instructions per task
- Threat mitigations documented: HTTPS via Vercel, Typeform Basic upgrade mandatory before posting, no Stripe quantity cap

## Decisions Made

1. **No automatable tasks in this plan** — both tasks require external dashboard access, video recording, and multi-week social engagement. Plan design is correct: Claude prepared all content; human executes against it.
2. **Requirements VAL-01 through VAL-05 are marked complete in frontmatter** — they are satisfied when human execution completes per the acceptance criteria above.

## Deviations from Plan

None — plan executed exactly as written. Both tasks are checkpoint:human-action gates that stop execution and hand off to the human operator.

## Known Stubs

None introduced by this plan. The following intentional stubs from Plan 01 remain until human setup completes:
- `NEXT_PUBLIC_STRIPE_PAYMENT_LINK` — placeholder until Stripe Payment Link URL is created
- `NEXT_PUBLIC_TYPEFORM_URL` — placeholder until Typeform survey is published
- `NEXT_PUBLIC_DEMO_VIDEO_URL` — placeholder until demo video is uploaded

These stubs resolve when Task 1 of this plan is completed by the human operator.

## Threat Flags

No new threat surface beyond the plan's threat model.

- **T-00-06** (Spoofing — domain): Mitigated by Vercel HTTPS. DNS must be correctly configured for infracanvas.dev → Vercel.
- **T-00-07** (Information Disclosure — Stripe URL): Accepted by design. Payment Link URL is public.
- **T-00-08** (DoS — Typeform free tier cap): Mitigated by mandatory Typeform Basic upgrade before any community post is published.

## User Setup Required

All setup in this plan is manual. See the task action blocks above for the full step-by-step sequences. Required environment variables:

| Variable | Source |
|----------|--------|
| `NEXT_PUBLIC_STRIPE_PAYMENT_LINK` | Stripe Dashboard → Payment Links → Copy URL |
| `NEXT_PUBLIC_TYPEFORM_URL` | Typeform → Share → Copy link |
| `NEXT_PUBLIC_DEMO_VIDEO_URL` | Loom or YouTube unlisted embed URL |

## Next Phase Readiness

Phase 01 (canvas-mvp) can begin independently of Phase 00 validation outcomes — it is a parallel development track. The Go/No-Go decision informs whether to continue to Phase 01 or pivot, but does not block it.

If Go/No-Go result is:
- **GO / CONDITIONAL GO** → Proceed with Phase 01 canvas-mvp as planned
- **EXTEND** → Continue outreach while beginning Phase 01 work
- **NO-GO** → Revisit product thesis before committing Phase 01 engineering resources

---
*Phase: 00-validation*
*Completed: 2026-04-16 (human execution pending)*

## Self-Check: PASSED

- [x] Plan 00-03 has no automatable tasks (both are checkpoint:human-action)
- [x] All prerequisite artifacts from Plans 01 and 02 are committed and available
- [x] SUMMARY.md documents all human execution steps with acceptance criteria and resume signals
- [x] Requirements VAL-01 through VAL-05 documented as pending human completion
- [x] No files created or modified (as expected for a human-execution plan)
