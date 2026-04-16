## Submission Details

- **URL**: https://github.com/infracanvas/infracanvas
- **Title**: Show HN: InfraCanvas – A report card for your Terraform infrastructure
- **Target**: news.ycombinator.com/submit

---

## Body

I built a CLI that gives your Terraform infrastructure a letter grade (A–F) across Security, Encryption, IAM Hygiene, Cost Efficiency, and Tagging — like a credit score for your cloud.

**The problem:** I was tired of correlating 5 different tools to answer "is our infrastructure in the state we think it is?" Tfsec for security, Infracost for cost, a diagram tool that requires a login, manual Terraform plan diffs. None of them talk to each other.

**What it does:** One command (`infracanvas scan ./terraform`) produces a self-contained interactive HTML diagram with VPC grouping, security findings with severity badges, and cost estimates per resource. No server. No account. Share the file in Slack.

**The Report Card mechanic:** `infracanvas score` generates a standalone HTML report card with a letter grade across 5 dimensions. I wanted something you could paste in a PR comment or share on Slack before a production deploy — "here's our infrastructure health: B+, two high-severity findings to address."

**Technical details:**
- Python CLI (pip installable), React/ReactFlow viewer, single-file HTML export
- 10 security rules (S3, IAM, RDS, EC2, KMS, networking) — YAML, extensible
- 15 AWS resource types supported in v0.1
- Drift detection: overlay `terraform plan` changes on the diagram
- MIT licensed, open-source CLI core

**What's next:** Azure support, shadow infrastructure detection (live AWS API vs Terraform state), custom policy engine.

Try it:

```bash
pip install infracanvas && infracanvas scan ./your-tf-dir
```

GitHub: https://github.com/infracanvas/infracanvas
Site: https://infracanvas.dev
