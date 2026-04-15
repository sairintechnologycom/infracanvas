# Phase 0: Validation - Research

**Researched:** 2026-04-15
**Domain:** Go-to-market validation / pre-launch demand testing (devtools B2B SaaS)
**Confidence:** HIGH (core tooling) / MEDIUM (community rules specifics)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Demo Format**
- D-01: Fake demo is a 2-3 minute narrated video (text overlays, no voice) showing the full scan lifecycle: `infracanvas scan ./terraform` → terminal progress → browser opens → interactive diagram with VPC groups → click a finding → score card
- D-02: Video uses the real existing React/ReactFlow viewer loaded with curated sample data, plus design overlays for features not yet built (score card polish, finding detail panel). Authentic base + aspirational polish.
- D-03: Silent video with text callouts — optimised for mute autoplay on LinkedIn and Reddit scroll

**Outreach & Posting**
- D-04: Posts framed as pain-point story first — lead with the problem ("5 tabs open trying to understand our infra"), product is the punchline. Not a direct product announcement.
- D-05: Stagger posts by platform: Reddit (r/devops) first → learn from feedback → refine → r/Terraform + Discord → LinkedIn. Each round improves the pitch.
- D-06: Soft funnel via landing page — all posts link to infracanvas.dev (not direct Typeform/Stripe links). Landing page has the video, value props, then CTA buttons to Typeform and Stripe.
- D-07: Account is fresh/low-activity — plan must include a credibility-building warm-up period (helpful comments, genuine participation in r/devops and r/Terraform) before the main demo post.

**Founding Member Page**
- D-08: Offer is $49/mo locked forever + private Discord/Slack channel for roadmap input.
- D-09: Visible counter showing "X of 50 spots remaining" on the page — creates social proof and urgency. Soft-capped (can extend if needed).
- D-10: Landing page is a simple static site deployed on Vercel (infracanvas.dev) with Stripe Checkout embedded.

**Customer Conversations**
- D-11: Primary sourcing from community respondents — people who engage with posts or fill out the Typeform.
- D-12: Mix of async-first + calls for high-signal: everyone goes through Typeform, top respondents (willingness to pay, large team, specific pain) get invited to 15-min video calls.
- D-13: Pain points documented in a structured spreadsheet: one row per conversation with columns for role, team size, current tools, top pain point, willingness to pay, direct quote.
- D-14: "Strong signal" for Go/No-Go defined as: completed Typeform AND named a specific tool they'd replace (tfsec, Infracost, draw.io, etc.) AND expressed willingness to pay.

### Claude's Discretion
- Video editing tool/workflow selection
- Typeform question design and sequencing
- Exact Reddit warm-up timeline and comment strategy
- Landing page copy and design details
- Spreadsheet template column structure
- Email follow-up cadence for high-signal respondents

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| VAL-01 | Fake demo posted across r/devops, r/Terraform, Terraform Discord, LinkedIn | Demo recording toolchain, community posting rules, warm-up strategy |
| VAL-02 | Typeform collects role, team size, current toolchain, willingness to pay | Typeform question sequencing, conversational survey best practices |
| VAL-03 | Stripe founding member page live ($49/mo locked forever) | Stripe Payment Links no-code setup, subscription product creation |
| VAL-04 | 20 customer conversations completed with documented pain points | Conversation tracking spreadsheet structure, discovery interview patterns |
| VAL-05 | Go/No-Go decision based on 10 credit cards OR 50 strong signals | Signal definition from D-14, decision framework |
</phase_requirements>

---

## Summary

Phase 0 is a go-to-market validation phase — no product code is written. All deliverables are external-facing: a demo video, community posts, a landing page, a Typeform survey, a Stripe founding member page, and 20 documented customer conversations. The technical complexity is low (static Vercel site, no-code Stripe, Typeform); the strategic complexity is high (community credibility, funnel design, signal quality).

The critical risk is Reddit account credibility. A fresh account posting a product demo to r/devops or r/Terraform will typically be removed or downvoted heavily without prior karma and community history. The warm-up period (D-07) is not optional — it is the gating dependency for VAL-01. Two to four weeks of genuine participation is the minimum viable credibility-building window.

The second risk is signal quality vs. signal volume. The Go/No-Go threshold (VAL-05) explicitly requires quality signals (D-14: Typeform + named tool replacement + willingness to pay), not just Typeform completions. The plan must distinguish counting raw responses from counting qualified strong signals.

**Primary recommendation:** Sequence all tasks around the Reddit warm-up constraint. Everything else (Typeform, Stripe, landing page, demo recording) can be built in parallel and completed within 2-3 weeks. The warm-up period determines total phase duration.

---

## Standard Stack

### Core
| Tool | Version/Plan | Purpose | Why Use |
|------|-------------|---------|---------|
| Vercel | Free/Pro | Static landing page hosting at infracanvas.dev | D-10 locked; zero-config deploy, custom domain, free SSL |
| Next.js | 14 (existing codebase) | Landing page framework | Project standard; App Router, static export |
| Tailwind CSS | 4.1.4 (existing) | Landing page styling | Project standard already installed in viewer/ |
| Stripe Payment Links | No-code dashboard | $49/mo founding member subscription | No backend needed; Payment Link = hosted Stripe Checkout page |
| Typeform | Free tier | Customer discovery survey | Conversational format maximises completion rate for B2B |
| Google Sheets | Free | Customer conversation tracker | Zero setup, shareable, sortable — sufficient for 20 conversations |

### Video Recording (Claude's Discretion — Recommended)
| Tool | Cost | Purpose | Tradeoff |
|------|------|---------|---------|
| Screen Studio | $108/yr | macOS screen recording with auto-zoom and polish | No text callout/overlay built-in; need second tool for callouts |
| ScreenFlow | ~$149 one-time | Full video editing + text callouts on macOS | Heavier, steeper learning curve |
| OBS Studio + DaVinci Resolve | Free | Record + edit + text overlays | Best for text callouts; steeper setup |
| Kap (macOS) + CapCut/DaVinci | Free + Free | Lightweight record then edit | Kap is minimal; editing in separate free tool adds callouts |

**Recommended:** OBS Studio (recording) + DaVinci Resolve (editing + text callouts). Both free, both support silent video with text overlay which D-03 requires. Screen Studio's auto-zoom is attractive but its lack of text callout support makes it a poor fit for D-01/D-03.

Alternative: ScreenFlow ($149 one-time) is the single-tool solution for macOS if budget allows — record, zoom, and add text callouts in one app.

### Alternatives Considered
| Standard Choice | Alternative | When Alternative Makes Sense |
|-----------------|-------------|------------------------------|
| Stripe Payment Links (no-code) | Stripe Checkout API | When you need custom UI, quantity counter, or webhook logic |
| Typeform | Google Forms | If Typeform free tier limits become a blocker (10 questions / 10 responses/mo on free) |
| Vercel (Next.js) | Plain HTML/CSS | Marginally faster to build but misses the existing codebase ecosystem |

**Installation (landing page):**
```bash
# New Next.js app for landing page (separate from viewer/)
npx create-next-app@14 landing --typescript --tailwind --app
cd landing && vercel deploy
```

---

## Architecture Patterns

### Recommended Project Structure
```
landing/                    # New: infracanvas.dev static site
├── app/
│   ├── page.tsx            # Main landing page (hero, video embed, CTA)
│   ├── layout.tsx          # Root layout, meta tags
│   └── globals.css         # Tailwind base
├── components/
│   ├── Hero.tsx            # Pain-point hook + headline
│   ├── DemoVideo.tsx       # Video embed (Loom/YouTube/self-hosted)
│   ├── ValueProps.tsx      # Three-panel feature summary
│   ├── FoundingMember.tsx  # Stripe CTA + spot counter
│   └── CTAButtons.tsx      # Typeform + Stripe Checkout links
├── public/
│   └── demo.mp4            # Or link to hosted video
└── vercel.json             # Static export config if needed

validation/                 # New: non-code validation artifacts
├── conversations/
│   └── tracker.csv         # Or Google Sheets link
├── typeform/
│   └── questions.md        # Question spec (for Claude's implementation)
└── posts/
    ├── reddit-r-devops.md  # Post drafts per platform
    ├── reddit-r-terraform.md
    ├── discord.md
    └── linkedin.md
```

### Pattern 1: Stripe Payment Links (No Backend Required)
**What:** Create a Stripe Product + Price in the Dashboard, generate a Payment Link URL, embed as a button on the landing page.
**When to use:** Pre-launch with no backend infrastructure — D-10 specifies no backend for the landing page.
**How it works:**
1. Stripe Dashboard → Products → Create Product ("InfraCanvas Founding Member")
2. Set price: $49/month recurring, currency USD
3. Products → Payment Links → Create Link from this price
4. Optional: Add quantity limit in Payment Links settings (maps to D-09 spot counter — but Stripe's built-in limit is hard stop; for a soft-cap with visible counter, use a manual counter component)
5. Embed the `pay.stripe.com/...` URL as a button on the landing page

**Spot counter for D-09:** Stripe does not provide a live "X remaining" counter widget. Options:
- Hardcode counter text, manually update as payments come in (sufficient for 50-spot cap at low velocity)
- Use a Vercel Edge Config or simple KV store (Upstash Redis — already in project stack) to hold the counter, fetched client-side

**Pattern 2: Typeform Conversational Survey**
**What:** Multi-step form with one question per screen, conditional logic to skip irrelevant branches.
**Recommended question sequence (Claude's Discretion):**
1. "What's your role?" (DevOps / Platform Eng / SRE / Architect / Engineering Manager / Other)
2. "How large is your infrastructure team?" (Solo / 2-5 / 6-20 / 20+)
3. "What tools do you currently use to understand your infra?" (open text — captures tool names for D-14)
4. "What's your biggest headache with your current setup?" (open text — captures pain point language)
5. "If a tool gave you a single diagram of your entire infra with security findings, cost, and drift — would you pay for it?" (Yes, definitely / Probably / Unlikely / No)
6. "If yes — what would feel like a fair monthly price for a team?" ($0-free / $10-25 / $49-99 / $100-200 / $200+)
7. "Can we follow up with you for a 15-minute call?" (Yes, here's my email / No thanks)

**Typeform free tier limits:** 10 questions max per form, 10 responses per month. The above 7-question form fits within the question limit. However, 10 responses/month is too low for meaningful validation — upgrade to Basic ($25/mo) which provides unlimited responses.

**Pattern 3: Reddit Warm-Up Strategy (D-07)**
**What:** Genuine community participation to build account credibility before the demo post.
**Timeline:** Minimum 2 weeks; 4 weeks is safer.
**Tactics:**
- Answer 2-4 technical questions per week in r/devops and r/Terraform with genuinely helpful, specific responses
- Share useful non-self-promotional content (interesting blog posts, tools from others)
- Avoid any mention of InfraCanvas during warm-up
- Target threads about: Terraform complexity, "how do you audit your infra", "what tools do you use for security scanning", "visualising cloud infrastructure"

**Reddit post structure for demo post (D-04):**
```
Title: "I was spending 20 minutes per incident correlating 5 different 
        tools to understand our infra. So I built something."

Body:
[Pain-point story: 2-3 paragraphs of relatable problem]
[What I built: 1 paragraph, product is the punchline]
[Demo video: embedded or linked]
[CTA: "If this resonates, I'd love 15 minutes of your time" → Typeform link]
[Disclosure: "I'm the maker"]
```

### Anti-Patterns to Avoid
- **Direct product announcement post:** Leads with "I built X" instead of the problem. Gets downvoted on r/devops.
- **Posting to multiple subreddits on the same day:** Looks like spam, gets cross-posted removal flags. Stagger by 1-2 weeks (D-05).
- **Linking directly to Typeform or Stripe from posts:** Appears commercial/spammy. All post CTAs should link to infracanvas.dev (D-06).
- **Posting with a new account (<30 days old):** High risk of automod removal on r/devops and r/Terraform. The warm-up period builds age AND karma.
- **Counting all Typeform completions as "strong signals":** D-14 defines a strong signal as Typeform + named tool replacement + expressed willingness to pay. Raw completion count is a vanity metric.
- **Stripe Payment Link with quantity hard-limit set to 50:** When 50 payments are collected, the link closes entirely — no fallback for soft-cap extension. Leave quantity unlimited and manage the counter manually.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Subscription billing | Custom payment form + backend | Stripe Payment Links | PCI compliance, Smart Retries, hosted checkout — no backend needed |
| Survey collection | Custom form UI + API | Typeform | Conditional logic, conversational UX, analytics built-in |
| Landing page analytics | Custom event tracking | Vercel Analytics (built-in) or Plausible | Zero setup, no GDPR risk at this stage |
| Email list management | Custom signup + DB | Typeform captures emails natively | Sufficient for 20-conversation scale |
| Video hosting | Self-hosting demo.mp4 | Loom free tier or YouTube unlisted | No bandwidth cost, better autoplay compatibility, embeds cleanly |

**Key insight:** This is a validation phase, not a build phase. Every hour spent building custom infrastructure for validation tooling is waste. Use hosted services for everything — the goal is to test demand, not to build the right backend for demand collection.

---

## Common Pitfalls

### Pitfall 1: Reddit Account Age / Karma Automod Removal
**What goes wrong:** Demo post is auto-removed within minutes because the account is too new or has insufficient karma. The post never gets seen.
**Why it happens:** r/devops and r/Terraform use automoderators with minimum account age (typically 30+ days) and karma thresholds (50-100+) to filter spam.
**How to avoid:** Start the warm-up period immediately. Do not post the demo until the account is at least 30 days old AND has 50+ combined karma from genuine contributions.
**Warning signs:** Post disappears within 5-10 minutes of submission without any notification.

### Pitfall 2: Typeform Free Tier Response Cap
**What goes wrong:** Typeform's free plan caps at 10 responses per month. After 10 completions, new respondents see an error or the form closes.
**Why it happens:** Typeform free tier is designed for testing, not production use.
**How to avoid:** Upgrade to Typeform Basic ($25/mo) before publishing the form link. Set up billing on Typeform before any post goes live.
**Warning signs:** Response count stops at 10 despite continued post engagement.

### Pitfall 3: Conflating Response Count with Strong Signals
**What goes wrong:** 50 Typeform completions are counted as "50 strong signals" for Go/No-Go. The product gets built. Most respondents had shallow interest — only 10 would have paid.
**Why it happens:** Optimism bias. It feels like progress to see form completions accumulate.
**How to avoid:** Implement D-14 rigorously: a strong signal = Typeform completed + named a specific tool to replace + expressed willingness to pay. Score each row in the tracker spreadsheet against these three criteria explicitly.
**Warning signs:** Response column says 50 but "named tool replacement" column is mostly blank.

### Pitfall 4: Demo Video Text Callouts vs. Tool Capability Gap
**What goes wrong:** Screen Studio is purchased for the demo video but has no text callout feature. Text overlays — required by D-01 and D-03 — must be added in a second tool, creating an unexpected editing step.
**Why it happens:** Screen Studio's auto-zoom feature is appealing and well-reviewed, but it's primarily a recording/presentation tool, not a full video editor.
**How to avoid:** Either use OBS + DaVinci Resolve (free, full text callout support) or ScreenFlow ($149, all-in-one for macOS). Do not assume Screen Studio handles all requirements.

### Pitfall 5: Stripe Payment Links Spot Counter Mismatch
**What goes wrong:** The "X of 50 spots remaining" counter on the landing page (D-09) shows 50 remaining even after 5 people have paid, because the counter is hardcoded and not updated.
**Why it happens:** There is no automatic hook between Stripe payment events and a landing page counter without backend code.
**How to avoid:** Either (a) manually update the counter text in the landing page code and redeploy whenever a payment is received (acceptable at low velocity), or (b) use Upstash Redis (already in project stack) as a simple KV store for the counter value, fetched via a Next.js API route or Edge Config.

### Pitfall 6: Landing Page on Same Vercel Project as Viewer
**What goes wrong:** The marketing landing page and the existing viewer/ React app become tangled in the same Vercel project, causing build conflicts.
**Why it happens:** The existing viewer/ uses Vite with vite-plugin-singlefile — incompatible with Next.js App Router in the same project.
**How to avoid:** Create the landing page as a separate Next.js project in a new directory (e.g., `landing/`) with its own Vercel project. Do not nest it inside viewer/.

---

## Code Examples

### Stripe Payment Link — No Backend Required
```
1. Stripe Dashboard → Products → + Add Product
2. Name: "InfraCanvas Founding Member"
3. Description: "Locked $49/mo forever + private roadmap Discord"
4. Pricing: Recurring, $49 USD / month
5. Save product
6. Payment Links → + New → Select the $49/mo price
7. (Optional) Customise: add logo, custom success page URL
8. Copy the pay.stripe.com/... URL
9. Embed as <a href="https://pay.stripe.com/..."> button in landing page
```

### Landing Page CTA Component (pattern)
```typescript
// Source: Locked decisions D-06, D-08, D-09
// components/FoundingMember.tsx
export function FoundingMember({ spotsRemaining }: { spotsRemaining: number }) {
  return (
    <section className="bg-slate-900 rounded-2xl p-8 text-center">
      <p className="text-amber-400 font-mono text-sm mb-2">
        {spotsRemaining} of 50 founding member spots remaining
      </p>
      <h2 className="text-2xl font-bold text-white mb-4">
        Lock in $49/mo forever
      </h2>
      <a
        href={process.env.NEXT_PUBLIC_STRIPE_PAYMENT_LINK}
        className="inline-block bg-amber-400 text-slate-900 font-bold px-8 py-3 rounded-lg"
      >
        Claim Your Spot
      </a>
      <p className="text-slate-400 text-sm mt-3">
        + Private Discord for roadmap input
      </p>
    </section>
  )
}
```

### Customer Conversation Tracker Spreadsheet Schema
```
Columns (one row per conversation):
| date | name | role | team_size | current_tools | top_pain_point |
| willingness_to_pay | specific_tool_to_replace | direct_quote |
| call_type (async/video) | strong_signal (Y/N) | follow_up_status |

Strong signal = Y only when:
  - willingness_to_pay is not "No" AND
  - specific_tool_to_replace is not blank AND
  - Typeform was completed
```

### Reddit Warm-Up Comment Template (genuine, not templated)
```
Target thread type: "What tools do you use for Terraform security scanning?"

Helpful response pattern (NOT templated — adapt to each thread):
- Acknowledge the question genuinely
- Share specific experience with tfsec / Checkov / Infracost tradeoffs
- Mention concrete limitation you encountered (e.g., "Infracost doesn't
  show you *why* a resource is expensive relative to its config")
- No mention of anything you're building
```

---

## State of the Art

| Old Approach | Current Approach | Impact for This Phase |
|--------------|------------------|-----------------------|
| Custom payment forms + backend | Stripe Payment Links (no-code) | Founding member page requires zero backend code |
| Waitlist email only | Founding member paid pre-order | Credit card > email as validation signal (much stronger) |
| Launch-first, learn later | Problem-first community posting (D-04) | r/devops culture rewards "I solved my own problem" framing |
| Single launch day | Staggered platform posts (D-05) | Each round refines pitch; Reddit → Discord → LinkedIn |
| Typeform free | Typeform Basic ($25/mo) | Free tier 10-response limit would cap VAL-02 mid-campaign |

**Deprecated/outdated:**
- Stripe `create_usage_record()` API: removed 2025-03-31. Not relevant to this phase (we're using Payment Links, not metered billing) but relevant as a future pitfall when building the SaaS backend in Phase 4.
- ProductHunt launch as validation: community has shifted; engagement is lower than 2020-2022 peak. Not in scope for Phase 0 (deferred by context).

---

## Open Questions

1. **infracanvas.dev domain registration**
   - What we know: Decision D-10 specifies infracanvas.dev as the domain. Domain registration is not mentioned in any planning document.
   - What's unclear: Is infracanvas.dev already registered? If not, the planner needs a task for domain acquisition before Vercel deployment.
   - Recommendation: Add a verification step in Wave 0 to check domain availability/ownership.

2. **Typeform Business Email Collection**
   - What we know: D-12 requires top respondents to get 15-min video call invites. The Typeform question sequence above includes an optional email field at the end.
   - What's unclear: Whether an optional email field on the last question captures enough high-signal respondents, vs. making email a required field (which reduces completion rate).
   - Recommendation: Make email optional but prominent. Accept lower capture rate in exchange for better overall completion rate.

3. **Spot Counter Real-Time Synchronisation**
   - What we know: D-09 requires a "X of 50 spots remaining" counter. Stripe Payment Links have no native counter webhook.
   - What's unclear: Whether manual redeploy (acceptable) or Upstash KV (slightly more complex) is the right call for this phase.
   - Recommendation: Start with hardcoded counter + manual redeploy on each payment. If payment velocity is high (10+ in first 48 hours), add Upstash KV. This avoids over-engineering for a soft-cap that may only be hit once.

4. **Terraform Discord Server Identity**
   - What we know: VAL-01 requires posting to "Terraform Discord". There are multiple Terraform-adjacent Discord servers (HashiCorp official, DevOps community servers).
   - What's unclear: Which specific Terraform Discord server is the intended target, and whether it has a #show-and-tell or equivalent channel that permits product posts.
   - Recommendation: Planner should include a research sub-task to join and identify the correct server and relevant channel before drafting the Discord post.

---

## Validation Architecture

> nyquist_validation is enabled per .planning/config.json

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Manual verification + checklist (no automated tests appropriate for GTM phase) |
| Config file | None — validation is evidence-based, not code-based |
| Quick run command | Review tracker spreadsheet + Stripe dashboard |
| Full suite command | Full Go/No-Go review against VAL-05 criteria |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VAL-01 | Demo posted to all 4 platforms with measurable engagement | Manual | Check post URLs + engagement counts | N/A |
| VAL-02 | Typeform live and collecting role/team/toolchain/WTP | Manual | Load Typeform URL, verify fields present | N/A |
| VAL-03 | Stripe founding member page live at $49/mo | Manual | Load Payment Link, verify price + description | N/A |
| VAL-04 | 20 rows in conversation tracker with all columns populated | Manual | Count tracker rows with strong_signal column scored | ❌ Wave 0: create tracker |
| VAL-05 | Go/No-Go decision documented: 10 cards OR 50 strong signals | Manual | Stripe payments count + strong signal count in tracker | ❌ Wave 0: define scoring formula |

### Sampling Rate
- **Per task:** Check the specific artifact produced (post live, Typeform live, Stripe link live)
- **Per wave:** Review engagement metrics and response counts against targets
- **Phase gate:** VAL-05 criteria met (10 credit cards OR 50 qualified strong signals) before phase closes

### Wave 0 Gaps
- [ ] `validation/conversations/tracker.csv` — covers VAL-04 (create blank tracker with correct columns)
- [ ] `validation/typeform/questions.md` — covers VAL-02 (document question spec before building the form)
- [ ] `landing/` — covers VAL-03/D-10 (create Next.js landing page project)

*(No automated test infrastructure needed — this phase produces no code under test)*

---

## Sources

### Primary (HIGH confidence)
- Stripe Documentation (docs.stripe.com/payment-links) — Payment Links no-code subscription setup confirmed
- Stripe Documentation (docs.stripe.com/billing/quickstart) — Subscription pricing confirmed, no backend required for Payment Links
- CONTEXT.md decisions D-01 through D-14 — locked constraints verified

### Secondary (MEDIUM confidence)
- Screen Studio official site (screen.studio) + community reviews — confirmed no text callout feature; recommended OBS + DaVinci Resolve as alternative
- Typeform official blog (typeform.com/blog/survey-design) — conversational survey design best practices confirmed
- B2B SaaS validation research (forumvc.com, beyondlabs.io) — 20-conversation customer discovery pattern confirmed as standard
- Reddit marketing guides (business.daily.dev, subredditsignals.com) — pain-point-first framing, community warm-up requirement confirmed across multiple sources

### Tertiary (LOW confidence — needs direct verification)
- r/devops and r/Terraform specific automod karma/age thresholds — not directly confirmed; inferred from general Reddit community patterns
- Terraform Discord server identity and posting rules — not confirmed; requires direct server membership to verify

---

## Metadata

**Confidence breakdown:**
- Stripe Payment Links (no-code): HIGH — verified via official Stripe docs
- Typeform question design: MEDIUM — verified via Typeform official blog + general B2B survey research
- Video recording toolchain: MEDIUM — verified Screen Studio limitation via multiple review sources; OBS/DaVinci recommended as well-established free alternative
- Reddit warm-up requirement: MEDIUM — consistent across multiple marketing guides; specific karma thresholds LOW (need direct r/devops sidebar check)
- Landing page (Next.js on Vercel): HIGH — project standard, already in use
- Customer discovery tracker structure: HIGH — standard industry practice confirmed across multiple sources

**Research date:** 2026-04-15
**Valid until:** 2026-07-15 (stable domain — Stripe/Typeform APIs change slowly; Reddit community rules are stable)
