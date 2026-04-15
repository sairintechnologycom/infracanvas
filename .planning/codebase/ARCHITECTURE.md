# Architecture

**Analysis Date:** 2026-04-15

## Pattern Overview

**Overall:** Full-stack pipeline architecture with layered CLI backend (Python) and interactive frontend (React). The system follows a data-flow pattern: Parse → Analyze → Annotate → Render.

**Key Characteristics:**
- Separate CLI and viewer: Python backend analyzes infrastructure, JavaScript frontend visualizes results
- Clear separation of concerns: parsing, graph construction, security analysis, cost estimation, drift detection all independent
- Data-driven UI: frontend receives fully annotated `ResourceGraph` object injected at runtime
- Modular analysis pipeline: security rules, cost models, and drift detection can be extended independently
- Single-file HTML output: viewer is bundled as a self-contained HTML file for easy distribution

## Layers

**Input/Parser Layer:**
- Purpose: Convert Terraform code into structured data
- Location: `cli/infracanvas/parser/`
- Contains: HCL parser, Terraform plan reader, reference resolver
- Depends on: `python-hcl2` library, external Terraform files
- Used by: Graph builder, plan analyzer
- Key files:
  - `hcl.py`: Parses `.tf` files into `ParsedResource`, `ParsedBlock` objects
  - `plan.py`: Reads Terraform JSON plan and extracts `PlanChange` objects
  - `references.py`: Identifies implicit dependencies between resources
  - `state.py`: State file parsing (if needed)

**Graph Construction Layer:**
- Purpose: Build resource graph with dependencies and grouping
- Location: `cli/infracanvas/graph/`
- Contains: Node/edge creation, topology-aware layout
- Depends on: Parsed Terraform data, NetworkX
- Used by: Security engine, cost estimator, drift analyzer
- Key files:
  - `builder.py`: Creates `ResourceNode` and edges from parsed data, determines VPC/subnet groups
  - `models.py`: Pydantic models for `ResourceNode`, `ResourceGraph`, `Finding`, etc.
  - `layout.py`: Tier-based layout rules (Internet, Public, Private, Data, Regional)

**Analysis Layer:**
- Purpose: Evaluate security findings, cost, and drift
- Location: `cli/infracanvas/security/`, `cli/infracanvas/cost/`, `cli/infracanvas/drift/`
- Contains: Rule engine, cost calculator, drift detector
- Depends on: Resource graph
- Used by: Main CLI
- Key modules:
  - `security/engine.py`: Loads rules, evaluates against each resource node
  - `security/loader.py`: Loads YAML rule files from `rules/aws/`
  - `cost/estimator.py`: Estimates monthly costs per resource and applies cost delta
  - `drift/analyzer.py`: Maps plan changes to graph nodes, annotates `drift` and `drift_changes`
  - `security/scorer.py`: Builds score card with category breakdowns

**Export Layer:**
- Purpose: Convert annotated graph to consumable formats
- Location: `cli/infracanvas/export/`
- Contains: HTML and JSON exporters, score card rendering
- Depends on: Resource graph, viewer template
- Used by: CLI commands
- Key files:
  - `html.py`: Embeds graph JSON into `viewer_template.html`, injects into `window.__INFRACANVAS_DATA__`
  - `json.py`: Serializes `ResourceGraph` to JSON
  - `scorecard.py`: Renders score card HTML from score data

**Frontend (Viewer) Layer:**
- Purpose: Interactive visualization and exploration
- Location: `viewer/src/`
- Contains: React components, Zustand state management, graph layout for rendering
- Depends on: Data injected via `window.__INFRACANVAS_DATA__`
- Used by: End users viewing HTML report
- Key components:
  - `App.tsx`: Entry point, loads data from window or sample
  - `store.ts`: Zustand store manages graph, selected node, filters
  - `components/DiagramCanvas.tsx`: ReactFlow canvas with nodes and edges
  - `components/FilterPanel.tsx`: Severity, resource type, drift filters
  - `components/DetailPanel.tsx`: Shows selected node details
  - `lib/layout.ts`: Converts `ResourceGraph` to ReactFlow nodes/edges with tier positioning

**CLI Layer:**
- Purpose: Command-line interface and orchestration
- Location: `cli/infracanvas/main.py`
- Contains: Typer app with commands: `scan`, `score`, `plan`, `export`
- Depends on: All analysis modules
- Commands:
  - `scan`: Parse → Graph → Security → Export (HTML/JSON)
  - `score`: Parse → Graph → Security → Cost → Score Card
  - `plan`: Parse → Graph → Drift → Cost Delta → Export
  - `export`: Convert existing JSON report to HTML
  - `watch`: Re-scan on `.tf` file changes

## Data Flow

**Core Scan Pipeline (scan command):**

1. User runs: `infracanvas scan ./terraform`
2. `_run_scan()` called:
   - `parse_directory()` → `ParsedTerraform` (resources, dependencies, locals, variables)
   - `build_graph()` → `ResourceGraph` (nodes with VPC grouping, edges)
   - `evaluate_all()` → Security rules applied, `Finding[]` attached to each node
   - Findings filtered by severity/ignore rules
   - `GraphSummary` computed (score, finding counts)
3. Output:
   - Console: Rich summary table with findings
   - File: `infracanvas-report.html` or `.json`

**Drift Detection Pipeline (plan command):**

1. User runs: `infracanvas plan ./terraform --planfile plan.json`
2. Same scan pipeline + drift overlay:
   - `PlanReader.read()` → `PlanChange[]` (added, changed, deleted)
   - `DriftAnalyzer.apply()` → Updates `drift` and `drift_changes` on matching nodes
   - Creates stub nodes for "added" resources not in current code
   - `CostEstimator.delta()` → Calculates cost impact
3. Output: Diagram with drift status badges, cost delta display

**Score Card Pipeline (score command):**

1. User runs: `infracanvas score ./terraform`
2. Scan pipeline + analysis:
   - `CostEstimator.estimate()` → Cost per resource
   - `Scorer.build()` → Categories (encryption, networking, IAM, logging)
   - Per-category: findings counted, grade assigned (A-F)
3. Output: Terminal table, JSON, or HTML scorecard

**State Management (Frontend):**

- Zustand store holds: `graph`, `selectedNode`, `filters`, `filterPanelOpen`
- `DiagramCanvas` watches graph and filters, updates node opacity
- Clicking node calls `setSelectedNode()` → triggers `DetailPanel` render
- Filter toggles update store → canvas re-renders with opacity changes
- `buildFlowElements()` converts `ResourceGraph` to ReactFlow format on every graph change

## Key Abstractions

**ResourceGraph:**
- Purpose: Represents complete infrastructure snapshot with security/cost/drift metadata
- Location: `cli/infracanvas/graph/models.py`
- Example: `ResourceGraph(nodes=[...], edges=[...], summary=..., metadata=...)`
- Pattern: Immutable Pydantic model, passed through pipeline
- Serialized to JSON, embedded in HTML, rendered in UI

**ResourceNode:**
- Purpose: Single infrastructure resource with all annotations
- Location: `cli/infracanvas/graph/models.py`
- Contains: id, type, attributes, dependencies, findings[], cost, drift, position
- Example: `aws_security_group.web` with findings and cost estimate
- Patterns: Matched by ID to plan changes, filtered by type/severity, positioned by tier

**Finding:**
- Purpose: Security issue with remediation guidance
- Location: `cli/infracanvas/graph/models.py`
- Fields: rule_id, severity, title, description, remediation, evidence
- Example: `SEC-001: S3 Bucket Publicly Accessible`
- Pattern: Multiple per node, aggregated in summary

**SecurityRule:**
- Purpose: Declarative security check
- Location: `cli/infracanvas/security/models.py` (loaded from YAML)
- Example: `sec-001.yaml`: "S3 acl == public-read → Critical"
- Pattern: Condition-based (attribute + operator + value), extensible

**ParsedTerraform:**
- Purpose: Raw parsed HCL structure
- Location: `cli/infracanvas/parser/hcl.py`
- Contains: resources[], variables[], locals[], outputs[], implicit_deps{}
- Pattern: Intermediate representation between HCL text and graph

## Entry Points

**CLI Entry:**
- Location: `cli/infracanvas/main.py`
- Triggers: `infracanvas scan|score|plan|export [options]`
- Responsibilities: Argument parsing, orchestrating pipeline, output handling, CI integration

**Frontend Entry:**
- Location: `viewer/src/main.tsx`
- Triggers: Browser loads HTML file
- Responsibilities: Mounts React app, initializes store with injected data

**Backend-to-Frontend Bridge:**
- Location: `cli/infracanvas/export/html.py`
- Mechanism: Replaces `window.__INFRACANVAS_DATA__ = null;` in template with JSON
- Result: Self-contained HTML with graph data embedded

## Error Handling

**Strategy:** Fail-fast with informative messages

**Patterns:**
- Parse errors: Exit code 2, print error to stderr, suggest --verbose
- Missing files: Exit code 1 or 2 depending on context
- CI mode: Separate stderr for diagnostics, only valid JSON to stdout
- HTML export fallback: If viewer template missing, export as JSON instead
- Watch mode: Catches re-scan errors, prints, continues watching

**Key locations:**
- `cli/infracanvas/main.py`: Try-except around `parse_directory()`, file checks before operations
- `cli/infracanvas/export/html.py`: Check template exists before reading
- `cli/infracanvas/drift/analyzer.py`: Handles missing resources gracefully (creates stubs)

## Cross-Cutting Concerns

**Logging:** Uses `rich.console.Console` for terminal output
- Regular output to stdout (console)
- CI mode diagnostics to stderr (_ci_console)
- Rich formatting for tables, colored text, progress

**Validation:** Pydantic models enforce schema at graph creation and serialization
- Type checking on all data structures
- MyPy strict mode in CLI
- TypeScript strict mode in frontend

**Configuration:** `.infracanvas.yml` loaded from project or parent directories
- Location: `cli/infracanvas/config.py`
- Customizable: severity_threshold, ignore_rules, output_dir, open_browser
- Pattern: Walks up filesystem, uses defaults if not found

**Security Rules:** YAML-based, loaded dynamically from `cli/infracanvas/security/rules/aws/`
- Condition-based pattern matching
- Extensible: Add new .yaml file to add rule
- Includes: S3, IAM, RDS, EC2, KMS, networking (10 rules total)

---

*Architecture analysis: 2026-04-15*
