# Phase 0: Validation - Context

**Gathered:** 2026-04-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Confirm real demand and willingness to pay for InfraCanvas before writing any product code. Deliverables: a fake demo video, community posts across Reddit/Discord/LinkedIn, a Stripe founding member page, 20 customer conversations, and a Go/No-Go decision based on 10 credit cards OR 50 strong signals.

</domain>

<decisions>
## Implementation Decisions

### Demo Format
- **D-01:** Fake demo is a 2-3 minute narrated video (text overlays, no voice) showing the full scan lifecycle: `infracanvas scan ./terraform` → terminal progress → browser opens → interactive diagram with VPC groups → click a finding → score card
- **D-02:** Video uses the real existing React/ReactFlow viewer loaded with curated sample data, plus design overlays for features not yet built (score card polish, finding detail panel). Authentic base + aspirational polish.
- **D-03:** Silent video with text callouts — optimised for mute autoplay on LinkedIn and Reddit scroll

### Outreach & Posting
- **D-04:** Posts framed as pain-point story first — lead with the problem ("5 tabs open trying to understand our infra"), product is the punchline. Not a direct product announcement.
- **D-05:** Stagger posts by platform: Reddit (r/devops) first → learn from feedback → refine → r/Terraform + Discord → LinkedIn. Each round improves the pitch.
- **D-06:** Soft funnel via landing page — all posts link to infracanvas.dev (not direct Typeform/Stripe links). Landing page has the video, value props, then CTA buttons to Typeform and Stripe.
- **D-07:** Account is fresh/low-activity — plan must include a credibility-building warm-up period (helpful comments, genuine participation in r/devops and r/Terraform) before the main demo post.

### Founding Member Page
- **D-08:** Offer is $49/mo locked forever + private Discord/Slack channel for roadmap input. Builds a community of early champions who feel invested in the product direction.
- **D-09:** Visible counter showing "X of 50 spots remaining" on the page — creates social proof and urgency. Soft-capped (can extend if needed).
- **D-10:** Landing page is a simple static site deployed on Vercel (infracanvas.dev) with Stripe Checkout embedded. Same site serves as the soft-funnel destination from community posts.

### Customer Conversations
- **D-11:** Primary sourcing from community respondents — people who engage with posts or fill out the Typeform. Warm leads, natural follow-up.
- **D-12:** Mix of async-first + calls for high-signal: everyone goes through Typeform, top respondents (willingness to pay, large team, specific pain) get invited to 15-min video calls.
- **D-13:** Pain points documented in a structured spreadsheet: one row per conversation with columns for role, team size, current tools, top pain point, willingness to pay, direct quote.
- **D-14:** "Strong signal" for Go/No-Go defined as: completed Typeform AND named a specific tool they'd replace (tfsec, Infracost, draw.io, etc.) AND expressed willingness to pay. This is what counts toward the 50-signal threshold.

### Claude's Discretion
- Video editing tool/workflow selection
- Typeform question design and sequencing
- Exact Reddit warm-up timeline and comment strategy
- Landing page copy and design details
- Spreadsheet template column structure
- Email follow-up cadence for high-signal respondents

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

No external specs — requirements fully captured in decisions above. Key reference files:

### Project Context
- `.planning/PROJECT.md` — Product vision, constraints, target personas (Priya → Alex → Sam), pricing tiers
- `.planning/REQUIREMENTS.md` §Validation — VAL-01 through VAL-05 acceptance criteria
- `.planning/ROADMAP.md` §Phase 0 — Success criteria (5 items) and dependency chain

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `viewer/` — Working React 18 + @xyflow/react + Zustand + Tailwind viewer that can be loaded with sample data for the demo video recording
- `cli/infracanvas/export/html.py` — Single-file HTML export that embeds graph data via `window.__INFRACANVAS_DATA__`
- `cli/infracanvas/main.py` — Working CLI with `scan`, `score`, `plan`, `export` commands that can be screen-recorded

### Established Patterns
- Viewer already renders VPC/subnet grouping, resource icons, dependency edges, and security finding badges — all needed for demo content
- Single-file HTML export means the demo can show a real standalone artifact

### Integration Points
- The landing page (new static site on Vercel) is a new deliverable — no existing integration point
- Typeform and Stripe are external services, not codebase integrations

</code_context>

<specifics>
## Specific Ideas

- Pain-point hook: "5 tabs open — AWS console, Terraform, tfsec, Infracost, draw.io" resonates with the core value prop
- Founding member Discord/Slack channel doubles as early customer feedback loop for Phase 1
- Score card mechanic ("letter grade for your infrastructure") is designed for viral sharing — demo should prominently feature it
- Fresh Reddit account means 1-2 weeks of genuine community participation before the demo post

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 00-validation*
*Context gathered: 2026-04-15*
