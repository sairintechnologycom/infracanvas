# Discord Post — Terraform Community

> **IMPORTANT:** Before posting, join the Terraform Discord and identify the correct channel for tool sharing. Some servers have strict self-promotion rules. Common channel names: #show-and-tell, #tools, #tooling, #resources, #community-projects. Read the server rules and pinned messages before posting. If there is no suitable channel, ask a moderator before sharing.

> **Note on server identity:** There are multiple Terraform-adjacent Discord servers. Confirm which server is active and relevant (HashiCorp official, DevOps community servers, etc.). The specific server and channel are not confirmed in planning documents — research this before preparing to post.

---

## Message Draft (shorter, casual format)

Hey — wanted to share something I've been building.

If you've ever stared at a Terraform module trying to understand what resources depend on what, or had to correlate tfsec findings with Infracost estimates by hand — this might be useful.

It's called InfraCanvas. One command: `infracanvas scan ./terraform`. It builds an interactive diagram from your HCL files — VPC groupings, dependency edges, security finding badges per resource, cost estimates, drift from `terraform plan`. Output is a single HTML file you can share with your team.

Short demo: https://infracanvas.dev

Happy to hear how you handle this today, what's painful, what I'm missing. Always learning from how people actually use Terraform at scale.

*(Full disclosure: I built it.)*

---

## Posting Notes

- **Tone:** More casual and conversational than Reddit posts. Discord culture rewards directness.
- **Length:** Keep it shorter than Reddit. One tight message, not three paragraphs.
- **CTA:** Link to infracanvas.dev only — not directly to Typeform or Stripe (per D-06).
- **Timing:** Post 1–2 weeks after r/Terraform post in the stagger sequence (D-05).
- **Disclosure:** Include the "(Full disclosure: I built it.)" line.
- **Engagement:** Stick around in the thread after posting. Discord communities respond well to active participation.
- **Community rules:** Some Discord servers explicitly ban product promotion or require moderator approval. Check before posting.

---

## Pre-Post Checklist

- [ ] Server and channel identified and confirmed to allow tool sharing
- [ ] Server rules read — no prohibition on self-promotion in the selected channel
- [ ] r/Terraform post has already been live for at least 1 week
- [ ] infracanvas.dev and demo still live
