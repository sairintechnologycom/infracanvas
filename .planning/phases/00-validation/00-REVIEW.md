---
phase: 00-validation
reviewed: 2026-04-16T00:00:00Z
depth: standard
files_reviewed: 24
files_reviewed_list:
  - landing/app/globals.css
  - landing/app/layout.tsx
  - landing/app/page.tsx
  - landing/components/DemoVideo.tsx
  - landing/components/Footer.tsx
  - landing/components/FoundingMember.tsx
  - landing/components/Hero.tsx
  - landing/components/Nav.tsx
  - landing/components/TypeformCTA.tsx
  - landing/components/ValueProps.tsx
  - landing/next.config.ts
  - landing/package.json
  - landing/postcss.config.mjs
  - landing/tsconfig.json
  - validation/conversations/scoring-guide.md
  - validation/conversations/tracker.csv
  - validation/demo/video-script.md
  - validation/go-no-go/decision-framework.md
  - validation/posts/discord-terraform.md
  - validation/posts/linkedin.md
  - validation/posts/reddit-r-devops.md
  - validation/posts/reddit-r-terraform.md
  - validation/posts/warmup-guide.md
  - validation/typeform/questions.md
findings:
  critical: 2
  warning: 3
  info: 4
  total: 9
status: issues_found
---

# Phase 00: Code Review Report

**Reviewed:** 2026-04-16T00:00:00Z
**Depth:** standard
**Files Reviewed:** 24
**Status:** issues_found

## Summary

Reviewed the full landing site (Next.js 15 / React 18 / Tailwind CSS 4) and all validation content artifacts. The landing components are simple, well-structured server components with no client-side logic, which is appropriate for this use case. Two critical issues were found: unguarded `process.env` values rendered directly as `href` attributes on `<a>` tags (potential open-redirect / broken-link risk), and the `output: 'export'` static-export mode in `next.config.ts` which is incompatible with Vercel's native deployment model while also silently breaking the `NEXT_PUBLIC_*` env var pipeline if the build is triggered on CI without those vars set. Three warnings cover missing `sandbox` on the video iframe, a broken self-referencing `tsconfig.json` path alias, and a logic gap in the spots-remaining counter. Four info-level items cover dead code, minor accessibility gaps, and a CSV privacy note.

---

## Critical Issues

### CR-01: Unguarded env var used directly as `href` — silent broken links and open-redirect potential

**File:** `landing/components/Hero.tsx:20`, `landing/components/Hero.tsx:29`, `landing/components/FoundingMember.tsx:20`

**Issue:** `process.env.NEXT_PUBLIC_STRIPE_PAYMENT_LINK` and `process.env.NEXT_PUBLIC_TYPEFORM_URL` are passed directly as `href` values with no fallback and no validation. In Next.js static export (`output: 'export'`), if these env vars are absent at build time the rendered HTML will contain `href="undefined"` — a literal string — which is a broken link in production. More importantly, `NEXT_PUBLIC_*` values are inlined at build time and cannot be patched at runtime; any misconfiguration silently ships broken CTAs. If a string is ever provided that is not an absolute HTTPS URL (e.g., an accidentally relative path), the `target="_blank"` anchor becomes an open redirect.

**Fix:**
```tsx
// Define validated helpers, e.g. in landing/lib/env.ts
function requireEnv(key: string): string {
  const val = process.env[key]
  if (!val) throw new Error(`Missing required env var: ${key}`)
  return val
}

// In page.tsx, validate at build time (server component — throws at build, not runtime):
const stripeUrl = requireEnv('NEXT_PUBLIC_STRIPE_PAYMENT_LINK')
const typeformUrl = requireEnv('NEXT_PUBLIC_TYPEFORM_URL')

// Pass as typed props to Hero and FoundingMember:
<Hero spotsRemaining={SPOTS_REMAINING} stripeUrl={stripeUrl} typeformUrl={typeformUrl} />
<FoundingMember spotsRemaining={SPOTS_REMAINING} stripeUrl={stripeUrl} />
<TypeformCTA typeformUrl={typeformUrl} />
```

This surfaces missing configuration at build time rather than shipping silent `href="undefined"` to production.

---

### CR-02: `output: 'export'` conflicts with stated Vercel deployment target

**File:** `landing/next.config.ts:7`

**Issue:** `output: 'export'` forces a fully static HTML/CSS/JS export to an `out/` directory. The inline comment even acknowledges this should be removed for Vercel. On Vercel, this mode disables ISR, image optimisation, and — critically — it means `process.env.NEXT_PUBLIC_*` values must be available at `next build` time with no runtime override. If the Vercel project does not have these env vars configured before the first deploy, the CTAs (`href="undefined"`) will go live silently. This is the root enabler of CR-01's production impact.

**Fix:** Remove `output: 'export'` when deploying to Vercel. Keep it only if intentionally targeting a CDN/S3 static host (not the stated constraint). If static export is genuinely intended, add a CI build check that fails when `NEXT_PUBLIC_STRIPE_PAYMENT_LINK` or `NEXT_PUBLIC_TYPEFORM_URL` are unset:

```ts
// next.config.ts — for static export only
const nextConfig: NextConfig = {
  output: 'export',
}

// Validate required env vars at config evaluation time:
const requiredEnvVars = [
  'NEXT_PUBLIC_STRIPE_PAYMENT_LINK',
  'NEXT_PUBLIC_TYPEFORM_URL',
  'NEXT_PUBLIC_DEMO_VIDEO_URL',
]
for (const key of requiredEnvVars) {
  if (!process.env[key]) {
    throw new Error(`Build aborted: required env var "${key}" is not set.`)
  }
}

export default nextConfig
```

---

## Warnings

### WR-01: `<iframe>` missing `sandbox` attribute — third-party video embed runs unrestricted

**File:** `landing/components/DemoVideo.tsx:8`

**Issue:** The video embed iframe has no `sandbox` attribute. Without sandboxing, the embedded origin (Loom, YouTube, or any URL supplied via `NEXT_PUBLIC_DEMO_VIDEO_URL`) can execute scripts in the same browsing context, navigate the top-level frame, and access storage. This is a low-severity issue today because the URL is controlled, but it is a defence-in-depth gap.

**Fix:**
```tsx
<iframe
  src={embedUrl}
  className="w-full aspect-video rounded-xl border border-slate-800"
  title="InfraCanvas demo video"
  allowFullScreen
  sandbox="allow-scripts allow-same-origin allow-presentation allow-popups"
/>
```

`allow-scripts` + `allow-same-origin` is required for most video players to function. `allow-presentation` enables fullscreen. `allow-popups` allows the player's own external links. This prevents top-frame navigation from the embedded content.

---

### WR-02: `tsconfig.json` path alias `@/*` maps to `./` (project root) — will not resolve as expected

**File:** `landing/tsconfig.json:25`

**Issue:** The path alias is:
```json
"paths": {
  "@/*": ["./"]
}
```
The conventional mapping is `"@/*": ["./*"]` (note the trailing `*` in the value array). Without the wildcard in the value, `@/components/Hero` will attempt to resolve to the literal directory `./` rather than `./components/Hero`. This alias will silently fail to resolve any subpath imports. Because all current imports use relative paths, this bug is latent — but if any future code uses `@/` aliases it will produce a confusing build error.

**Fix:**
```json
"paths": {
  "@/*": ["./*"]
}
```

---

### WR-03: `SPOTS_REMAINING` is a hardcoded constant with no guard against going negative or exceeding 50

**File:** `landing/app/page.tsx:7`

**Issue:** The comment `// Update manually after each payment and redeploy` is the only mechanism keeping this number accurate. There is no guard preventing `SPOTS_REMAINING` from being set to a negative number or a value above 50, both of which would produce nonsensical UI copy ("−3 of 50 founding member spots remaining"). This is a logic correctness issue in the rendering path.

**Fix:**
```ts
const RAW_SPOTS = 50 // Update manually after each payment and redeploy
const SPOTS_REMAINING = Math.max(0, Math.min(50, RAW_SPOTS))
```

This costs nothing and prevents accidentally deploying negative or out-of-range copy.

---

## Info

### IN-01: `<footer>` wrapper in `layout.tsx` is redundant — `Footer` component renders a `<div>`, not semantic HTML

**File:** `landing/app/layout.tsx:37`, `landing/components/Footer.tsx:1`

**Issue:** `layout.tsx` wraps `<Footer />` in a `<footer>` element, but `Footer.tsx` renders a `<div>` as its root. The semantic landmark (`<footer>`) is on the layout wrapper, which is correct, but the inner `<div>` creates unnecessary nesting. Similarly, `Nav` is wrapped in `<header>` in layout while rendering a `<nav>` internally — this produces `<header><nav>` nesting which is valid but slightly redundant.

**Fix:** Either remove the `<header>` / `<footer>` wrappers in `layout.tsx` and make the components responsible for their own semantic element, or keep the wrappers and simplify the inner components. The former is cleaner:

```tsx
// layout.tsx
<Nav />          {/* Nav renders <nav> */}
<main>{children}</main>
<Footer />       {/* Footer renders its own landmark */}
```

---

### IN-02: `DemoVideo` renders nothing meaningful when `embedUrl` is an empty string — section heading still appears

**File:** `landing/components/DemoVideo.tsx:7`

**Issue:** When `NEXT_PUBLIC_DEMO_VIDEO_URL` is unset, `page.tsx` passes `embedUrl=""`. The component renders the "See it in action" label and the "Video coming soon" placeholder, which is acceptable. However the section-level heading `<p className="text-sm font-mono...">See it in action</p>` uses a `<p>` tag styled to look like a section label. This is not a heading landmark and will be skipped by screen readers navigating by headings.

**Fix:** Use a visually styled `<h2>` (or `<span aria-hidden>` if purely decorative) for the "See it in action" label to maintain heading hierarchy. The same pattern appears in `FoundingMember.tsx:5` and `Hero.tsx:4` where visually prominent labels are `<p>` elements.

---

### IN-03: `validation/conversations/tracker.csv` contains a real-looking PII record

**File:** `validation/conversations/tracker.csv:2`

**Issue:** The CSV contains a sample row with the name "Jane Doe" dated `2026-04-20` (a future date from today's perspective). This is clearly a placeholder/fixture. However the scoring guide's own privacy note states: "This file may contain names and email addresses of respondents. Store it in the local git repository only." The file is currently committed to the repository. Ensure that as real respondent data accumulates, this file is either added to `.gitignore` or moved to a non-public location. The sample row itself is harmless but the pattern of committing this file should be reviewed before real PII arrives.

**Fix:** Consider adding a `.gitignore` rule now, before real data is collected:
```
validation/conversations/tracker.csv
```
Keep a `tracker.csv.example` with only the header row and the sample fixture as documentation.

---

### IN-04: `reddit-r-devops.md` post body contains a duplicate CTA link pointing to the same URL twice

**File:** `validation/posts/reddit-r-devops.md:22-23`

**Issue:** The post body includes two consecutive links to `https://infracanvas.dev` — one framed as a demo link and one as a survey invitation — but both resolve to the same URL. If the Typeform survey URL is different from the landing page URL, the second link should point to the Typeform directly (once it is live). Per D-06, the Reddit posts intentionally avoid linking directly to Typeform — this is correct — but the duplicate phrasing ("Here's a 2-minute demo: infracanvas.dev" followed immediately by "I'd love 15 minutes... https://infracanvas.dev") reads redundantly and may dilute the CTA.

**Fix:** Consolidate to a single link in the post body, or differentiate the two CTAs with distinct anchor text. This is a content quality note, not a blocking issue.

---

_Reviewed: 2026-04-16T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
