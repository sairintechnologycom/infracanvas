# Report Card

`infracanvas score` gives your infrastructure a letter grade across five dimensions — a single number you can drop into Slack, a PR description, or a post-incident review.

## Generate a score

```bash
infracanvas score ./terraform
```

Output: `infracanvas-score.html` (opens in your browser).

## The five dimensions

| Dimension | What it measures |
|-----------|------------------|
| **Security** | Public exposure, open security groups, wildcard IAM |
| **Encryption** | S3 / EBS / RDS encryption at rest, KMS rotation |
| **IAM Hygiene** | Least-privilege, unused roles, wildcard actions |
| **Cost Efficiency** | Oversized instances, idle resources, un-tiered storage |
| **Tagging** | Required tags present on billable resources |

## Grading scale

| Grade | Meaning |
|-------|---------|
| A | No critical / high findings; ≥ 95% on that dimension |
| B | Minor findings only |
| C | Medium findings present |
| D | One or more high findings |
| F | One or more critical findings |

The overall grade is the **lowest** per-dimension grade — one critical finding drops the whole card to F.

## Sharing the score

- **Slack / PR**: attach `infracanvas-score.html` directly
- **README badge**: export JSON and render your own badge

  ```bash
  infracanvas score ./terraform --json > score.json
  ```

## Improving your grade

1. Open the report — findings are ordered by severity
2. Apply the remediation shown on each finding card
3. Re-run `infracanvas score` to confirm the grade moved

## Ignoring rules

Some rules don't apply to every environment (e.g. tag enforcement in `dev`). Silence them in `.infracanvas.yml`:

```yaml
ignore_rules:
  - SEC-010   # tagging
```
