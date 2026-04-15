# Codebase Structure

**Analysis Date:** 2026-04-15

## Directory Layout

```
infracanvas/
├── cli/                           # Python backend: parsing, analysis, export
│   ├── infracanvas/               # Main package
│   │   ├── __init__.py
│   │   ├── main.py               # Typer CLI app with 5 commands
│   │   ├── config.py             # .infracanvas.yml loading
│   │   ├── parser/               # Input parsing
│   │   │   ├── hcl.py           # Parse .tf files
│   │   │   ├── plan.py          # Parse terraform plan JSON
│   │   │   ├── references.py    # Extract implicit dependencies
│   │   │   └── state.py         # Terraform state parsing
│   │   ├── graph/                # Resource graph construction
│   │   │   ├── builder.py       # Build graph from parsed HCL
│   │   │   ├── models.py        # Pydantic models for all data structures
│   │   │   └── layout.py        # Tier-based layout rules
│   │   ├── security/             # Security scanning
│   │   │   ├── engine.py        # Rule evaluation engine
│   │   │   ├── loader.py        # Load YAML rules
│   │   │   ├── models.py        # Rule and condition models
│   │   │   ├── scorer.py        # Build security score card
│   │   │   └── rules/           # Rule definitions
│   │   │       └── aws/         # AWS resource rules
│   │   │           ├── s3.yaml
│   │   │           ├── database.yaml
│   │   │           ├── compute.yaml
│   │   │           ├── networking.yaml
│   │   │           └── iam.yaml
│   │   ├── cost/                 # Cost estimation
│   │   │   └── estimator.py     # Monthly cost calculation
│   │   ├── drift/                # Drift detection
│   │   │   └── analyzer.py      # Apply terraform plan to graph
│   │   └── export/               # Output generation
│   │       ├── html.py          # HTML export (embeds in viewer)
│   │       ├── json.py          # JSON export
│   │       └── scorecard.py      # Score card HTML rendering
│   ├── pyproject.toml            # Project metadata, dependencies
│   ├── tests/                    # Test suite
│   │   ├── fixtures/            # Test Terraform files
│   │   │   ├── clean_infra/
│   │   │   ├── large/
│   │   │   ├── multi_module/
│   │   │   ├── malformed/
│   │   │   ├── single_resource/
│   │   │   ├── demo_infra/
│   │   │   ├── insecure_setup/
│   │   │   └── empty_blocks/
│   │   └── test_*.py            # Unit and integration tests
│   └── .venv/                   # Python virtual environment
│
├── viewer/                        # React frontend: visualization
│   ├── src/
│   │   ├── main.tsx             # React entry point
│   │   ├── App.tsx              # Root component, loads injected data
│   │   ├── store.ts             # Zustand store (graph, filters, selection)
│   │   ├── types.ts             # TypeScript interfaces (matching backend models)
│   │   ├── sample-data.ts       # Demo graph for development
│   │   ├── components/          # React UI components
│   │   │   ├── DiagramCanvas.tsx      # ReactFlow graph visualization
│   │   │   ├── FilterPanel.tsx        # Sidebar: severity/type/drift filters
│   │   │   ├── DetailPanel.tsx        # Right sidebar: node details & findings
│   │   │   ├── SummaryBar.tsx         # Top bar: score, resource count, findings
│   │   │   ├── ResourceNode.tsx       # Node component (rendered in canvas)
│   │   │   ├── GroupNode.tsx          # Group/VPC node (container node)
│   │   │   ├── FindingCard.tsx        # Finding detail card
│   │   │   └── icons/
│   │   │       ├── ResourceIcon.tsx   # Generic resource icon renderer
│   │   │       └── AwsIcon.tsx        # AWS service icon mapper
│   │   ├── lib/
│   │   │   ├── layout.ts        # Converts ResourceGraph to ReactFlow nodes/edges
│   │   │   └── colors.ts        # Color scheme (severity, resource types, zones)
│   │   ├── __tests__/           # Vitest test suite
│   │   │   ├── setup.ts         # Test setup
│   │   │   ├── store.test.ts
│   │   │   ├── types.test.ts
│   │   │   └── colors.test.ts
│   │   └── vite-env.d.ts        # Vite type declarations
│   ├── dist/                    # Built output (single HTML file)
│   ├── index.html               # Vite template
│   ├── package.json             # Node dependencies
│   ├── tsconfig.json            # TypeScript config
│   ├── vite.config.ts           # Vite build config (produces single-file output)
│   └── node_modules/
│
├── docs/                         # Documentation
├── .github/                      # GitHub workflows
├── .planning/                    # GSD planning documents
│   └── codebase/                # This directory
├── build.sh                     # Build script (compiles viewer, builds CLI)
├── install.sh                   # Installation script
├── pyproject.toml              # Root project config (if shared)
├── Dockerfile                  # Docker build for CLI
├── README.md                   # User-facing documentation
└── Formula/                    # Homebrew formula
```

## Directory Purposes

**cli/infracanvas/:**
- Purpose: Main application logic
- Contains: Parsing, analysis, export modules
- Key files: `main.py` (entry), `config.py` (configuration)

**cli/infracanvas/parser/:**
- Purpose: Convert Terraform code to structured data
- Contains: HCL parser, plan reader, reference resolver
- Files map to input types: `hcl.py`, `plan.py`, `state.py`, `references.py`

**cli/infracanvas/graph/:**
- Purpose: Build and model infrastructure graphs
- Contains: Graph construction, data models, layout rules
- Core: `models.py` defines all Pydantic structures, `builder.py` constructs graphs

**cli/infracanvas/security/:**
- Purpose: Security scanning and scoring
- Contains: Rule engine, rule definitions, scorer
- Rules: YAML files in `rules/aws/` (extensible by provider)

**cli/infracanvas/cost/:**
- Purpose: Cost estimation
- Contains: Cost calculator for resources and delta computation

**cli/infracanvas/drift/:**
- Purpose: Terraform plan drift detection
- Contains: Analyzer that maps plan changes to graph nodes

**cli/infracanvas/export/:**
- Purpose: Generate output formats
- Contains: HTML (with embedded viewer), JSON, scorecard renderers
- Critical: `html.py` embeds graph JSON for frontend consumption

**viewer/src/:**
- Purpose: React frontend
- Contains: UI components, state management, layout logic

**viewer/src/components/:**
- Purpose: React components
- Organization: By concern (Canvas, Panels, Cards, Icons)
- Pattern: Functional components with hooks, memoized where needed

**viewer/src/lib/:**
- Purpose: Utilities
- `layout.ts`: Graph to ReactFlow format conversion (called on every graph change)
- `colors.ts`: Severity and resource type color mappings

**cli/tests/ and viewer/src/__tests__/:**
- Purpose: Test coverage
- Backend: pytest with fixtures in `fixtures/`
- Frontend: Vitest with jsdom

## Key File Locations

**Entry Points:**
- CLI: `cli/infracanvas/main.py` - Typer app, main() function, commands
- Frontend: `viewer/src/main.tsx` - ReactDOM.createRoot()
- HTML: `cli/infracanvas/export/html.py` - Template injection point

**Configuration:**
- `.infracanvas.yml` - Project configuration (loaded by `cli/infracanvas/config.py`)
- `viewer/tsconfig.json` - TypeScript settings
- `cli/pyproject.toml` - Python package metadata, dependencies
- `viewer/vite.config.ts` - Vite build config

**Core Logic:**
- Parser: `cli/infracanvas/parser/hcl.py` - Main parsing entry
- Graph builder: `cli/infracanvas/graph/builder.py` - Creates ResourceGraph
- Security: `cli/infracanvas/security/engine.py` - Rule evaluation
- Export: `cli/infracanvas/export/html.py` - Viewer embedding

**Testing:**
- Backend fixtures: `cli/tests/fixtures/` - Terraform test files
- Frontend tests: `viewer/src/__tests__/` - Vitest files

## Naming Conventions

**Files:**
- Python modules: `snake_case.py` (e.g., `hcl.py`, `security_engine.py`)
- React components: `PascalCase.tsx` (e.g., `DiagramCanvas.tsx`, `FilterPanel.tsx`)
- Test files: `test_*.py` (backend), `*.test.ts` (frontend)
- Config: `.infracanvas.yml` (dot-prefixed YAML)

**Directories:**
- Functional modules: lowercase (e.g., `parser`, `graph`, `security`)
- React components: `components/` (plural)
- Tests: `tests/` or `__tests__/` (convention by language)
- Utils: `lib/` (frontend), utilities inline in CLI modules

**Python Classes:**
- Data models: `PascalCase` with `BaseModel` or `@dataclass` (e.g., `ResourceGraph`, `Finding`)
- Functions: `snake_case` (e.g., `parse_directory()`, `evaluate_all()`)

**TypeScript Types:**
- Interfaces: `PascalCase` with `interface` keyword (e.g., `ResourceGraph`, `DriftStatus`)
- Enum-like: Union types or enums (e.g., `type Severity = 'critical' | 'high' | ...`)
- Functions: `camelCase` (e.g., `buildFlowElements()`, `isNodeVisible()`)

## Where to Add New Code

**New Security Rule:**
- Add file: `cli/infracanvas/security/rules/aws/{category}.yaml`
- Format: YAML with `id`, `title`, `severity`, `resource_types`, `condition`, `remediation`
- Loaded automatically by `loader.py` via `rglob("*.yaml")`

**New CLI Command:**
- Edit: `cli/infracanvas/main.py`
- Pattern: Add `@app.command()` function with Typer annotations
- Name: Follows Typer conventions (function name is command name)

**New Analysis Module:**
- Create: `cli/infracanvas/{category}/{module}.py`
- Pattern: Takes ResourceGraph, returns modified ResourceGraph
- Integration: Call from `_run_scan()` or specific command in `main.py`

**New React Component:**
- Create: `viewer/src/components/{ComponentName}.tsx`
- Pattern: Functional component with hooks, use `useStore` for state
- Export: Named export, memoize if expensive (e.g., `export const Component = memo(...)`)

**New Frontend Utility:**
- Create: `viewer/src/lib/{utility}.ts`
- Pattern: Pure functions taking types from `types.ts`
- Test: Add `__tests__/{utility}.test.ts`

**New Test Fixture (Terraform):**
- Create: `cli/tests/fixtures/{scenario}/main.tf`
- Pattern: Minimal Terraform code to exercise specific feature
- Used by: Integration tests in `cli/tests/test_*.py`

## Special Directories

**cli/tests/fixtures/:**
- Purpose: Test Terraform files
- Generated: No (manually created)
- Committed: Yes
- Contents: Directories with `*.tf` files for different test scenarios

**viewer/dist/:**
- Purpose: Built viewer output
- Generated: Yes (by `npm run build`)
- Committed: No
- Contents: Single `index.html` (bundled with all CSS/JS)

**cli/.venv/:**
- Purpose: Python virtual environment
- Generated: Yes (by `python -m venv .venv`)
- Committed: No
- Contents: Python dependencies and interpreter

**viewer/node_modules/:**
- Purpose: JavaScript dependencies
- Generated: Yes (by `npm install`)
- Committed: No
- Contents: All npm packages

**cli/infracanvas/security/rules/:**
- Purpose: Rule definitions
- Generated: No (manually edited)
- Committed: Yes
- Contents: YAML files organizing rules by AWS service
- Extension point: Add new .yaml files to add rules without code changes

## Import Patterns

**Backend (Python):**
- Relative imports within package: `from infracanvas.parser.hcl import parse_directory`
- Type hints: `from __future__ import annotations` for forward references
- Models: All Pydantic structures imported from `infracanvas.graph.models`
- Rules: Loaded dynamically from YAML, not imported

**Frontend (TypeScript):**
- React imports: `import { useState } from 'react'`
- Component imports: `import { ComponentName } from './components/ComponentName'`
- Store: `import { useStore } from './store'`
- Types: `import type { TypeName } from './types'`
- Utilities: `import { utilityFunction } from './lib/layout'`

## Data Flow Through Codebase

1. User runs CLI command
2. `main.py` validates arguments, loads config
3. `parser/hcl.py` reads `.tf` files → `ParsedTerraform`
4. `graph/builder.py` converts → `ResourceGraph`
5. `security/engine.py` evaluates rules → `Finding[]` on each node
6. `cost/estimator.py` adds cost estimates
7. Optional: `drift/analyzer.py` applies plan changes
8. Optional: `security/scorer.py` builds score card
9. `export/html.py` or `export/json.py` outputs
10. HTML export embeds JSON in template, served to browser
11. Frontend reads `window.__INFRACANVAS_DATA__`
12. React renders graph with filters and detail panels

---

*Structure analysis: 2026-04-15*
