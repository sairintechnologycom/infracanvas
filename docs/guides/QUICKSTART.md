# Quickstart

Get from zero to your first InfraCanvas report in 5 minutes.

## Requirements

- Python 3.12+
- A directory containing Terraform `.tf` files

## 1. Install

```bash
pip install infracanvas
```

From source:

```bash
git clone https://github.com/infracanvas/infracanvas
cd infracanvas && pip install -e cli/
```

## 2. Scan your Terraform

```bash
infracanvas scan ./path/to/terraform
```

This produces `infracanvas-report.html` in the current directory and opens it in your default browser.

No Terraform handy? Try a bundled fixture:

```bash
infracanvas scan cli/tests/fixtures/insecure_setup
```

## 3. Explore the report

- **Diagram** — resources grouped by VPC / subnet, arranged by network topology
- **Severity badges** — Critical / High / Medium / Info on each node
- **Detail panel** — click a node for findings + remediation guidance
- **Filter panel** — toggle by severity or resource type

## 4. Next steps

- Grade the infrastructure: see [SCORING.md](./SCORING.md)
- Fail a PR on new findings: see [CI_INTEGRATION.md](./CI_INTEGRATION.md)
- Overlay drift from `terraform plan`:

  ```bash
  terraform plan -out=tfplan.binary
  terraform show -json tfplan.binary > plan.json
  infracanvas plan ./terraform --planfile plan.json
  ```

## Configuration (optional)

Drop `.infracanvas.yml` in your project root:

```yaml
severity_threshold: high
ignore_rules:
  - SEC-010
open_browser: false
output_dir: ./reports
```
