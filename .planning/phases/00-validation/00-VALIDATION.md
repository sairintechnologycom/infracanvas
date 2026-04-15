---
phase: 0
slug: validation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-15
---

# Phase 0 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Manual verification (no automated tests — this is a go-to-market validation phase) |
| **Config file** | none |
| **Quick run command** | `echo "Phase 0 is manual validation"` |
| **Full suite command** | `echo "Phase 0 is manual validation"` |
| **Estimated runtime** | ~1 second |

---

## Sampling Rate

- **After every task commit:** Verify deliverable exists and meets acceptance criteria
- **After every plan wave:** Review all deliverables against success criteria
- **Before `/gsd-verify-work`:** All 5 success criteria checked
- **Max feedback latency:** Manual review within same session

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 0-01-01 | 01 | 1 | VAL-01 | — | N/A | manual | Visual inspection of demo video | N/A | ⬜ pending |
| 0-02-01 | 02 | 1 | VAL-02 | — | N/A | manual | Typeform live check | N/A | ⬜ pending |
| 0-03-01 | 03 | 1 | VAL-03 | — | N/A | manual | Stripe checkout test | N/A | ⬜ pending |
| 0-04-01 | 04 | 2 | VAL-04 | — | N/A | manual | Post engagement metrics | N/A | ⬜ pending |
| 0-05-01 | 05 | 3 | VAL-05 | — | N/A | manual | Conversation log review | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. Phase 0 is a go-to-market validation phase with no code deliverables — all verification is manual.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Demo video plays and shows full scan lifecycle | VAL-01 | Video content — cannot be automated | Open video file, verify 2-3 min runtime, text overlays visible, scan→diagram→findings→score flow |
| Typeform captures all required fields | VAL-02 | External SaaS — manual verification | Submit test response, verify role/team size/toolchain/willingness fields captured |
| Stripe founding member page accepts payment | VAL-03 | Payment flow — manual end-to-end | Complete test checkout at $49/mo, verify confirmation |
| Community posts generate engagement | VAL-04 | Social platform metrics — manual collection | Check post upvotes, comments, click-through to landing page |
| 20 conversations documented with pain points | VAL-05 | Qualitative research — manual by nature | Review spreadsheet for completeness: role, team size, tools, pain point, willingness, quote |

---

## Validation Sign-Off

- [ ] All tasks have manual verify instructions
- [ ] Sampling continuity: each deliverable verified before next wave
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency: same-session review
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
