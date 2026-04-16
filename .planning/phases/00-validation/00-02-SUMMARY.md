---
phase: 00-validation
plan: "02"
subsystem: validation
tags: [gtm, content, community, typeform, reddit, linkedin, go-no-go]
dependency_graph:
  requires: []
  provides:
    - validation/typeform/questions.md
    - validation/conversations/tracker.csv
    - validation/conversations/scoring-guide.md
    - validation/posts/reddit-r-devops.md
    - validation/posts/reddit-r-terraform.md
    - validation/posts/discord-terraform.md
    - validation/posts/linkedin.md
    - validation/posts/warmup-guide.md
    - validation/demo/video-script.md
    - validation/go-no-go/decision-framework.md
  affects: []
tech_stack:
  added: []
  patterns:
    - Pain-point-first community post framing (D-04)
    - Soft funnel via landing page — all posts link to infracanvas.dev only (D-06)
    - Reddit warm-up strategy — 30+ day account age, 50+ karma before demo post (D-07)
    - D-14 strong signal scoring — Typeform completion + named tool replacement + WTP
key_files:
  created:
    - validation/typeform/questions.md
    - validation/conversations/tracker.csv
    - validation/conversations/scoring-guide.md
    - validation/posts/reddit-r-devops.md
    - validation/posts/reddit-r-terraform.md
    - validation/posts/discord-terraform.md
    - validation/posts/linkedin.md
    - validation/posts/warmup-guide.md
    - validation/demo/video-script.md
    - validation/go-no-go/decision-framework.md
  modified: []
decisions:
  - "All post CTAs link to infracanvas.dev only — no direct Typeform or Stripe links (D-06)"
  - "Strong signal requires ALL three D-14 criteria: Typeform complete + named tool + WTP"
  - "Go/No-Go thresholds: Path A = 10 credit cards OR Path B = 50 strong signals (VAL-05)"
  - "Warm-up minimum: 30-day account age AND 50+ karma before demo post (D-07)"
  - "Demo video format: Silent with text callouts via OBS Studio + DaVinci Resolve (D-03)"
  - "LinkedIn uses Link-in-comments pattern to avoid algorithm link penalties (D-05)"
metrics:
  duration: "5m"
  completed: "2026-04-16T02:21:30Z"
  tasks_completed: 2
  tasks_total: 2
  files_created: 10
  files_modified: 0
---

# Phase 0 Plan 02: Validation Content Artifacts Summary

**One-liner:** 10-file validation artifact suite — Typeform question spec, D-14 strong signal tracker, pain-point-first community post drafts for r/devops/r/Terraform/Discord/LinkedIn, Reddit warm-up guide, 7-scene silent demo video script, and Go/No-Go decision framework with credit card and strong signal thresholds.

---

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Typeform question spec and conversation tracker | 66a5505 | validation/typeform/questions.md, validation/conversations/tracker.csv, validation/conversations/scoring-guide.md |
| 2 | Community posts, warm-up guide, video script, Go/No-Go framework | 1b97b76 | validation/posts/*.md (5 files), validation/demo/video-script.md, validation/go-no-go/decision-framework.md |

---

## What Was Built

### Task 1 — Typeform Spec, Tracker, Scoring Guide

**`validation/typeform/questions.md`:** Complete Typeform question specification for manual creation in the Typeform UI. 7 questions in order — role, team size, current tools (D-14 capture point), pain point, willingness to pay, price preference (conditional on Q5), follow-up consent with conditional email field. Includes Typeform Basic ($25/mo) upgrade warning per RESEARCH.md pitfall #2. Post-launch checklist included.

**`validation/conversations/tracker.csv`:** Blank CSV with all 12 D-13 columns: `date, name, role, team_size, current_tools, top_pain_point, willingness_to_pay, specific_tool_to_replace, direct_quote, call_type, strong_signal, follow_up_status`. One example row demonstrating correct format.

**`validation/conversations/scoring-guide.md`:** Full D-14 scoring methodology. Strong signal = ALL three conditions: Typeform completed + named specific tool + expressed WTP. Scoring matrix table. Explicit warning against counting raw completions as strong signals. Column definitions for all 12 tracker fields. Privacy note.

### Task 2 — Posts, Warm-Up, Video Script, Go/No-Go

**`validation/posts/reddit-r-devops.md`:** r/devops post draft. Title: "I was spending 20 minutes per incident correlating 5 different tools..." Pain-point story lead, product as punchline, links to infracanvas.dev only. Includes posting checklist and warm-up gate.

**`validation/posts/reddit-r-terraform.md`:** r/Terraform post draft adapted for Terraform-specific pain (module complexity, dependency tracing). Explicit 1–2 week stagger delay after r/devops per D-05. Incorporates feedback refinement step.

**`validation/posts/discord-terraform.md`:** Shorter, casual Discord format. Includes research note about server and channel identity (unconfirmed in planning — verify before posting). Pre-post checklist.

**`validation/posts/linkedin.md`:** LinkedIn-optimised format with short paragraphs, line breaks. "Link in comments" pattern to avoid algorithm penalty. Video attachment instruction for native autoplay. First comment ready with infracanvas.dev link.

**`validation/posts/warmup-guide.md`:** Minimum 2-week (ideally 4-week) warm-up timeline. 30+ day account age AND 50+ combined karma required before demo post. 5 example comment patterns (genuine, not templated per RESEARCH.md). Hard rule: ZERO mention of InfraCanvas during warm-up.

**`validation/demo/video-script.md`:** 7-scene script for 2–3 minute silent demo video. Scene 1: "5 tabs, 0 clarity" problem hook. Scene 2-3: Terminal scan. Scene 4: Interactive diagram. Scene 5: Finding detail panel. Scene 6: Score card (design overlay per D-02). Scene 7: End screen. Recording tool: OBS Studio + DaVinci Resolve. Text callout style guide included. References `viewer/src/sample-data.ts` for curated dataset.

**`validation/go-no-go/decision-framework.md`:** Phase 0 Go/No-Go decision framework. Two paths to GO: Path A (10+ credit cards from Stripe) or Path B (50+ strong signals in tracker). Full decision matrix: GO / CONDITIONAL GO / EXTEND / NO-GO with specific thresholds. CONDITIONAL GO investigation guide (pricing/trust gap analysis). Decision record template for logging the final decision.

---

## Key Decisions Made

1. **All post CTAs link to infracanvas.dev only** — Enforces D-06 soft funnel via landing page. No direct Typeform or Stripe links in any post draft.

2. **Strong signal scoring is strict** — D-14 criteria documented with explicit warnings against counting raw completions. Scoring guide is self-contained and repeats the definition for operators who may not read the full CONTEXT.md.

3. **Go/No-Go framework has 5-level matrix** — Not just GO/NO-GO. Added CONDITIONAL GO (50 signals, <5 cards) and EXTEND (20–49 signals) for nuanced operator guidance.

4. **Warm-up guide includes verification checklist** — Operators fill in actual numbers (account age, karma counts) before posting the demo. Prevents premature posting by making the check explicit.

5. **Video script references sample-data.ts** — Grounds the demo in the existing codebase. Prevents operator from creating entirely synthetic demo data that won't match real CLI output.

---

## Deviations from Plan

None — plan executed exactly as written. All 10 artifacts created with full acceptance criteria met.

---

## Known Stubs

None. All content is complete and self-contained. The video script references `viewer/src/sample-data.ts` which is a real existing file — the operator enhances it for curated demo content, which is an intended human task (within Claude's discretion per CONTEXT.md).

---

## Threat Flags

None. All artifacts are static markdown and CSV files. No code runs, no services contacted, no network endpoints introduced.

---

## Self-Check: PASSED
