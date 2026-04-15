# Testing Patterns

**Analysis Date:** 2026-04-15

## Test Framework

**TypeScript/React:**
- Runner: Vitest 4.1.4
- Config: `vite.config.ts` (not separate vitest.config)
- Assertion Library: Vitest built-in `expect`
- Testing Library: `@testing-library/react` 16.3.2, `@testing-library/jest-dom` 6.9.1
- Environment: jsdom
- Setup file: `src/__tests__/setup.ts`

**Python:**
- Runner: pytest (via pyproject.toml `testpaths = ["tests"]`)
- Assertion Library: pytest assertions (standard `assert`)
- Type checking: mypy in strict mode
- Coverage tool: .coverage file present (pytest-cov)

**Run Commands:**

TypeScript:
```bash
npm test                    # Run all tests once
npm run test:watch         # Watch mode
npx vitest run --coverage  # Coverage (inferred)
```

Python:
```bash
pytest                      # Run all tests
pytest --watch             # Watch mode (requires pytest-watch)
pytest --cov               # Coverage
```

## Test File Organization

**Location:**
- TypeScript: Co-located in `src/__tests__/` directory (separate from source tree)
  - `src/__tests__/store.test.ts`
  - `src/__tests__/types.test.ts`
  - `src/__tests__/colors.test.ts`
- Python: Separate `tests/` directory at project root
  - `tests/test_config.py`
  - `tests/test_graph.py`
  - `tests/test_parser.py`
  - `tests/test_cli.py`

**Naming:**
- TypeScript: `[name].test.ts` suffix
- Python: `test_[name].py` prefix

**Structure:**
```
viewer/
├── src/
│   ├── __tests__/
│   │   ├── setup.ts
│   │   ├── colors.test.ts
│   │   ├── store.test.ts
│   │   └── types.test.ts
│   ├── components/
│   ├── lib/
│   └── ...

cli/
├── tests/
│   ├── fixtures/
│   ├── test_config.py
│   ├── test_graph.py
│   └── ...
├── infracanvas/
└── ...
```

## Test Structure

**TypeScript Suite Organization:**
```typescript
import { describe, it, expect, beforeEach } from 'vitest';
import { useStore } from '../store';

describe('Store', () => {
  beforeEach(() => {
    useStore.setState({
      graph: null,
      selectedNode: null,
      filterPanelOpen: false,
      filters: { severities: [], resourceTypes: [], driftStatuses: [] },
    });
  });

  it('setGraph updates graph state', () => {
    useStore.getState().setGraph(mockGraph);
    expect(useStore.getState().graph).toBe(mockGraph);
  });

  it('toggleFilterPanel toggles state', () => {
    expect(useStore.getState().filterPanelOpen).toBe(false);
    useStore.getState().toggleFilterPanel();
    expect(useStore.getState().filterPanelOpen).toBe(true);
  });
});
```

**Python Suite Organization:**
```python
class TestBuildGraph:
    """B-001 through B-008: Graph builder tests."""

    def test_b001_correct_node_count(self):
        """B-001: Graph has correct node count after parsing simple_vpc fixture."""
        parsed = parse_directory(FIXTURES / "simple_vpc")
        graph = build_graph(parsed)
        assert len(graph.nodes) == 6

    def test_b002_edge_between_subnet_and_vpc(self):
        """B-002: Edge exists between subnet and vpc (implicit dependency)."""
        parsed = parse_directory(FIXTURES / "simple_vpc")
        graph = build_graph(parsed)
        edge_pairs = {(e["source"], e["target"]) for e in graph.edges}
        assert ("aws_subnet.public", "aws_vpc.main") in edge_pairs
```

**Patterns:**
- Setup: `beforeEach()` for TypeScript (Zustand state reset); pytest fixtures optional
- Teardown: Not heavily used; state cleaned in `beforeEach` or via function parameters
- Assertions: Direct `expect()` chains in TypeScript; `assert` statements in Python
- Test IDs in docstrings: `B-001`, `E-002` format for tracking requirements

## Mocking

**Framework:**
- TypeScript: Vitest built-in mocking (uses Vitest's `vi` utilities)
- Python: Not explicitly used in examined tests; pytest fixtures used instead

**Patterns for TypeScript:**
Zustand store mocking via `setState()`:
```typescript
beforeEach(() => {
  useStore.setState({
    graph: null,
    selectedNode: null,
    filterPanelOpen: false,
    filters: { severities: [], resourceTypes: [], driftStatuses: [] },
  });
});
```

**What to Mock:**
- Zustand store state in component tests
- Callbacks and event handlers for React components
- External dependencies (imports from libraries)

**What NOT to Mock:**
- Pure utility functions like `getResourceColor()`, `getHighestSeverity()` — test directly
- Type system / data structures — test real objects
- Pydantic model validation — test real models

## Fixtures and Factories

**Test Data (TypeScript):**
```typescript
const mockNode: ResourceNode = {
  id: 'aws_vpc.main',
  type: 'aws_vpc',
  name: 'main',
  provider: 'aws',
  module: '',
  region: 'us-east-1',
  group: '',
  attributes: { cidr_block: '10.0.0.0/16' },
  dependencies: [],
  findings: [],
  cost: { monthly_usd: 0, currency: 'USD', basis: '' },
  drift: 'unchanged',
  position: { x: 0, y: 0 },
};

const mockGraph: ResourceGraph = {
  version: '1.0',
  metadata: {
    scan_id: 'test-001',
    project: 'test-project',
    provider: 'aws',
    scanned_at: '2026-01-01T00:00:00Z',
    terraform_version: '1.7.0',
  },
  nodes: [mockNode],
  edges: [],
  summary: { ... },
};
```

**Test Data (Python):**
```python
FIXTURES = Path(__file__).parent / "fixtures"

# Usage
parsed = parse_directory(FIXTURES / "simple_vpc")
graph = build_graph(parsed)
```

**Location:**
- TypeScript: Fixtures defined inline in test files or in `src/__tests__/` as constants
- Python: Fixtures in `tests/fixtures/` directory (Terraform HCL files for parser testing)

## Coverage

**Requirements:** Not enforced; .coverage file present indicating some coverage tracking

**View Coverage:**
```bash
# Python
pytest --cov=infracanvas --cov-report=html

# TypeScript (if configured)
vitest run --coverage
```

## Test Types

**Unit Tests:**
- Scope: Individual functions and store mutations
- Approach: Pure functions tested directly (e.g., `getResourceColor`, `getHighestSeverity`)
- Zustand store mutations tested via `setState` and `getState`
- TypeScript: ~40-50 assertions per test file

**Integration Tests:**
- Scope: End-to-end data flow (parse → build → export)
- Approach: File I/O with fixture Terraform files
- Python: `test_integration.py` exists
- Example: Parse directory → build graph → export JSON → validate schema

**E2E Tests:**
- Framework: Not found
- CLI tested via `test_cli.py` which invokes actual `_run_scan()` function
- HTML export tested indirectly through integration tests

## Common Patterns

**Async Testing (TypeScript):**
Not heavily used; Zustand operations are synchronous. React Testing Library helpers could be used:
```typescript
// Pattern (not yet in codebase)
await waitFor(() => {
  expect(useStore.getState().graph).not.toBeNull();
});
```

**Error Testing (Python):**
```python
def test_invalid_yaml_returns_default(self, tmp_path):
    (tmp_path / ".infracanvas.yml").write_text(":::invalid yaml{{")
    config = load_config(tmp_path)
    assert config == InfraCanvasConfig()

def test_empty_directory(self, tmp_path):
    """E-008: Empty directory produces graph with 0 nodes and no error."""
    parsed = parse_directory(tmp_path)
    graph = build_graph(parsed)
    assert len(graph.nodes) == 0
    assert len(graph.edges) == 0
```

**Type Validation Testing (TypeScript):**
```typescript
it('E-010: sample-data matches ResourceGraph shape', () => {
  const graph: ResourceGraph = sampleData;
  expect(graph.version).toBeDefined();
  expect(graph.metadata).toBeDefined();
  expect(graph.nodes).toBeDefined();
  
  for (const node of sampleData.nodes) {
    const n: ResourceNode = node;
    expect(n.id).toBeDefined();
    expect(n.type).toBeDefined();
  }
});
```

**Property-based Testing:**
```typescript
it('multiple severity filters accumulate', () => {
  useStore.getState().toggleSeverityFilter('critical');
  useStore.getState().toggleSeverityFilter('high');
  expect(useStore.getState().filters.severities).toEqual(['critical', 'high']);
});
```

## Setup Files

**TypeScript (`src/__tests__/setup.ts`):**
```typescript
import '@testing-library/jest-dom';
```

Configures DOM matchers for jest-dom library.

**Vitest Configuration (in `vite.config.ts`):**
```typescript
test: {
  environment: 'jsdom',
  globals: true,
  setupFiles: ['./src/__tests__/setup.ts'],
}
```

**Python (`pyproject.toml`):**
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

## Test Execution

**TypeScript:**
- Tests use `vitest run` for single run
- Watch mode via `vitest` (no `run` flag)
- Global test functions available due to `globals: true` in config

**Python:**
- Tests discovered via `pytest` with standard naming
- Fixtures available via pytest's built-in fixture system
- tmp_path fixture used for temporary directories
- Classes used for test organization (not required but common pattern)

## Quality Standards

**Naming Convention for Tests:**
- Descriptive test names: `test_setGraph updates graph state`
- Test IDs in docstrings linking to requirements: `E-001`, `B-005`, etc.
- Python test class names follow pattern: `Test[Component]`

**Assertion Style:**
- Single assertion per test where possible
- Related assertions grouped in single test when testing behavior
- `expect().toBe()`, `expect().toEqual()`, `expect().toContain()` used frequently
- `assert len(list) == N` for quantity assertions

---

*Testing analysis: 2026-04-15*
