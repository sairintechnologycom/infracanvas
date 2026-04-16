# Reddit Post — r/Terraform

> **IMPORTANT:** Post this 1–2 weeks AFTER the r/devops post per D-05 stagger strategy. Read the engagement and comments on the r/devops post first — refine this draft based on what resonated or what critics said.

---

## Suggested Title

> I got tired of mentally mapping resource dependencies from HCL files, so I made a tool that draws the diagram for you

---

## Post Body

If you've worked on a Terraform codebase with more than a few modules, you know the feeling: you're trying to understand a resource, so you grep through `.tf` files tracing `module.` references, `data.` lookups, and implicit `depends_on` chains. Eventually you sketch a rough diagram on paper (or draw.io, or a whiteboard) just to hold the picture in your head long enough to make a decision.

The deeper the module nesting, the worse it gets. Three levels in, and you're reading five files simultaneously trying to reconstruct the topology. And when you add tfsec or Checkov to the picture — those findings reference resources by type and name, which you then have to map back to the module where they actually live. It's a lot of context-switching for what should be a simple "what does this infrastructure look like?" question.

InfraCanvas parses your HCL files and renders the full infrastructure as an interactive diagram: VPC/subnet groupings, resource icons, dependency edges, security findings per resource (with severity badges and remediation guidance), cost estimates from your provider config, and drift overlays from `terraform plan` output. It's `infracanvas scan ./terraform` — one command, one HTML file.

Demo and early access: https://infracanvas.dev

If you've built any tooling around Terraform visualisation or want to share what your current workflow looks like, I'd love to hear it — either as a comment here or in the survey at infracanvas.dev.

Full disclosure: I built this. Questions welcome.

---

## Posting Notes

- **Platform:** r/Terraform
- **Framing:** Terraform-specific pain (module complexity, dependency tracing, per-resource security findings). Same pain-point-first structure as r/devops post (D-04).
- **CTA:** Links go to infracanvas.dev only — NOT directly to Typeform or Stripe (per D-06)
- **Timing:** Post 1–2 weeks AFTER r/devops post (D-05). This gives time to incorporate feedback from r/devops into the pitch.
- **Refinement:** Before posting, review comments on the r/devops post. Incorporate language from comments that showed strong resonance. Address objections preemptively in the body.
- **Flair:** Check r/Terraform flair options. "Tools" or "Show r/Terraform" are typical candidates.

---

## Stagger Reminder (D-05)

The platform stagger sequence is:

1. **r/devops** — first, learn from engagement
2. **r/Terraform** — 1–2 weeks later, refined pitch
3. **Discord (Terraform)** — 1–2 weeks after r/Terraform
4. **LinkedIn** — last in sequence

Do not post all platforms on the same day or within the same week. Cross-posted content within a short window gets flagged as spam.

---

## Pre-Post Checklist

- [ ] r/devops post has been live for at least 1 week
- [ ] r/devops post feedback incorporated into this draft
- [ ] infracanvas.dev and Typeform still live and working
- [ ] Warm-up participation in r/Terraform is established (comments, karma)
