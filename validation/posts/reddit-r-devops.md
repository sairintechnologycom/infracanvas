# Reddit Post — r/devops

> **IMPORTANT:** Do NOT post this until the warm-up period is complete. See `validation/posts/warmup-guide.md` for requirements (30+ day account age, 50+ combined karma, 2–4 weeks of genuine community participation).

---

## Suggested Title

> I was spending 20 minutes per incident correlating 5 different tools to understand our infra. So I built something.

---

## Post Body

Every time something goes wrong in our environment, I'd open the same five tabs: AWS Console to find the resource, Terraform to check what state we thought it was in, tfsec to see if there were any relevant security findings, Infracost to understand what it was costing us, and draw.io (or Lucidchart, depending on the day) to get the topology picture. None of them talked to each other. Every incident started with 15–20 minutes of manual correlation before I could even understand the blast radius.

I kept wondering: why doesn't a single tool give me a complete picture — the diagram, the security posture, the cost, the drift from what Terraform thinks is deployed? I'm not asking for something that auto-remediates or connects to live AWS. Just: run a command against my Terraform files, give me one annotated diagram I can actually reason about.

So I built it. It's called InfraCanvas. One CLI command — `infracanvas scan ./terraform` — parses your HCL files, builds a ReactFlow diagram with VPC/subnet grouping, overlays security findings with severity badges, adds per-resource cost estimates, and detects drift from your Terraform plan. The output is a single self-contained HTML file with no external dependencies — you can share it with your team or drop it in a PR.

Here's a 2-minute demo: https://infracanvas.dev

If this resonates with how you've been working, I'd genuinely love 15 minutes of your time to understand your workflow — what your toolchain looks like, what's painful, what you wish existed: https://infracanvas.dev

Full disclosure: I'm the maker. Happy to answer any questions about how it works or what's on the roadmap.

---

## Posting Notes

- **Platform:** r/devops
- **Framing:** Pain-point story first (D-04). Product is the punchline, not the lead.
- **CTA:** Links go to infracanvas.dev only — NOT directly to Typeform or Stripe (per D-06)
- **Timing:** Post first in the platform stagger sequence (D-05). Wait 1–2 weeks before posting to r/Terraform.
- **Disclosure:** Include the "Full disclosure: I'm the maker" line. r/devops culture penalises undisclosed self-promotion.
- **Flair:** Check current r/devops flair options. "Discussion" or "Tools & Resources" are typical candidates.
- **Video:** If the demo video is embedded (Reddit natively plays MP4 and supports Loom/YouTube embeds), embed it inline. If linking, use the infracanvas.dev URL which hosts the video.

---

## Pre-Post Checklist

- [ ] Reddit account is 30+ days old
- [ ] Account has 50+ combined karma from genuine r/devops / r/Terraform participation
- [ ] No self-promotional posts in account history during warm-up period
- [ ] infracanvas.dev landing page is live with the demo video
- [ ] Typeform is live and accepting responses (Typeform Basic activated)
- [ ] Demo video is uploaded and playable
- [ ] Warm-up guide requirements met (see `validation/posts/warmup-guide.md`)
