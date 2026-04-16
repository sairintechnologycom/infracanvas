# Phase 0 Go/No-Go Decision Framework

**Evaluate this framework:** 4–6 weeks after the first community post goes live (not after warm-up, not after account creation).

**Data sources to gather before decision:**
- [ ] Stripe dashboard — Payments → filter by product "InfraCanvas Founding Member" → count paid subscriptions
- [ ] Typeform response count — raw total (not strong signals)
- [ ] Conversation tracker (`validation/conversations/tracker.csv`) — count rows where `strong_signal` = Y
- [ ] Reddit post engagement — upvotes, comments, saves on r/devops and r/Terraform posts
- [ ] LinkedIn post engagement — impressions, reactions, comments

---

## Two Paths to GO

### Path A: 10 or more credit cards captured

Count: Stripe dashboard → Payments → filter by product "InfraCanvas Founding Member" → count completed payments

- **Threshold:** 10+ paid subscriptions at $49/mo
- **What this means:** Strongest possible validation. Real money at founder-level pricing. Build Phase 1.

### Path B: 50 or more strong signals in conversation tracker

Count: Open `validation/conversations/tracker.csv` → count rows where `strong_signal` = `Y`

- **Threshold:** 50+ strong signal rows
- **Strong signal definition (D-14):** Typeform completed AND named a specific tool they would replace AND expressed willingness to pay ("Yes definitely" or "Probably" on Q5)
- **What this means:** Strong demand signal with intention to pay. Build Phase 1.

> **Warning:** Do NOT count raw Typeform completions as strong signals. See `validation/conversations/scoring-guide.md` for the exact scoring methodology. 50 Typeform completions where nobody named a tool to replace is NOT 50 strong signals.

---

## Decision Matrix

| Credit Cards | Strong Signals | Decision | Action |
|-------------|---------------|----------|--------|
| 10+ | Any | **GO** | Strongest validation. Proceed to Phase 1 immediately. |
| 5–9 | 50+ | **GO** | Strong validation with payment traction. Proceed to Phase 1. |
| 0–4 | 50+ | **CONDITIONAL GO** | Demand exists but payment friction unresolved. Investigate pricing and positioning before Phase 1. Run 5–10 direct conversations to understand the barrier. |
| Any | 20–49 | **EXTEND** | Continue outreach for 2 more weeks. Adjust pitch based on what's not resonating. Post to remaining platforms in the stagger sequence. |
| 0 | <20 (after 6 weeks of active outreach) | **NO-GO** | Insufficient signal. Pivot or shelve. Do not proceed to Phase 1. |

---

## CONDITIONAL GO — Investigation Before Proceeding

If you hit 50+ strong signals but fewer than 5 credit cards, do not assume the product is validated. The gap between "willing to pay" and "actually paying" may indicate:

1. **Pricing too high** — $49/mo may be above the individual budget. Ask directly in follow-up conversations.
2. **Wrong buyer** — Individual contributors may say yes but the budget is controlled by their manager. Adjust the message.
3. **Trust gap** — New tool, no social proof, no established brand. May need a free trial to convert.
4. **Timing** — Budget already allocated for this quarter. May convert later.

Run 5–10 direct discovery calls with strong signal respondents specifically asking: "What would need to be true for you to pay for this today?" Incorporate findings before proceeding to Phase 1.

---

## EXTEND — Pitch Adjustment Guide

If you hit 20–49 strong signals after the initial posting round, extend for 2 more weeks:

1. **Review Reddit comments** — What objections came up? What features were requested? What did people say they already use?
2. **Refine the pitch** — Does the title/framing need to change? Is the pain-point story landing? Is the demo video convincing?
3. **Post remaining platforms** — If LinkedIn or Discord haven't been posted yet, post them now.
4. **Direct outreach** — DM users who engaged with the post (upvoted, commented positively) and invite them to the Typeform.

If still below 50 strong signals after the extended period, escalate to a NO-GO review.

---

## NO-GO — Decision Protocol

A NO-GO after 6 weeks of active outreach (not including warm-up) means one or more of the following is true:

- The pain point is not painful enough to motivate action
- The target audience (DevOps engineers, Platform Engineers) is not the right buyer
- The product-market fit hypothesis is wrong and needs reframing
- The validation channel (Reddit) doesn't reach the buyer

Before shelving, document:
- Total outreach reach (combined post views/impressions across all platforms)
- Total Typeform responses (raw)
- Total strong signals
- Top objections from comments and conversations
- Hypothesis being invalidated

This debrief becomes the input for a pivot strategy or a revised Phase 0.

---

## Decision Record Template

Fill this in when making the Go/No-Go decision:

```
Date of decision: ___________
Weeks since first post: ___
Credit cards (Stripe): ___
Strong signals (tracker): ___
Raw Typeform responses: ___
r/devops post: ___ upvotes, ___ comments
r/Terraform post: ___ upvotes, ___ comments
LinkedIn post: ___ impressions, ___ reactions
Discord: ___ reactions, ___ replies

Decision: GO / CONDITIONAL GO / EXTEND / NO-GO

Rationale:
[1-3 sentences on why this decision was made]

Next steps:
[Specific actions: start Phase 1, run 5 more conversations, pivot hypothesis, etc.]
```
