---
phase: 0
slug: validation
status: draft
shadcn_initialized: false
preset: none
created: 2026-04-15
---

# Phase 0 — UI Design Contract

> Visual and interaction contract for the InfraCanvas validation landing page at infracanvas.dev.
> This is a single-page static marketing site. No component library. No design system overhead. Tailwind CSS only.

---

## Overview

**What this is:** A single-page Next.js 15 (App Router) marketing site deployed on Vercel.
**What this is not:** A SaaS app, a dashboard, or a component library consumer.
**Primary job:** Convert community traffic (Reddit, Discord, LinkedIn) into two conversion events:
1. Typeform completion (strong signal candidate)
2. Stripe founding member checkout ($49/mo)

**Single file:** `landing/app/page.tsx` contains all sections, assembled linearly. Components in `landing/components/` are simple presentational fragments — no state management, no store, no routing.

---

## Design System

**Approach:** Dark-themed, developer-credible aesthetic. Borrows from tools engineers already trust (Linear, Vercel, Fly.io). Not a typical SaaS marketing site — no gradients, no stock photos, no corporate blue. Terminal-adjacent.

**Base:** Tailwind CSS 4.x (utility-first, no custom config needed at this scale)
**No shadcn/ui.** No Radix. No component registry.
**No animations library.** CSS transitions only where needed (hover states on buttons).

**Key visual decisions:**
- Dark background (`slate-950` / `#0a0f1e`) — signals developer tool, not enterprise marketing
- Amber accent (`amber-400` / `#fbbf24`) — warm contrast against dark, used for CTAs and urgency text only
- Mono font for code snippets and the CLI command — reinforces CLI-first identity
- Maximum content width: `max-w-4xl` — readable prose width, not full-bleed marketing sprawl

---

## Spacing Scale

Uses Tailwind's default 4px base unit. All spacing uses multiples of 4px.

| Token | px | Tailwind | Usage |
|-------|----|----------|-------|
| xs    | 4  | p-1      | Icon gaps, badge padding |
| sm    | 8  | p-2      | Tight inline spacing |
| md    | 16 | p-4      | Default element padding |
| lg    | 24 | p-6      | Section-internal spacing |
| xl    | 32 | p-8      | Card padding, section gaps |
| 2xl   | 48 | py-12    | Between major sections |
| 3xl   | 64 | py-16    | Top/bottom of hero |
| 4xl   | 96 | py-24    | Full-bleed section padding |

**Vertical rhythm rule:** Sections separated by `py-16` on mobile, `py-24` on desktop. No section touches another without clear whitespace.

---

## Typography

**Font stack:**
- Body + headings: `Inter` (Google Fonts, preconnect in `layout.tsx`)
- Code/mono: `JetBrains Mono` or `font-mono` (Tailwind system mono fallback acceptable)

**No custom font loading beyond Inter.** System mono is sufficient for CLI snippets.

| Role | Size | Weight | Tailwind | Usage |
|------|------|--------|----------|-------|
| Hero headline | 48–60px | 800 | `text-5xl lg:text-6xl font-extrabold` | Primary "one command" message |
| Section heading | 30px | 700 | `text-3xl font-bold` | Value props, founding member section |
| Subheading | 20px | 600 | `text-xl font-semibold` | Individual value prop titles |
| Body | 16px | 400 | `text-base` | Paragraphs, descriptions |
| Body large | 18px | 400 | `text-lg` | Hero subtext, lead-in copy |
| Caption / label | 14px | 500 | `text-sm font-medium` | Spot counter, pricing context |
| Mono / CLI | 14px | 400 | `text-sm font-mono` | `infracanvas scan ./terraform` |

**Line height:** `leading-relaxed` (1.625) for body copy. `leading-tight` for large display headings.

---

## Color

Follows the 60/30/10 rule.

**60% — Background (neutrals):**
| Name | Hex | Tailwind | Usage |
|------|-----|----------|-------|
| Page background | `#0a0f1e` | `bg-slate-950` | Base canvas |
| Card / section bg | `#0f172a` | `bg-slate-900` | FoundingMember section, feature cards |
| Subtle border | `#1e293b` | `border-slate-800` | Dividers, card outlines |
| Muted text | `#94a3b8` | `text-slate-400` | Secondary copy, disclaimers |

**30% — Text (content layer):**
| Name | Hex | Tailwind | Usage |
|------|-----|----------|-------|
| Primary text | `#f8fafc` | `text-slate-50` | Headlines, body |
| Secondary text | `#cbd5e1` | `text-slate-300` | Subheadings, descriptions |
| Muted text | `#64748b` | `text-slate-500` | Legal, fine print |

**10% — Accent (action / urgency only):**
| Name | Hex | Tailwind | Usage |
|------|-----|----------|-------|
| Primary CTA | `#fbbf24` | `bg-amber-400` | "Claim Your Spot" button, price display |
| CTA text | `#0a0f1e` | `text-slate-950` | Text on amber buttons (contrast) |
| Urgency text | `#fbbf24` | `text-amber-400` | Spot counter, "X remaining" |
| CTA hover | `#f59e0b` | `hover:bg-amber-500` | Amber button hover state |
| Secondary CTA | transparent | `border border-slate-600` | "Tell us what you need" Typeform button |
| Secondary CTA text | `#f8fafc` | `text-slate-50` | Outlined button text |
| Secondary CTA hover | `#1e293b` | `hover:bg-slate-800` | Outlined button hover fill |

**Semantic colors (status indicators in value props):**
| Purpose | Color | Tailwind |
|---------|-------|----------|
| Security finding badge | `#ef4444` | `text-red-400` |
| Cost indicator | `#22c55e` | `text-green-400` |
| Drift marker | `#f97316` | `text-orange-400` |

---

## Page Sections

The page renders top-to-bottom in this exact order. No navigation, no sidebar.

```
[Nav bar]           — Logo + single CTA (sticky, minimal)
[Hero]              — Pain hook, headline, subtext, CLI command, primary CTAs
[Demo Video]        — Embedded video, context caption
[Value Props]       — 3 columns: Canvas / Security / Cost+Drift
[Founding Member]   — Spot counter, locked price, Stripe CTA
[Typeform CTA]      — Secondary ask: "Help us build this right"
[Footer]            — Minimal: copyright + "No spam, no sales calls"
```

---

## Section Specifications

### 1. Nav Bar

**Layout:** Fixed top, `backdrop-blur-sm bg-slate-950/80`, full width.
**Content:** Logo left (`InfraCanvas` wordmark in `font-bold text-slate-50`) + single right CTA.
**CTA:** "Get Early Access" → scrolls to `#founding-member` section (anchor link).
**Height:** `h-14`. No hamburger menu. No navigation links. Not a full navbar — a minimal strip.

---

### 2. Hero

**Layout:** Centered, `max-w-3xl mx-auto`, `pt-32 pb-20` (accounts for fixed nav).

**Pain hook** (above headline):
```
text-amber-400 text-sm font-mono uppercase tracking-widest
"5 tabs open. 0 clarity."
```

**Headline:**
```
text-5xl lg:text-6xl font-extrabold text-slate-50 leading-tight
"One command. Your entire infrastructure — visualised, scored, explained."
```

**Subtext:**
```
text-lg text-slate-300 mt-4 max-w-2xl
"InfraCanvas scans your Terraform directory and opens an interactive diagram
with security findings, cost estimates, and drift detection. AWS, Azure, and
physical data centres — in a single view."
```

**CLI command block:**
```
mt-8 bg-slate-900 border border-slate-800 rounded-lg px-6 py-4
font-mono text-sm text-slate-50
$ infracanvas scan ./terraform
```

**CTA buttons:**
```
mt-8 flex flex-col sm:flex-row gap-4 justify-center

Primary: "Claim Founding Member Spot — $49/mo"
  bg-amber-400 text-slate-950 font-bold px-8 py-3 rounded-lg
  → Stripe Payment Link (NEXT_PUBLIC_STRIPE_PAYMENT_LINK)

Secondary: "Tell us what you need"
  border border-slate-600 text-slate-50 font-medium px-8 py-3 rounded-lg
  hover:bg-slate-800
  → Typeform URL (NEXT_PUBLIC_TYPEFORM_URL)
```

**Urgency note** (below CTAs):
```
text-sm text-amber-400 font-mono
"[N] of 50 founding member spots remaining"
```

---

### 3. Demo Video

**Layout:** Full-width container, `max-w-4xl mx-auto`, `py-16`.

**Section label:**
```
text-sm font-mono text-amber-400 uppercase tracking-widest mb-4
"See it in action"
```

**Video embed:**
```
Aspect ratio: 16:9
Implementation: <iframe> (Loom or YouTube unlisted)
Tailwind: w-full aspect-video rounded-xl border border-slate-800 overflow-hidden
```

**Caption below video:**
```
text-sm text-slate-400 mt-3 text-center
"2-minute walkthrough: scan → diagram → security findings → score card"
```

**Fallback if no video yet:** Static screenshot of the viewer with a "Video coming soon" overlay badge. Do not block the section.

---

### 4. Value Props

**Layout:** `py-16`, `max-w-4xl mx-auto`.

**Section heading:**
```
text-3xl font-bold text-slate-50 text-center mb-12
"Everything you need to understand your infrastructure"
```

**Grid:** `grid grid-cols-1 md:grid-cols-3 gap-6`

Three cards, each `bg-slate-900 border border-slate-800 rounded-xl p-6`:

**Card 1 — Canvas (Infrastructure Diagrams)**
- Icon: `[map]` or SVG box icon in `text-amber-400`
- Title: `"Visual infrastructure map"` — `text-xl font-semibold text-slate-50`
- Body: `"One command generates an interactive diagram of your AWS and Azure resources, grouped by VPC and subnet, with dependency edges. No manual drawing."` — `text-slate-300 text-sm`
- Badge/tag: `"AWS + Azure"` — `text-xs font-mono text-slate-400`

**Card 2 — Security Findings**
- Icon: shield SVG in `text-red-400`
- Title: `"Security blind spots, surfaced"`
- Body: `"10 built-in AWS security rules (S3 public access, IAM wildcards, unencrypted RDS) with severity ratings and remediation steps. No config required."`
- Badge: `"10 rules at launch"` — `text-xs font-mono text-slate-400`

**Card 3 — Cost + Drift**
- Icon: chart/dollar SVG in `text-green-400`
- Title: `"Cost and drift in the same view"`
- Body: `"See cost estimates per resource and flag drift between your Terraform state and what's actually deployed. No more surprises on the AWS bill."`
- Badge: `"Coming in v1.0"` — `text-xs font-mono text-orange-400`

---

### 5. Founding Member

**ID:** `id="founding-member"` (anchor target from nav CTA and hero CTA)

**Layout:** `py-16`, `max-w-2xl mx-auto text-center`.

**Container:** `bg-slate-900 border border-amber-400/20 rounded-2xl p-10`

**Urgency counter:**
```
text-amber-400 font-mono text-sm mb-2
"[N] of 50 founding member spots remaining"
```
Note: `[N]` is the `spotsRemaining` prop. Start at 50, decrement manually on each payment.

**Heading:**
```
text-3xl font-bold text-slate-50 mb-2
"Lock in $49/mo — forever"
```

**Subtext:**
```
text-slate-300 text-base mb-6
"Price locks at $49/mo for founding members. When we launch publicly, pricing goes up.
You'll also get a private Discord channel for direct roadmap input."
```

**What you get list:**
```
text-left max-w-sm mx-auto mb-8 space-y-2

Items (checkmark + text, text-slate-300 text-sm):
- $49/mo locked forever (no price increases, ever)
- Private Discord channel — direct access to the founder
- Input on which features ship first
- Early access to every phase as it ships
```

**Primary CTA:**
```
bg-amber-400 text-slate-950 font-bold text-lg px-10 py-4 rounded-xl w-full
"Claim Your Founding Member Spot"
→ NEXT_PUBLIC_STRIPE_PAYMENT_LINK
```

**Disclaimer:**
```
text-slate-500 text-xs mt-4
"Secure checkout via Stripe. Cancel anytime. No questions asked."
```

---

### 6. Typeform CTA

**Layout:** `py-16 text-center max-w-2xl mx-auto`.

**Heading:**
```
text-2xl font-bold text-slate-50 mb-3
"Not ready to pay yet? Help us build this right."
```

**Body:**
```
text-slate-300 text-base mb-6
"We're talking to engineers who manage Terraform-managed infrastructure.
2 minutes. No sales call."
```

**CTA:**
```
border border-slate-600 text-slate-50 font-medium px-8 py-3 rounded-lg hover:bg-slate-800
"Answer 7 questions →"
→ NEXT_PUBLIC_TYPEFORM_URL
```

**Note below:**
```
text-slate-500 text-sm mt-3
"We read every response. High-signal respondents get invited for a 15-min call."
```

---

### 7. Footer

**Layout:** `border-t border-slate-800 py-8 text-center`.

```
text-slate-500 text-sm
"© 2026 InfraCanvas. No spam. No sales calls. Just infrastructure clarity."
```

Optional: social/contact link (GitHub, Twitter/X) as `text-slate-400 hover:text-slate-200` — only if accounts exist. Do not add placeholder links.

---

## Copywriting Contract

All copy below is locked. Do not paraphrase or rephrase during implementation.

### Hero

| Element | Copy |
|---------|------|
| Pain hook | `5 tabs open. 0 clarity.` |
| Headline | `One command. Your entire infrastructure — visualised, scored, explained.` |
| Subtext | `InfraCanvas scans your Terraform directory and opens an interactive diagram with security findings, cost estimates, and drift detection. AWS, Azure, and physical data centres — in a single view.` |
| CLI block | `$ infracanvas scan ./terraform` |
| Primary CTA | `Claim Founding Member Spot — $49/mo` |
| Secondary CTA | `Tell us what you need` |
| Urgency | `[N] of 50 founding member spots remaining` |

### Value Props

| Card | Title | Badge |
|------|-------|-------|
| Canvas | `Visual infrastructure map` | `AWS + Azure` |
| Security | `Security blind spots, surfaced` | `10 rules at launch` |
| Cost + Drift | `Cost and drift in the same view` | `Coming in v1.0` |

### Founding Member

| Element | Copy |
|---------|------|
| Counter | `[N] of 50 founding member spots remaining` |
| Heading | `Lock in $49/mo — forever` |
| Subtext | `Price locks at $49/mo for founding members. When we launch publicly, pricing goes up. You'll also get a private Discord channel for direct roadmap input.` |
| CTA | `Claim Your Founding Member Spot` |
| Disclaimer | `Secure checkout via Stripe. Cancel anytime. No questions asked.` |

### Typeform CTA

| Element | Copy |
|---------|------|
| Heading | `Not ready to pay yet? Help us build this right.` |
| Body | `We're talking to engineers who manage Terraform-managed infrastructure. 2 minutes. No sales call.` |
| CTA | `Answer 7 questions →` |
| Note | `We read every response. High-signal respondents get invited for a 15-min call.` |

### SEO / Meta

| Tag | Value |
|-----|-------|
| `<title>` | `InfraCanvas — Your infrastructure, visualised` |
| `meta description` | `One command gives you a complete, annotated picture of your hybrid infrastructure — security blind spots, cost, and drift — across AWS, Azure, and physical data centres.` |
| `og:title` | `InfraCanvas — One command. Your entire infrastructure.` |
| `og:description` | Same as meta description |
| `og:image` | 1200×630 screenshot of the viewer diagram (dark background) |

---

## Component List

All components are presentational (no state, no hooks unless for the counter).

| Component | File | Props | Notes |
|-----------|------|-------|-------|
| Nav | `components/Nav.tsx` | none | Sticky, minimal |
| Hero | `components/Hero.tsx` | `spotsRemaining: number` | Pain hook + headline + CTAs |
| DemoVideo | `components/DemoVideo.tsx` | `embedUrl: string` | iframe wrapper with aspect-video |
| ValueProps | `components/ValueProps.tsx` | none | Static 3-card grid |
| FoundingMember | `components/FoundingMember.tsx` | `spotsRemaining: number` | Stripe CTA block |
| TypeformCTA | `components/TypeformCTA.tsx` | none | Secondary ask section |
| Footer | `components/Footer.tsx` | none | Single-line copyright |

`spotsRemaining` is passed from `page.tsx` as a static constant. No API call at this stage.

```typescript
// landing/app/page.tsx
const SPOTS_REMAINING = 50 // Update manually after each payment and redeploy
```

---

## Environment Variables

All external URLs are env vars. No hardcoded external links in component files.

| Variable | Example | Used by |
|----------|---------|---------|
| `NEXT_PUBLIC_STRIPE_PAYMENT_LINK` | `https://pay.stripe.com/...` | Hero, FoundingMember |
| `NEXT_PUBLIC_TYPEFORM_URL` | `https://form.typeform.com/to/...` | Hero, TypeformCTA |
| `NEXT_PUBLIC_DEMO_VIDEO_URL` | `https://www.loom.com/embed/...` | DemoVideo |

Add to Vercel project environment settings (not committed to repo).

---

## Responsive Behaviour

| Breakpoint | Key changes |
|------------|-------------|
| Mobile (`< 640px`) | Hero CTAs stack vertically. Value props in 1 column. FoundingMember full-width. |
| Tablet (`640–1024px`) | Hero CTAs in row. Value props in 1 column (md: 3 columns). |
| Desktop (`> 1024px`) | Value props 3-column. Max-width containers centered. |

No custom breakpoints. Tailwind defaults (`sm:`, `md:`, `lg:`) only.

---

## Performance Constraints

This is a static Vercel site. It must meet:

- First Contentful Paint: < 1.5s
- No JavaScript required for above-the-fold rendering (Next.js SSG)
- No client-side data fetching (counter is a static prop from `page.tsx`)
- Total page weight: < 200KB (excluding video iframe)
- Inter font: loaded via `next/font/google` with `display: swap`

---

## Registry Safety

No component registry in use. No shadcn/ui. No Radix UI. No external UI packages beyond Tailwind CSS.

**Allowed dependencies:**
- `tailwindcss` — already in project
- `next` — landing page framework
- `react`, `react-dom` — framework deps
- `next/font` — Google Fonts loading (built-in, zero extra package)

**Do not add:**
- `@radix-ui/*` — not needed for a 7-section static page
- `framer-motion` — no animations required
- `shadcn/ui` — overkill for this scope
- `react-icons` — use inline SVGs or Lucide only if already installed

**SVG icons:** Use inline SVGs or Heroicons copy-pasted as TSX. Do not install an icon package for 3-5 icons.

---

## Accessibility Minimums

- All `<a>` CTAs have descriptive `aria-label` when the visible text is ambiguous
- Video iframe has `title` attribute: `title="InfraCanvas demo video"`
- Color contrast: amber-400 on slate-950 passes WCAG AA (4.8:1 ratio)
- Page has a single `<h1>` (hero headline). All other headings use `<h2>` / `<h3>` in order.
- `<main>` wraps all page sections. `<header>` wraps Nav. `<footer>` wraps Footer.

---

## Checker Sign-Off

- [ ] Pain hook copy matches contract exactly
- [ ] Hero headline copy matches contract exactly
- [ ] CLI block renders in monospace with `$` prefix
- [ ] Primary CTA links to `NEXT_PUBLIC_STRIPE_PAYMENT_LINK` env var (not hardcoded)
- [ ] Secondary CTA links to `NEXT_PUBLIC_TYPEFORM_URL` env var (not hardcoded)
- [ ] `spotsRemaining` renders in both Hero and FoundingMember sections
- [ ] `id="founding-member"` present on the FoundingMember section
- [ ] Nav CTA is an anchor link to `#founding-member`
- [ ] Demo video renders as 16:9 iframe with border and rounded corners
- [ ] Value props render as 3-column grid on desktop, 1-column on mobile
- [ ] FoundingMember section has amber border accent (`border-amber-400/20`)
- [ ] No hardcoded external URLs in component files
- [ ] `SPOTS_REMAINING` constant in `page.tsx` (not in a component file)
- [ ] `<title>` and `meta description` match SEO contract
- [ ] `og:image` configured in `layout.tsx`
- [ ] Inter font loaded via `next/font/google`
- [ ] Page renders without JavaScript (Next.js SSG confirmed)
- [ ] No `@radix-ui`, `framer-motion`, or `shadcn` packages added
- [ ] Lighthouse mobile Performance score > 90

---

*UI-SPEC written: 2026-04-15*
*Phase: 00-validation*
*Covers: VAL-03 (Stripe page) and D-06/D-09/D-10 (landing page decisions)*
