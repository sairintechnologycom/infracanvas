# InfraCanvas

**One command. Complete infrastructure picture. Security scores included.**

Run one command against your Terraform directory and get an interactive diagram with VPC grouping, security findings, and a letter-graded Report Card — all in a single shareable HTML file.

```bash
pip install infracanvas
infracanvas scan ./your-terraform-directory
# Browser opens with interactive diagram + security score
```

---

## Report Card

`infracanvas score` gives your infrastructure a credit score — an A–F letter grade across 5 dimensions, shareable on Slack or in a PR.

```bash
infracanvas score ./terraform
```

Dimensions scored: **Security · Encryption · IAM Hygiene · Cost Efficiency · Tagging**

Like a credit score for your cloud: instant signal, no manual correlation. Share it on Slack, paste it in a PR, or attach it to a post-incident review.

---

## Quick Start

```bash
# 1. Install
pip install infracanvas

# 2. Scan your Terraform directory
infracanvas scan ./your-terraform-directory

# 3. Browser opens with interactive diagram + security score
```

---

## What You Get

- **Interactive infrastructure diagram** — VPC grouping, subnets, security groups, auto-arranged by network topology
- **Security findings** — severity badges (Critical / High / Medium / Info) with remediation guidance
- **Infrastructure Report Card** — A–F letter grade across 5 dimensions (Security, Encryption, IAM Hygiene, Cost Efficiency, Tagging)
- **Single-file HTML** — share with anyone, no server, no dependencies
- **Drift detection** — overlay `terraform plan` changes on the diagram (added / changed / deleted)
- **Cost estimates** — per-resource and per-group (us-east-1)

> Finding details and score breakdowns require a founding member subscription ($49/mo) — [infracanvas.dev](https://infracanvas.dev)

---

## Installation

```bash
# PyPI (recommended)
pip install infracanvas

# Homebrew (coming soon)
brew install infracanvas/infracanvas/infracanvas

# From source
git clone https://github.com/infracanvas/infracanvas
cd infracanvas && pip install -e cli/
```

---

## Commands

| Command | Description |
|---------|-------------|
| `infracanvas scan <dir>` | Generate interactive HTML diagram with security findings |
| `infracanvas score <dir>` | Generate shareable Report Card (A–F letter grade) |
| `infracanvas plan <dir> --planfile plan.json` | Overlay terraform plan changes on diagram |
| `infracanvas serve <dir>` | Serve live-updating diagram in browser |
| `infracanvas export <dir>` | Export JSON graph for tooling integration |

---

## Supported AWS Resources (15)

`aws_instance` · `aws_s3_bucket` · `aws_security_group` · `aws_vpc` · `aws_subnet` ·
`aws_internet_gateway` · `aws_nat_gateway` · `aws_lb` · `aws_rds_instance` ·
`aws_lambda_function` · `aws_iam_role` · `aws_iam_policy` · `aws_kms_key` ·
`aws_cloudfront_distribution` · `aws_ebs_volume`

---

## Security Rules (10 built-in)

| ID | Severity | Title |
|----|----------|-------|
| SEC-001 | Critical | S3 Bucket Publicly Accessible |
| SEC-002 | High | S3 Bucket Missing Encryption |
| SEC-003 | Critical | Security Group Allows SSH/RDP from Internet |
| SEC-004 | High | Security Group Allows All Traffic from Internet |
| SEC-005 | Critical | RDS Instance Publicly Accessible |
| SEC-006 | High | RDS Instance Missing Encryption |
| SEC-007 | Critical | IAM Policy with Wildcard Action |
| SEC-008 | High | EBS Volume Unencrypted |
| SEC-009 | Medium | KMS Key Rotation Disabled |
| SEC-010 | Info | Missing Required Tags |

---

## CI/CD Integration

```yaml
- name: InfraCanvas Security Gate
  run: |
    pip install infracanvas
    infracanvas scan ./terraform --ci --severity high
    # Exit 0: no findings at or above threshold
    # Exit 1: findings found
    # Exit 2: parse error
```

---

## Configuration

Create `.infracanvas.yml` in your project root:

```yaml
severity_threshold: high
ignore_rules:
  - SEC-010   # tagging not enforced in dev
open_browser: false
output_dir: ./reports
```

---

## Requirements

- Python 3.12+
- Terraform files (`.tf`) in the target directory

---

## License

MIT — see [LICENSE](LICENSE)

## Contributing

Issues and PRs welcome. See [infracanvas.dev](https://infracanvas.dev) for the roadmap.
