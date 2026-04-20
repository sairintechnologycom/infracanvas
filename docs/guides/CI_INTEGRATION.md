# CI Integration

Block pull requests that introduce security findings at or above a severity threshold.

## The `--ci` flag

```bash
infracanvas scan ./terraform --ci --severity high
```

Behaviour:

- Writes JSON diagnostics to **stderr**; valid JSON only on **stdout**
- Does not open a browser
- Exits with:

  | Code | Meaning |
  |------|---------|
  | `0`  | No findings at or above `--severity` |
  | `1`  | Findings found — fail the build |
  | `2`  | Parse error — Terraform invalid |

## GitHub Actions

```yaml
# .github/workflows/infracanvas.yml
name: InfraCanvas
on:
  pull_request:
    paths:
      - 'terraform/**'

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install infracanvas
      - name: Security gate
        run: infracanvas scan ./terraform --ci --severity high
      - name: Upload report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: infracanvas-report
          path: infracanvas-report.html
```

## GitLab CI

```yaml
infracanvas:
  image: python:3.12-slim
  stage: test
  script:
    - pip install infracanvas
    - infracanvas scan ./terraform --ci --severity high
  artifacts:
    when: always
    paths:
      - infracanvas-report.html
    expire_in: 1 week
```

## Picking a threshold

| Threshold | When to use |
|-----------|-------------|
| `critical` | Minimum bar — only block on critical-severity rules |
| `high` | **Recommended** for most teams |
| `medium` | Strict — expect noise early |
| `info` | Blocks on anything, including missing tags |

## Ignoring rules in CI

Commit `.infracanvas.yml` to silence rules that don't apply:

```yaml
severity_threshold: high
ignore_rules:
  - SEC-010   # tag enforcement handled elsewhere
```

## Posting the report to a PR

Use the uploaded artifact URL, or render the Report Card into a PR comment:

```bash
infracanvas score ./terraform --json > score.json
# feed score.json to gh pr comment / your bot
```
