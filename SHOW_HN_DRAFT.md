## Submission Details

- **URL**: https://github.com/sairintechnologycom/infracanvas
- **Title**: Show HN: InfraCanvas — Turn your Terraform repo into an interactive security diagram (AWS + Azure)
- **Target**: news.ycombinator.com/submit

Title alternatives (pick whichever performs best in the title preview):
- *Show HN: One command turns your Terraform into an interactive security diagram*
- *Show HN: InfraCanvas — Terraform → annotated architecture diagram + CIS findings*
- *Show HN: A report card for your hybrid-cloud Terraform (AWS + Azure)*

---

## Body

I built a CLI that turns a directory of Terraform code into a self-contained interactive HTML diagram with security findings and a letter-grade report card. AWS and Azure, ~50 CIS-tagged rules, runs entirely on your laptop, no cloud credentials, no SaaS account.

**The problem.** I was tired of stitching five tools together to answer "is our infrastructure in the state we think it is?" — tfsec for security, Infracost for cost, a diagram tool that wants a login, manual `terraform plan` diffs. None of them produce one artifact you can drop in a Slack thread.

**What it does.** One command:

```bash
pip install infracanvas
infracanvas scan ./your-terraform-dir
```

~5 seconds later your browser opens a 3.5 MB self-contained HTML file with:
- Every resource as a node, color-coded by service, dragged-and-zoomable
- VPC / region / subnet grouping rendered as background containers
- Click any node → side panel with all attributes, dependencies, and findings
- Severity badges (Critical / High / Medium / Info) on offending nodes
- A separate `infracanvas score` command produces a shareable A–F letter-grade card across Security / Encryption / IAM Hygiene / Cost Efficiency / Tagging
- Drift overlay: pass `--planfile out.json` and see added (green) / changed (amber) / deleted (red) nodes

**It's deliberately not a SaaS.** The CLI reads `.tf` files on disk. It never calls AWS or Azure APIs. No `aws configure` needed, no IAM role to grant, no security review to file. Works offline, works in CI, works in air-gapped customer environments. The HTML is a static file — you can email it, paste it in a Slack thread, attach to a PR.

**Rule coverage.** ~50 rules tagged with CIS / NIST / SOC2 / PCI-DSS / HIPAA framework IDs. On a deliberately-bad multi-cloud fixture (S3 public-read, RDS publicly_accessible + storage_encrypted=false + hardcoded password, IAM Action:* Resource:* policy, Azure NSG allowing 22/3389 from 0.0.0.0/0, storage public + TLS 1.0, SQL Server public + hardcoded admin password) it catches ~85% of the high-impact CIS controls a buyer would test against, including hardcoded secrets (`password = "literal"` in Terraform source).

**Technical bits:**
- Python 3.12 CLI, single PyPI install
- React + @xyflow/react viewer bundled as a single HTML file at install time
- HCL parsed via `python-hcl2`, deps graph via NetworkX
- Rules are YAML — extensible, ~10 lines per rule
- Drift via `terraform show -json plan.bin`
- Cost estimates from embedded us-east-1 pricing tables
- MIT, open-core (CLI + ~50 baseline rules free; managed dashboard for teams later)

**What it doesn't do yet:** GCP, Pulumi, CloudFormation, click-ops drift detection (i.e. resources in your AWS account but not in Terraform). The DC-agent for on-prem networking is in beta but not shipped as part of this release.

Standalone binaries (no Python needed) on the GitHub Release for Linux / macOS / Windows.

PyPI: https://pypi.org/project/infracanvas/
GitHub: https://github.com/sairintechnologycom/infracanvas
Site: https://infracanvas.dev

Feedback especially welcome on (1) rule false-positive rate against your real Terraform, (2) what the next provider should be, (3) whether the "single-file HTML you can paste in Slack" workflow lands or feels weird.

---

## Pre-submission checklist

- [ ] Submit between Tue–Thu, 8–10 am Pacific (highest HN traffic window)
- [ ] First comment within 2 min: short note about *why* you built it (one paragraph, personal — what tool you were trying to use that didn't work)
- [ ] Have a 30-second screen recording GIF ready to drop in the thread if someone asks "what does it look like" — link to it, don't inline
- [ ] Run `infracanvas scan` against your own repo right before submitting and verify the HTML opens cleanly in a private-window browser
- [ ] Monitor the thread for the first 2 hours; reply to *every* comment, even one-liners — this is what gets you on the front page
- [ ] Don't ask for upvotes anywhere — instant flag
- [ ] If a commenter finds a bug, fix it within the day and reply on the thread linking to the commit / new release. Nothing builds Show HN credibility faster.

## Sub-bar metrics to watch

- 2-hour vote velocity: 15+ upvotes in the first 2 hours usually = front-page ride
- Comment-to-vote ratio: aim for >0.3 (substantive discussion beats pure upvotes)
- PyPI download count from `pypistats` 24h after submission

## Post-launch landing pad

After the post, expect:
- Issues asking "what about GCP / Pulumi / OpenTofu"
- People running it against their employer's monorepo and reporting parse errors on custom modules
- One or two false-positive reports against the new SEC-031/SEC-032/AZ-011 secret-detection rules — be ready to add a `--ignore` example to the README
