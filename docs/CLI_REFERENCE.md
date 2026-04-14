# CLI Reference

## Global Options

| Flag | Description |
|------|-------------|
| `--version`, `-V` | Show version and exit |
| `--help` | Show help and exit |

---

## `infracanvas scan`

Scan a Terraform directory and generate an annotated resource graph.

```bash
infracanvas scan <directory> [options]
```

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `directory` | Yes | Path to directory containing `.tf` files |

### Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--output`, `-o` | Path | auto | Output file path |
| `--format`, `-f` | String | `json` | Output format: `json`, `html` |
| `--quiet`, `-q` | Flag | false | JSON only to stdout (for piping) |
| `--severity`, `-s` | String | none | Filter findings by severity: `critical`, `high`, `medium`, `info` |
| `--ci` | Flag | false | CI mode: JSON to stdout, exit 1 on findings |
| `--watch`, `-w` | Flag | false | Re-scan on `.tf` file changes |
| `--ignore` | String[] | [] | Rule IDs to skip (repeatable) |

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success, no findings at threshold |
| 1 | Findings exist at or above severity threshold |
| 2 | Parse error, no `.tf` files, or invalid input |

### Examples

```bash
# Basic scan, JSON output
infracanvas scan ./terraform

# HTML diagram, auto-opens browser
infracanvas scan ./terraform --format html

# CI pipeline — fail on high+ findings
infracanvas scan ./terraform --ci --severity high

# Skip specific rules
infracanvas scan ./terraform --ignore SEC-010 --ignore SEC-009

# Watch mode — re-scan on file changes
infracanvas scan ./terraform --watch
```

---

## `infracanvas score`

Generate a security score card for a Terraform directory.

```bash
infracanvas score <directory> [options]
```

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `directory` | Yes | Path to directory containing `.tf` files |

### Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--format`, `-f` | String | `terminal` | Output format: `terminal`, `json`, `html` |
| `--output`, `-o` | Path | auto | Output file path |

### Examples

```bash
# Terminal score card
infracanvas score ./terraform

# JSON for programmatic use
infracanvas score ./terraform --format json

# HTML score card
infracanvas score ./terraform --format html --output scorecard.html
```

---

## `infracanvas plan`

Scan directory and overlay Terraform plan diff on the diagram.

```bash
infracanvas plan <directory> --planfile <plan.json> [options]
```

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `directory` | Yes | Path to directory containing `.tf` files |

### Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--planfile`, `-p` | Path | required | Terraform plan JSON file |
| `--output`, `-o` | Path | auto | Output file path |
| `--format`, `-f` | String | `html` | Output format: `html`, `json` |

### Examples

```bash
# Generate plan JSON first
terraform plan -out=plan.bin
terraform show -json plan.bin > plan.json

# Overlay drift on diagram
infracanvas plan ./terraform --planfile plan.json

# JSON output
infracanvas plan ./terraform --planfile plan.json --format json
```

---

## `infracanvas export`

Re-export a JSON report to HTML or formatted JSON.

```bash
infracanvas export <report.json> [options]
```

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `report` | Yes | Path to InfraCanvas JSON report file |

### Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--output`, `-o` | Path | auto | Output file path |
| `--format`, `-f` | String | `html` | Export format: `html`, `json` |

---

## Configuration File

InfraCanvas looks for `.infracanvas.yml` in the target directory and parent directories (up to home).

### Keys

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `severity_threshold` | String | `high` | CI exit threshold severity |
| `ignore_rules` | String[] | `[]` | Rule IDs to always skip |
| `output_dir` | String | `.` | Default output directory |
| `open_browser` | Bool | `true` | Auto-open HTML reports in browser |
| `provider` | String | `aws` | Default cloud provider |

### Example

```yaml
severity_threshold: high
ignore_rules:
  - SEC-010
open_browser: false
output_dir: ./reports
```
