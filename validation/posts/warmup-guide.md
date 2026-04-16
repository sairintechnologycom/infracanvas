# Reddit Warm-Up Guide

**Purpose:** Build Reddit account credibility before the InfraCanvas demo post. A fresh or low-activity account posting a product demo to r/devops or r/Terraform will typically be auto-removed or downvoted without prior karma and community history. This warm-up period is not optional.

---

## Why This Matters

r/devops and r/Terraform use automoderators with minimum thresholds:

- **Account age:** 30+ days (posts from newer accounts are auto-removed silently)
- **Combined karma:** 50+ (karma earned from genuine community contributions)

A post that disappears within 5–10 minutes of submission without any notification is a strong sign of automod removal. You will not be notified. The post simply will not be seen.

**Do the warm-up. Then post the demo.**

---

## Timeline

| Phase | Duration | Activity |
|-------|----------|----------|
| Account creation | Day 0 | Create Reddit account if not already done |
| Early warm-up | Weeks 1–2 | 2–4 genuine comments per week in r/devops and r/Terraform |
| Active warm-up | Weeks 3–4 | Continue commenting; start identifying threads for the demo post |
| Demo post | Week 4+ | Only after account age 30+ days AND 50+ karma |

**Minimum:** 2 weeks. **Recommended:** 4 weeks. The account age requirement alone forces patience — there is no shortcut.

---

## Minimum Thresholds Before Demo Post

Do not post the demo until BOTH conditions are met:

- **Account age:** 30+ days
- **Combined karma:** 50+ karma from r/devops and r/Terraform combined

Verify both before posting. The Reddit account profile shows account age and karma.

---

## Frequency

- 2–4 genuine comments per week
- Spread across r/devops and r/Terraform
- Do not force it — only comment where you have something genuinely useful to add

---

## Target Thread Types

Look for threads with these themes:

- "What tools do you use for Terraform security scanning?"
- "How do you visualise your cloud infrastructure?"
- "How do you audit your AWS/Azure environment?"
- "Terraform module complexity — how do you manage it?"
- "What's your infra-as-code toolchain?"
- "How do you track infrastructure costs?"
- "What's your DevOps toolstack in [year]?"
- "What's your biggest pain with Terraform at scale?"

Use Reddit search: `site:reddit.com r/devops [keyword]` or browse the New/Hot tabs.

---

## ZERO Mention of InfraCanvas During Warm-Up

**Do not mention InfraCanvas, your project, or anything you are building during the warm-up period.** Zero. None. Not even "I'm working on something similar."

Any mention of your product during warm-up will:
1. Reveal the strategy, which backfires on Reddit communities
2. Create a comment history that looks like a lead-up to a spam post
3. Undermine the credibility you are building

Be a helpful community member. That is all.

---

## Example Comment Patterns

These are patterns, not templates. Adapt to the actual thread. The goal is genuine contribution — do NOT copy-paste these verbatim.

**Pattern 1: Sharing specific experience (tool comparison thread)**

> We've been using tfsec for a while and recently added Checkov alongside it. tfsec is faster but Checkov has broader rule coverage across provider types. The main friction is that neither of them integrates well with Infracost — you end up with two separate passes and have to mentally correlate findings across them. If anyone has a workflow that ties these together cleanly I'd be interested.

**Pattern 2: Acknowledging a legitimate complaint (complexity thread)**

> Yeah, the module reference problem gets really bad at scale. We had a codebase where a single change in a root module touched 40 resources across 6 provider accounts and it was genuinely difficult to communicate the blast radius to the team before applying. We ended up making a rough diagram by hand every time. Would love a better answer.

**Pattern 3: Answering a question with a specific recommendation (toolchain thread)**

> For Terraform security scanning at the team level: tfsec for fast feedback in the CI pipeline (it's fast enough to run on every PR), Checkov for deeper scanning on a weekly scheduled job where the longer runtime is acceptable. Infracost for cost estimates on PRs — the comment bot integration is useful for getting engineers to think about cost impact without a separate step.

**Pattern 4: Asking a genuine question in a thread you have interest in**

> Curious how you handle shared infrastructure costs across teams — like a VPC or a Transit Gateway that's used by multiple product teams. Do you allocate by traffic, by resource count, or some other method? We've been doing rough percentage splits but it feels arbitrary.

---

## Rules Summary

1. Be specific and helpful — generic "good point!" comments build no karma and add no value
2. Share genuine technical experience — what you've actually used, what worked, what didn't
3. ZERO mention of InfraCanvas or anything you are building
4. No promotional language of any kind during warm-up
5. Build karma through value, not volume — 3 great comments beat 10 mediocre ones
6. Read the thread before commenting — do not reply without reading the full context

---

## Verification Before Demo Post

Before submitting the demo post, run this check:

```
[ ] Reddit account age: ___ days (must be 30+)
[ ] r/devops karma: ___
[ ] r/Terraform karma: ___
[ ] Combined karma: ___ (must be 50+)
[ ] No product-related comments in history
[ ] Warm-up period: ___ weeks (should be 2+, ideally 4)
```

If any box is unchecked — wait. The post can always be submitted later. A removed post cannot be recovered.
