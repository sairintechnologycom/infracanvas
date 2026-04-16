# InfraCanvas — 2 Minute Infrastructure Survey

Typeform question specification. Use this document to manually create the form in the Typeform UI.

---

## Form Settings

- **Title:** InfraCanvas — 2 Minute Infrastructure Survey
- **Description (shown before Q1):** Help us build the right tool. 7 quick questions about your infrastructure workflow.
- **End screen message:** "Thanks! We read every response. If you said yes to a call, we'll be in touch within 48 hours."

---

## Pricing Note

> **Important:** Upgrade to **Typeform Basic ($25/mo)** before publishing this form. The free tier caps at 10 responses per month, which will block new respondents mid-campaign. Set up billing before any post goes live.

---

## Questions

### Q1 — Role

**Question text:** What's your role?

**Field type:** Multiple choice (single select)

**Options:**
- DevOps Engineer
- Platform Engineer
- SRE
- Solutions Architect
- Engineering Manager
- Other (please specify) — *enable open text follow-up field*

**Required:** Yes

---

### Q2 — Team Size

**Question text:** How large is your infrastructure team?

**Field type:** Multiple choice (single select)

**Options:**
- Solo (just me)
- 2–5
- 6–20
- 20+

**Required:** Yes

---

### Q3 — Current Tools

**Question text:** What tools do you currently use to understand your infrastructure?

**Field type:** Long text (open answer)

**Hint text:** e.g., AWS Console, Terraform, tfsec, Infracost, draw.io, Lucidchart, Datadog

**Required:** Yes

**Note for scoring:** This is the answer used to determine `specific_tool_to_replace` in the tracker. A response that names a specific tool (tfsec, Infracost, draw.io, Lucidchart, etc.) is a prerequisite for a strong signal per D-14.

---

### Q4 — Biggest Headache

**Question text:** What's your biggest headache with your current setup?

**Field type:** Long text (open answer)

**Required:** No (but encouraged — this captures pain-point language for positioning)

---

### Q5 — Willingness to Pay

**Question text:** If a tool gave you a single diagram of your entire infra with security findings, cost, and drift — would you pay for it?

**Field type:** Multiple choice (single select)

**Options:**
- Yes definitely
- Probably
- Unlikely
- No

**Required:** Yes

**Note:** Responses of "Yes definitely" or "Probably" are the willingness-to-pay signal used for D-14 strong signal scoring.

---

### Q6 — Pricing Preference

**Question text:** What would feel like a fair monthly price for your team?

**Field type:** Multiple choice (single select)

**Options:**
- Free only
- $10–25/mo
- $49–99/mo
- $100–200/mo
- $200+/mo

**Required:** No

**Conditional logic:** Only show this question if Q5 answer is "Yes definitely" OR "Probably". Hide for "Unlikely" and "No".

**Note:** This is the willingness to pay pricing calibration question. Responses help set price anchoring for the founding member offer ($49/mo).

---

### Q7 — Follow-Up

**Question text:** Can we follow up with you for a 15-minute call?

**Field type:** Multiple choice (single select)

**Options:**
- Yes, here's my email
- No thanks

**Conditional email field:** If respondent selects "Yes, here's my email", show an additional email input field immediately after. Label: "Your email address". Required when shown.

**Required:** Yes (the multiple choice selection itself; email field is required only when "Yes" is selected)

---

## Conditional Logic Summary

| Condition | Action |
|-----------|--------|
| Q5 = "Yes definitely" OR "Probably" | Show Q6 |
| Q5 = "Unlikely" OR "No" | Skip Q6 |
| Q7 = "Yes, here's my email" | Show email input field |
| Q7 = "No thanks" | Proceed to end screen |

---

## End Screen

**Text:** Thanks! We read every response. If you said yes to a call, we'll be in touch within 48 hours.

**Button:** (optional) Link to infracanvas.dev with label "Learn more about InfraCanvas"

---

## Post-Launch Checklist

- [ ] Typeform Basic ($25/mo) plan activated before form is published
- [ ] Form URL tested end-to-end on desktop and mobile
- [ ] Conditional logic verified: Q6 only appears after "Yes definitely" / "Probably" on Q5
- [ ] Email capture on Q7 "Yes" branch is working
- [ ] Test response appears in Typeform Results dashboard
- [ ] Form URL embedded on infracanvas.dev landing page (not linked directly from Reddit posts)
