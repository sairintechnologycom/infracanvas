# InfraCanvas

> One command. Full picture. Every blind spot visible.

Interactive Terraform architecture diagrams with security findings, drift detection, and cost estimates.

```
pip install infracanvas
```

## Quickstart

```bash
# Interactive HTML diagram with security annotations
infracanvas scan ./terraform

# Shareable security score card
infracanvas score ./terraform

# Drift detection from terraform plan
infracanvas plan ./terraform --planfile plan.json
```

## Features

### Architecture Diagrams
Generates tiered VPC layouts with security groups, subnets, and regional services — automatically arranged by network topology.

```bash
infracanvas scan ./terraform --format html
```

### Security Scanning
10 built-in rules covering S3, IAM, RDS, EC2, KMS, and networking. Each finding includes severity, evidence, and remediation guidance.

```bash
infracanvas scan ./terraform --ci --severity high
# Exit code 0: no findings at or above threshold
# Exit code 1: findings found
# Exit code 2: parse error
```

### Drift Detection
Overlay `terraform plan` changes on the architecture diagram. See added, changed, and deleted resources with cost delta.

```bash
terraform plan -out=plan.bin && terraform show -json plan.bin > plan.json
infracanvas plan ./terraform --planfile plan.json
```

### Security Score Card
Letter-graded score across encryption, networking, IAM, and logging categories.

```bash
infracanvas score ./terraform --format json
```

## Security Rules

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

## CI/CD Integration

### GitHub Actions

```yaml
- name: InfraCanvas Security Scan
  run: |
    pip install infracanvas
    infracanvas scan ./terraform --ci --severity high
```

### Configuration File

Create `.infracanvas.yml` in your project root:

```yaml
severity_threshold: high
ignore_rules:
  - SEC-010   # tagging not enforced in dev
open_browser: false
output_dir: ./reports
```

## Install

```bash
# PyPI (recommended)
pip install infracanvas

# Homebrew
brew install infracanvas

# Binary
curl -sSL https://infracanvas.dev/install.sh | bash

# Docker
docker run --rm -v $(pwd):/workspace infracanvas/infracanvas scan /workspace
```

## Comparison

| Feature | InfraCanvas | Brainboard | Pluralith | Hava.io | Cloudcraft |
|---------|:-----------:|:----------:|:---------:|:-------:|:----------:|
| Free tier | Unlimited | Limited | Limited | No | Limited |
| Security scanning | 10 rules | No | No | No | No |
| Drift detection | Yes | No | Yes | No | No |
| Cost estimation | Yes | No | No | Yes | Yes |
| Offline / CLI | Yes | No | Yes | No | No |
| Score card | Yes | No | No | No | No |
| Open source | Yes | No | No | No | No |

## Requirements

- Python 3.12+
- Terraform files (`.tf`) in the target directory

## License

MIT
