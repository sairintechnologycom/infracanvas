<!-- GSD:project-start source:PROJECT.md -->
## Project

**InfraCanvas**

InfraCanvas is a hybrid cloud intelligence platform that gives engineering and leadership teams a single visual pane of glass across AWS, Azure, and physical data centre infrastructure — showing configuration, security, network traffic paths, and cost in real time. It combines three products: Canvas (infrastructure diagrams + security), FlowMap (hybrid network topology + asymmetric routing detection), and CostLens (shared infrastructure cost allocation). CLI-first, open-core, with a SaaS dashboard for teams.

**Core Value:** One command gives you a complete, annotated picture of your hybrid infrastructure — security blind spots, network path asymmetry, drift, and shared cost — across AWS, Azure, and physical data centres, so you never have to manually correlate 5 different tools to answer "is our infrastructure in the state we think it is?"

### Constraints

- **Solo founder**: Must minimize operational complexity — no separate infrastructure to maintain
- **Cost**: SaaS hosting budget $10–104/mo until revenue (Railway/Fly.io + Vercel + Neon + R2 + Upstash + Clerk)
- **CLI stack**: Python 3.12+, pip-installable + PyInstaller standalone binary
- **DC Agent stack**: Go, single binary, cross-compiled Linux amd64 + macOS arm64
- **Frontend stack**: Next.js 14 App Router on Vercel
- **Backend stack**: FastAPI on Railway or Fly.io
- **Browser**: Modern browsers only (ES2020+), no IE support
- **Performance**: Parse 500 resources < 10s, FlowMap topology < 20s, HTML < 5MB
- **Security**: No cloud credentials stored. CLI scans are local-only. DC agent read-only, outbound-only.
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Languages
- Python 3.12 - CLI tool (`/Users/bhushan/Documents/Projects/Infracanvas/cli/`), Terraform parsing, graph building, security scanning, cost estimation
- TypeScript 5.8.3 - Web viewer frontend (`/Users/bhushan/Documents/Projects/Infracanvas/viewer/`)
- JavaScript/TSX - React components, UI logic
- HTML/CSS - Viewer interface, exported reports
## Runtime
- Node.js (via npm) - JavaScript runtime for viewer development and building
- Python 3.12 - CLI execution environment
- Docker - Container runtime (Python 3.12-slim base)
- npm - JavaScript dependencies, lockfile present (`package-lock.json`)
- pip/hatchling - Python dependencies via PyPI, managed through `pyproject.toml`
## Frameworks
- React 18.3.1 - UI framework for interactive diagrams (`/Users/bhushan/Documents/Projects/Infracanvas/viewer/`)
- Typer 0.12.3 - CLI framework for command-line interface (`/Users/bhushan/Documents/Projects/Infracanvas/cli/`)
- Pydantic 2.7.1 - Data validation and serialization (Python models)
- @xyflow/react 12.6.0 - Node-link diagram visualization for architecture graphs
- dagre 0.8.5 - Graph layout algorithm for automatic node positioning
- D3 (via @xyflow dependencies) - Lower-level visualization primitives
- Lucide React 0.511.0 - Icon library for UI components
- AWS React Icons 3.3.0 - AWS service icons for resource visualization
- Tailwind CSS 4.1.4 - Utility-first CSS framework
- @tailwindcss/vite 4.1.4 - Vite integration for Tailwind
- Zustand 5.0.5 - Lightweight client-side state management for filters, selected nodes
- python-hcl2 4.3.4 - Terraform HCL parsing
- NetworkX 3.3 - Graph data structure and algorithms (dependency graph building)
- PyYAML 6.0.1 - YAML parsing for config files
- Watchdog 4.0.1 - File system monitoring
- Vitest 4.1.4 - Test runner (JS/TS)
- @testing-library/react 16.3.2 - React component testing utilities
- @testing-library/jest-dom 6.9.1 - DOM matchers for assertions
- jsdom 29.0.2 - DOM implementation for tests
- pytest - Python test framework (implicit via project structure at `cli/tests/`)
- Vite 6.3.2 - Frontend build tool and dev server
- @vitejs/plugin-react 4.4.1 - React support in Vite
- vite-plugin-singlefile 2.0.3 - Bundles entire app into single HTML file
- TypeScript 5.8.3 - Type checking
- Babel - JS transformation via Vite dependencies
## Key Dependencies
- python-hcl2 4.3.4 - Core parsing of Terraform HCL files
- NetworkX 3.3 - Builds resource dependency graphs
- Pydantic 2.7.1 - Type-safe data models for graph structures
- React 18.3.1 - Interactive UI rendering
- @xyflow/react 12.6.0 - Diagram visualization engine
- Rich 13.7.1 - Terminal formatting and tables for CLI output
- PyYAML 6.0.1 - Configuration file parsing
- Typer 0.12.3 - CLI argument parsing and help
- Lucide React 0.511.0 - Consistent icon system
- Tailwind CSS 4.1.4 - Responsive styling
- Vite 6.3.2 - Fast build and HMR
- TypeScript 5.8.3 - Static type safety
- Vitest 4.1.4 - Fast unit testing
## Configuration
- Python target: Python 3.12+ (specified in `pyproject.toml`, line 10)
- Node.js: No explicit version file detected (`.nvmrc` not present)
- TypeScript config: `tsconfig.json` targets ES2020, strict mode enabled
- Frontend: `vite.config.ts` (`/Users/bhushan/Documents/Projects/Infracanvas/viewer/`)
- Backend: `pyproject.toml` with Hatchling build system
- Ruff config: Line length 100, Python 3.12 target
- MyPy: Strict mode for Python type checking
- Ruff linting: E, F, I, N, W, UP rules (line 49)
- MyPy: Strict type checking enabled (line 52-53)
- TypeScript: Strict mode, no unused locals/params, isolatedModules
## Platform Requirements
- Python 3.12+
- Node.js + npm (modern LTS recommended)
- macOS/Linux/Windows with shell support
- Docker container with Python 3.12-slim base (`Dockerfile`)
- Deployment: CLI distributed via PyPI, web viewer bundled as single HTML file
- Standalone binary support (Python package entry point: `infracanvas`)
- Modern browsers supporting ES2020+ (Vite target)
- JavaScript enabled for interactive diagrams
- No specific browser version requirements (no IE support)
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Naming Patterns
- Components: PascalCase (`FilterPanel.tsx`, `DiagramCanvas.tsx`, `FindingCard.tsx`)
- Utilities/Libraries: camelCase (`colors.ts`, `layout.ts`)
- Python modules: snake_case (`hcl.py`, `builder.py`, `models.py`)
- Test files: suffixed with `.test.ts` or `.test.tsx` (TypeScript) or `test_*.py` (Python)
- React components: PascalCase (exported default functions)
- Utility functions: camelCase (`buildFlowElements`, `getResourceColor`, `getHighestSeverity`)
- Private/helper functions: camelCase with underscore prefix for Python (`_strip_quotes`, `_clean_value`, `_parse_file`)
- Event handlers: camelCase starting with `on` or `handle` (`onNodeClick`, `handleFitView`)
- TypeScript: camelCase (`selectedNode`, `filterPanelOpen`, `resourceTypes`)
- Python: snake_case (`severity_filter`, `ignore_rules`, `resource_type`)
- Constants: UPPERCASE (`EDGE_STYLES`, `ZONE_COLORS`, `FIXTURES`)
- Type discriminant unions: lowercase literal strings (`'critical'`, `'high'`, `'unchanged'`, `'added'`)
- Interfaces: PascalCase with `I` prefix not used; prefer plain names (`Filters`, `StoreState`, `ResourceNode`)
- Type aliases: PascalCase (`Severity`, `DriftStatus`, `EdgeRelationship`, `ZoneType`)
- Pydantic models (Python): PascalCase (`ResourceNode`, `Finding`, `ResourceGraph`, `GraphSummary`)
- Enum values: StrEnum in Python, exported type literals in TypeScript
## Code Style
- No explicit formatter configured (ESLint/Prettier not found)
- Indentation: 2 spaces (TypeScript/React, Tailwind classes)
- Indentation: 4 spaces (Python)
- Line length: 100 characters (Python via Ruff in `pyproject.toml`)
- No semicolons at end of lines (TypeScript idiomatic style)
- **Python:** Ruff with rules `E F I N W UP` (pyflakes, isort, pep8-naming, pyupgrade)
- **Python mypy:** strict mode enabled; `hcl2` module has `ignore_missing_imports = true`
- **TypeScript:** TSConfig strict: `true`, enforces `noUnusedLocals`, `noUnusedParameters`, `noFallthroughCasesInSwitch`
## Import Organization
- No path aliases configured; relative imports used throughout
## Error Handling
- **TypeScript/React:** Type guards and conditional rendering (`if (!graph) return null;`)
- **Python CLI:** `typer.Exit(code=N)` for error exits with `console.print()` for error messages
- Try-catch with specific exception handling (`except (json.JSONDecodeError, ValueError) as exc`)
- Console logging via Rich library for formatted output
## Logging
- Status messages: `console.print("[cyan]Watching for changes...[/cyan]")`
- Errors: `console.print(f"[red]Error:[/red] {message}")`
- Tables: `Table()` for structured output
- Color tags: `[bold]`, `[red]`, `[green]`, `[yellow]`, `[blue]`
## Comments
- Python docstrings at function/class level using triple quotes (`"""docstring here."""`)
- Inline comments for non-obvious logic (e.g., "debounce" comment in watch handler)
- Module-level docstrings at top of files
- Test case descriptions in docstrings with test IDs (e.g., `B-001`, `E-002`, `E-007`)
- Not heavily used; React components have minimal documentation
- Type definitions in interfaces serve as implicit documentation
## Function Design
- `isNodeVisible()`: 18 lines
- `getResourceColor()`: 7 lines
- `getHighestSeverity()`: 7 lines
- Prefer destructuring in React hooks: `const { graph, filters } = useStore(...)`
- Use spread operator for config merging: `...node.style`
- Type annotations mandatory in Python, optional but used in TypeScript
- Default parameters used in Python (`allow_empty: bool = False`)
- Void for event handlers and state setters
- Explicit null returns for absence: `return null` (React)
- None returns in Python
- Union types for flexible returns: `Severity | null`
## Module Design
- **React components:** Default exports as functions (not classes)
- **Utilities:** Named exports from library files (`export const severityColors`, `export function getResourceColor()`)
- **Python:** Functions and classes defined at module level; no default exports
- Not used; direct imports from specific modules
## Type System
- Strict mode enabled; `unknown` used for unsafe casts before narrowing
- Type guards used for discriminated unions: `if (node.type === 'resource')`
- Generic types with constraints for store: `create<StoreState>((set) => ({...}))`
- Union types for enums: `type Severity = 'critical' | 'high' | 'medium' | 'info'`
- Type annotations required in strict mypy mode
- Pydantic `BaseModel` for runtime validation
- `StrEnum` for enumeration of string values
- `dict[str, object]` for untyped JSON-like data
- Ellipsis (`...`) for required fields in Typer: `planfile: Path = ...`
## State Management
- Store actions are methods that call `set()` to update state
- Selectors use arrow functions: `useStore(s => s.graph)`
- Immutable state updates with spread operator: `...s.filters`
- Filter arrays handled with `.includes()` and `.filter()`
- Pydantic models immutable by default
- Configuration loaded into dataclasses or Pydantic models
- No mutable global state; passed as parameters
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## Pattern Overview
- Separate CLI and viewer: Python backend analyzes infrastructure, JavaScript frontend visualizes results
- Clear separation of concerns: parsing, graph construction, security analysis, cost estimation, drift detection all independent
- Data-driven UI: frontend receives fully annotated `ResourceGraph` object injected at runtime
- Modular analysis pipeline: security rules, cost models, and drift detection can be extended independently
- Single-file HTML output: viewer is bundled as a self-contained HTML file for easy distribution
## Layers
- Purpose: Convert Terraform code into structured data
- Location: `cli/infracanvas/parser/`
- Contains: HCL parser, Terraform plan reader, reference resolver
- Depends on: `python-hcl2` library, external Terraform files
- Used by: Graph builder, plan analyzer
- Key files:
- Purpose: Build resource graph with dependencies and grouping
- Location: `cli/infracanvas/graph/`
- Contains: Node/edge creation, topology-aware layout
- Depends on: Parsed Terraform data, NetworkX
- Used by: Security engine, cost estimator, drift analyzer
- Key files:
- Purpose: Evaluate security findings, cost, and drift
- Location: `cli/infracanvas/security/`, `cli/infracanvas/cost/`, `cli/infracanvas/drift/`
- Contains: Rule engine, cost calculator, drift detector
- Depends on: Resource graph
- Used by: Main CLI
- Key modules:
- Purpose: Convert annotated graph to consumable formats
- Location: `cli/infracanvas/export/`
- Contains: HTML and JSON exporters, score card rendering
- Depends on: Resource graph, viewer template
- Used by: CLI commands
- Key files:
- Purpose: Interactive visualization and exploration
- Location: `viewer/src/`
- Contains: React components, Zustand state management, graph layout for rendering
- Depends on: Data injected via `window.__INFRACANVAS_DATA__`
- Used by: End users viewing HTML report
- Key components:
- Purpose: Command-line interface and orchestration
- Location: `cli/infracanvas/main.py`
- Contains: Typer app with commands: `scan`, `score`, `plan`, `export`
- Depends on: All analysis modules
- Commands:
## Data Flow
- Zustand store holds: `graph`, `selectedNode`, `filters`, `filterPanelOpen`
- `DiagramCanvas` watches graph and filters, updates node opacity
- Clicking node calls `setSelectedNode()` → triggers `DetailPanel` render
- Filter toggles update store → canvas re-renders with opacity changes
- `buildFlowElements()` converts `ResourceGraph` to ReactFlow format on every graph change
## Key Abstractions
- Purpose: Represents complete infrastructure snapshot with security/cost/drift metadata
- Location: `cli/infracanvas/graph/models.py`
- Example: `ResourceGraph(nodes=[...], edges=[...], summary=..., metadata=...)`
- Pattern: Immutable Pydantic model, passed through pipeline
- Serialized to JSON, embedded in HTML, rendered in UI
- Purpose: Single infrastructure resource with all annotations
- Location: `cli/infracanvas/graph/models.py`
- Contains: id, type, attributes, dependencies, findings[], cost, drift, position
- Example: `aws_security_group.web` with findings and cost estimate
- Patterns: Matched by ID to plan changes, filtered by type/severity, positioned by tier
- Purpose: Security issue with remediation guidance
- Location: `cli/infracanvas/graph/models.py`
- Fields: rule_id, severity, title, description, remediation, evidence
- Example: `SEC-001: S3 Bucket Publicly Accessible`
- Pattern: Multiple per node, aggregated in summary
- Purpose: Declarative security check
- Location: `cli/infracanvas/security/models.py` (loaded from YAML)
- Example: `sec-001.yaml`: "S3 acl == public-read → Critical"
- Pattern: Condition-based (attribute + operator + value), extensible
- Purpose: Raw parsed HCL structure
- Location: `cli/infracanvas/parser/hcl.py`
- Contains: resources[], variables[], locals[], outputs[], implicit_deps{}
- Pattern: Intermediate representation between HCL text and graph
## Entry Points
- Location: `cli/infracanvas/main.py`
- Triggers: `infracanvas scan|score|plan|export [options]`
- Responsibilities: Argument parsing, orchestrating pipeline, output handling, CI integration
- Location: `viewer/src/main.tsx`
- Triggers: Browser loads HTML file
- Responsibilities: Mounts React app, initializes store with injected data
- Location: `cli/infracanvas/export/html.py`
- Mechanism: Replaces `window.__INFRACANVAS_DATA__ = null;` in template with JSON
- Result: Self-contained HTML with graph data embedded
## Error Handling
- Parse errors: Exit code 2, print error to stderr, suggest --verbose
- Missing files: Exit code 1 or 2 depending on context
- CI mode: Separate stderr for diagnostics, only valid JSON to stdout
- HTML export fallback: If viewer template missing, export as JSON instead
- Watch mode: Catches re-scan errors, prints, continues watching
- `cli/infracanvas/main.py`: Try-except around `parse_directory()`, file checks before operations
- `cli/infracanvas/export/html.py`: Check template exists before reading
- `cli/infracanvas/drift/analyzer.py`: Handles missing resources gracefully (creates stubs)
## Cross-Cutting Concerns
- Regular output to stdout (console)
- CI mode diagnostics to stderr (_ci_console)
- Rich formatting for tables, colored text, progress
- Type checking on all data structures
- MyPy strict mode in CLI
- TypeScript strict mode in frontend
- Location: `cli/infracanvas/config.py`
- Customizable: severity_threshold, ignore_rules, output_dir, open_browser
- Pattern: Walks up filesystem, uses defaults if not found
- Condition-based pattern matching
- Extensible: Add new .yaml file to add rule
- Includes: S3, IAM, RDS, EC2, KMS, networking (10 rules total)
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, or `.github/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
