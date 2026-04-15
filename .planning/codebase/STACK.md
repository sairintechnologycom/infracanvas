# Technology Stack

**Analysis Date:** 2026-04-15

## Languages

**Primary:**
- Python 3.12 - CLI tool (`/Users/bhushan/Documents/Projects/Infracanvas/cli/`), Terraform parsing, graph building, security scanning, cost estimation
- TypeScript 5.8.3 - Web viewer frontend (`/Users/bhushan/Documents/Projects/Infracanvas/viewer/`)
- JavaScript/TSX - React components, UI logic

**Secondary:**
- HTML/CSS - Viewer interface, exported reports

## Runtime

**Environment:**
- Node.js (via npm) - JavaScript runtime for viewer development and building
- Python 3.12 - CLI execution environment
- Docker - Container runtime (Python 3.12-slim base)

**Package Manager:**
- npm - JavaScript dependencies, lockfile present (`package-lock.json`)
- pip/hatchling - Python dependencies via PyPI, managed through `pyproject.toml`

## Frameworks

**Core:**
- React 18.3.1 - UI framework for interactive diagrams (`/Users/bhushan/Documents/Projects/Infracanvas/viewer/`)
- Typer 0.12.3 - CLI framework for command-line interface (`/Users/bhushan/Documents/Projects/Infracanvas/cli/`)
- Pydantic 2.7.1 - Data validation and serialization (Python models)

**Visualization:**
- @xyflow/react 12.6.0 - Node-link diagram visualization for architecture graphs
- dagre 0.8.5 - Graph layout algorithm for automatic node positioning
- D3 (via @xyflow dependencies) - Lower-level visualization primitives
- Lucide React 0.511.0 - Icon library for UI components
- AWS React Icons 3.3.0 - AWS service icons for resource visualization

**UI/Styling:**
- Tailwind CSS 4.1.4 - Utility-first CSS framework
- @tailwindcss/vite 4.1.4 - Vite integration for Tailwind

**State Management:**
- Zustand 5.0.5 - Lightweight client-side state management for filters, selected nodes

**Parser/Transform:**
- python-hcl2 4.3.4 - Terraform HCL parsing
- NetworkX 3.3 - Graph data structure and algorithms (dependency graph building)
- PyYAML 6.0.1 - YAML parsing for config files
- Watchdog 4.0.1 - File system monitoring

**Testing:**
- Vitest 4.1.4 - Test runner (JS/TS)
- @testing-library/react 16.3.2 - React component testing utilities
- @testing-library/jest-dom 6.9.1 - DOM matchers for assertions
- jsdom 29.0.2 - DOM implementation for tests
- pytest - Python test framework (implicit via project structure at `cli/tests/`)

**Build/Dev:**
- Vite 6.3.2 - Frontend build tool and dev server
- @vitejs/plugin-react 4.4.1 - React support in Vite
- vite-plugin-singlefile 2.0.3 - Bundles entire app into single HTML file
- TypeScript 5.8.3 - Type checking
- Babel - JS transformation via Vite dependencies

## Key Dependencies

**Critical:**
- python-hcl2 4.3.4 - Core parsing of Terraform HCL files
- NetworkX 3.3 - Builds resource dependency graphs
- Pydantic 2.7.1 - Type-safe data models for graph structures
- React 18.3.1 - Interactive UI rendering
- @xyflow/react 12.6.0 - Diagram visualization engine

**Infrastructure:**
- Rich 13.7.1 - Terminal formatting and tables for CLI output
- PyYAML 6.0.1 - Configuration file parsing
- Typer 0.12.3 - CLI argument parsing and help
- Lucide React 0.511.0 - Consistent icon system
- Tailwind CSS 4.1.4 - Responsive styling

**Development:**
- Vite 6.3.2 - Fast build and HMR
- TypeScript 5.8.3 - Static type safety
- Vitest 4.1.4 - Fast unit testing

## Configuration

**Environment:**
- Python target: Python 3.12+ (specified in `pyproject.toml`, line 10)
- Node.js: No explicit version file detected (`.nvmrc` not present)
- TypeScript config: `tsconfig.json` targets ES2020, strict mode enabled

**Build:**
- Frontend: `vite.config.ts` (`/Users/bhushan/Documents/Projects/Infracanvas/viewer/`)
  - Single-file HTML build (via vite-plugin-singlefile)
  - Built viewer template embedded in CLI
  - Assets inlined for portability
- Backend: `pyproject.toml` with Hatchling build system
- Ruff config: Line length 100, Python 3.12 target
- MyPy: Strict mode for Python type checking

**Code Quality:**
- Ruff linting: E, F, I, N, W, UP rules (line 49)
- MyPy: Strict type checking enabled (line 52-53)
- TypeScript: Strict mode, no unused locals/params, isolatedModules

## Platform Requirements

**Development:**
- Python 3.12+
- Node.js + npm (modern LTS recommended)
- macOS/Linux/Windows with shell support

**Production:**
- Docker container with Python 3.12-slim base (`Dockerfile`)
- Deployment: CLI distributed via PyPI, web viewer bundled as single HTML file
- Standalone binary support (Python package entry point: `infracanvas`)

**Browser:**
- Modern browsers supporting ES2020+ (Vite target)
- JavaScript enabled for interactive diagrams
- No specific browser version requirements (no IE support)

---

*Stack analysis: 2026-04-15*
