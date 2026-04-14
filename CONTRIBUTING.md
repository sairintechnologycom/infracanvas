# Contributing

## Development Setup

```bash
# Clone the repo
git clone https://github.com/infracanvas/infracanvas.git
cd infracanvas

# CLI (Python)
cd cli
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e .
pip install pytest pytest-cov ruff

# Viewer (TypeScript)
cd ../viewer
npm install
npm run dev
```

## Running Tests

```bash
# CLI tests
cd cli && pytest --cov=infracanvas -q

# Viewer tests
cd viewer && npm test
```

## Adding a Security Rule

1. Create a YAML entry in `cli/infracanvas/security/rules/aws/` (or a new file for new resource types)

2. Follow the rule schema:
   ```yaml
   - id: SEC-0XX
     title: "Short descriptive title"
     severity: critical|high|medium|info
     resource_types:
       - aws_resource_type
     condition:
       attribute: "attribute_name"
       operator: "in|not_exists|equals|regex|exists"
       values: ["value1", "value2"]
     description: "What this rule checks and why it matters."
     remediation: "How to fix the issue."
   ```

3. Add test cases in `cli/tests/test_security.py`:
   - Positive test: resource that triggers the rule
   - Negative test: resource that passes

4. Run `pytest tests/test_security.py -v` to verify

5. Submit a PR — CI will validate rule format automatically

## Code Style

- Python: Ruff with `E, F, I, N, W, UP` rules, line length 100
- TypeScript: Standard Vite/React conventions
- Commit messages: imperative mood, concise

## Project Structure

```
infracanvas/
├── cli/                    # Python CLI package
│   ├── infracanvas/
│   │   ├── main.py         # CLI entry point (Typer)
│   │   ├── config.py       # .infracanvas.yml loader
│   │   ├── parser/         # HCL, state, plan parsing
│   │   ├── graph/          # Resource graph + models
│   │   ├── security/       # Rule engine + YAML rules
│   │   ├── cost/           # Cost estimation
│   │   ├── drift/          # Drift analysis
│   │   └── export/         # HTML, JSON, scorecard
│   └── tests/
├── viewer/                 # React diagram viewer
│   └── src/
│       ├── components/     # React components
│       ├── lib/            # Layout engine, colors
│       └── __tests__/
└── docs/
```
