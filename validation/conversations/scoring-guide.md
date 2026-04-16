# Customer Conversation Scoring Guide

This guide defines what counts as a "strong signal" for the Phase 0 Go/No-Go decision. Apply it to every row in `tracker.csv` before marking the `strong_signal` column.

---

## Strong Signal Definition (D-14)

A response counts as a **strong signal** ONLY when ALL three conditions are met:

1. **Typeform was completed** — The respondent reached the end screen. Partial submissions (abandoned mid-form) do not count.

2. **Respondent named a specific tool they would replace** — The `specific_tool_to_replace` column is not blank, and it names an actual tool. Acceptable examples: tfsec, Checkov, Infracost, draw.io, Lucidchart, Datadog, AWS Console, the Terraform CLI itself. Generic answers like "current spreadsheet" or "nothing" do not qualify.

3. **Respondent expressed willingness to pay** — The `willingness_to_pay` column is "Yes definitely" or "Probably". "Unlikely" and "No" do not qualify.

**Mark `strong_signal` = `Y` ONLY when all 3 criteria are met. Mark `N` otherwise.**

---

## Scoring Matrix

| Typeform completed | Named specific tool | Willing to pay | strong_signal |
|--------------------|---------------------|----------------|---------------|
| Yes | Yes | Yes definitely or Probably | **Y** |
| Yes | Yes | Unlikely or No | N |
| Yes | No / blank | Any | N |
| No (abandoned) | Any | Any | N |

---

## Critical Warning

> **Do NOT count raw Typeform completions as strong signals.** A completion where someone says they wouldn't pay or doesn't name a tool to replace is NOT a strong signal. The completion count is a vanity metric. The strong signal count is the only number that matters for Go/No-Go.

If you catch yourself thinking "well, 50 people filled it out, that's basically 50 strong signals" — stop. Go back to the matrix above. Re-score every row individually.

---

## Go/No-Go Reference (VAL-05)

The Phase 0 Go/No-Go requires one of the following thresholds:

- **Path A:** 10 credit cards captured in Stripe (strongest validation)
- **Path B:** 50 strong signals (`strong_signal` = `Y` rows) in this tracker

Count only `Y` rows in the `strong_signal` column of `tracker.csv`. Do not count raw Typeform responses, post engagement, or direct messages.

See `validation/go-no-go/decision-framework.md` for the full decision matrix.

---

## Column Definitions

| Column | Description | Valid Values |
|--------|-------------|--------------|
| `date` | Date of conversation or Typeform response | YYYY-MM-DD |
| `name` | First name or alias of respondent | Text (or "Anonymous") |
| `role` | Job role from Q1 | DevOps Engineer, Platform Engineer, SRE, Solutions Architect, Engineering Manager, Other |
| `team_size` | Infrastructure team size from Q2 | Solo, 2-5, 6-20, 20+ |
| `current_tools` | Tools named in Q3 | Comma-separated list |
| `top_pain_point` | Main pain from Q4 | Text |
| `willingness_to_pay` | Q5 answer | Yes definitely, Probably, Unlikely, No |
| `specific_tool_to_replace` | Specific tool extracted from Q3 answer | Tool name (or blank if none named) |
| `direct_quote` | Best direct quote from the conversation | Text in double quotes |
| `call_type` | How the conversation happened | async (Typeform only), video (live call) |
| `strong_signal` | All 3 D-14 criteria met? | Y or N |
| `follow_up_status` | Where is this person in the funnel | new, invited, scheduled, completed, declined |

---

## Privacy Note

This file may contain names and email addresses of respondents. Store it in the local git repository only. Do not upload to public file-sharing services. If sharing with collaborators, use a Google Sheet with restricted access.
