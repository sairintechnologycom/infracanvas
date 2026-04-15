# Coding Conventions

**Analysis Date:** 2026-04-15

## Naming Patterns

**Files:**
- Components: PascalCase (`FilterPanel.tsx`, `DiagramCanvas.tsx`, `FindingCard.tsx`)
- Utilities/Libraries: camelCase (`colors.ts`, `layout.ts`)
- Python modules: snake_case (`hcl.py`, `builder.py`, `models.py`)
- Test files: suffixed with `.test.ts` or `.test.tsx` (TypeScript) or `test_*.py` (Python)

**Functions:**
- React components: PascalCase (exported default functions)
- Utility functions: camelCase (`buildFlowElements`, `getResourceColor`, `getHighestSeverity`)
- Private/helper functions: camelCase with underscore prefix for Python (`_strip_quotes`, `_clean_value`, `_parse_file`)
- Event handlers: camelCase starting with `on` or `handle` (`onNodeClick`, `handleFitView`)

**Variables:**
- TypeScript: camelCase (`selectedNode`, `filterPanelOpen`, `resourceTypes`)
- Python: snake_case (`severity_filter`, `ignore_rules`, `resource_type`)
- Constants: UPPERCASE (`EDGE_STYLES`, `ZONE_COLORS`, `FIXTURES`)
- Type discriminant unions: lowercase literal strings (`'critical'`, `'high'`, `'unchanged'`, `'added'`)

**Types:**
- Interfaces: PascalCase with `I` prefix not used; prefer plain names (`Filters`, `StoreState`, `ResourceNode`)
- Type aliases: PascalCase (`Severity`, `DriftStatus`, `EdgeRelationship`, `ZoneType`)
- Pydantic models (Python): PascalCase (`ResourceNode`, `Finding`, `ResourceGraph`, `GraphSummary`)
- Enum values: StrEnum in Python, exported type literals in TypeScript

## Code Style

**Formatting:**
- No explicit formatter configured (ESLint/Prettier not found)
- Indentation: 2 spaces (TypeScript/React, Tailwind classes)
- Indentation: 4 spaces (Python)
- Line length: 100 characters (Python via Ruff in `pyproject.toml`)
- No semicolons at end of lines (TypeScript idiomatic style)

**Linting:**
- **Python:** Ruff with rules `E F I N W UP` (pyflakes, isort, pep8-naming, pyupgrade)
- **Python mypy:** strict mode enabled; `hcl2` module has `ignore_missing_imports = true`
- **TypeScript:** TSConfig strict: `true`, enforces `noUnusedLocals`, `noUnusedParameters`, `noFallthroughCasesInSwitch`

## Import Organization

**Order:**
1. External third-party libraries (`react`, `zustand`, `@xyflow/react`, `lucide-react`)
2. Internal app code from parent directories (`../store`, `../types`, `../lib/colors`)
3. Type imports using `type` keyword where applicable

**Path Aliases:**
- No path aliases configured; relative imports used throughout

**Pattern:**
```typescript
// TypeScript example (DiagramCanvas.tsx)
import { useCallback, useEffect, useMemo } from 'react';
import { ReactFlow, Background, Controls, ... } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { ResourceNodeMemo } from './ResourceNode';
import { buildFlowElements } from '../lib/layout';
import { useStore } from '../store';
import type { ResourceNode } from '../types';
```

```python
# Python example (main.py)
from __future__ import annotations
from pathlib import Path
from typing import Annotated
import typer
from rich.console import Console
from infracanvas.config import InfraCanvasConfig, load_config
```

## Error Handling

**Patterns:**
- **TypeScript/React:** Type guards and conditional rendering (`if (!graph) return null;`)
- **Python CLI:** `typer.Exit(code=N)` for error exits with `console.print()` for error messages
- Try-catch with specific exception handling (`except (json.JSONDecodeError, ValueError) as exc`)
- Console logging via Rich library for formatted output

**Severity mapping in Python:**
```python
severity_styles = {
    "critical": "red",
    "high": "bright_red",
    "medium": "yellow",
    "info": "blue",
}
```

## Logging

**Framework:** Rich library (`console = Console()`)

**Patterns:**
- Status messages: `console.print("[cyan]Watching for changes...[/cyan]")`
- Errors: `console.print(f"[red]Error:[/red] {message}")`
- Tables: `Table()` for structured output
- Color tags: `[bold]`, `[red]`, `[green]`, `[yellow]`, `[blue]`

## Comments

**When to Comment:**
- Python docstrings at function/class level using triple quotes (`"""docstring here."""`)
- Inline comments for non-obvious logic (e.g., "debounce" comment in watch handler)
- Module-level docstrings at top of files
- Test case descriptions in docstrings with test IDs (e.g., `B-001`, `E-002`, `E-007`)

**JSDoc/TSDoc:**
- Not heavily used; React components have minimal documentation
- Type definitions in interfaces serve as implicit documentation

**Example from Python:**
```python
def _strip_quotes(value: str) -> str:
    """Strip surrounding double quotes that python-hcl2 adds to keys/values."""
    if isinstance(value, str) and len(value) >= 2 and value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    return value
```

## Function Design

**Size:** Functions kept short and focused, 20-50 lines typical range
- `isNodeVisible()`: 18 lines
- `getResourceColor()`: 7 lines
- `getHighestSeverity()`: 7 lines

**Parameters:**
- Prefer destructuring in React hooks: `const { graph, filters } = useStore(...)`
- Use spread operator for config merging: `...node.style`
- Type annotations mandatory in Python, optional but used in TypeScript
- Default parameters used in Python (`allow_empty: bool = False`)

**Return Values:**
- Void for event handlers and state setters
- Explicit null returns for absence: `return null` (React)
- None returns in Python
- Union types for flexible returns: `Severity | null`

## Module Design

**Exports:**
- **React components:** Default exports as functions (not classes)
- **Utilities:** Named exports from library files (`export const severityColors`, `export function getResourceColor()`)
- **Python:** Functions and classes defined at module level; no default exports

**Barrel Files:**
- Not used; direct imports from specific modules

**Example structure:**
```typescript
// colors.ts - multiple named exports
export const severityColors: Record<Severity | 'clean', string> = { ... };
export function getResourceColor(resourceType: string): string { ... };
export function getHighestSeverity(findings: { severity: Severity }[]): Severity | null { ... };
```

## Type System

**TypeScript:**
- Strict mode enabled; `unknown` used for unsafe casts before narrowing
- Type guards used for discriminated unions: `if (node.type === 'resource')`
- Generic types with constraints for store: `create<StoreState>((set) => ({...}))`
- Union types for enums: `type Severity = 'critical' | 'high' | 'medium' | 'info'`

**Python:**
- Type annotations required in strict mypy mode
- Pydantic `BaseModel` for runtime validation
- `StrEnum` for enumeration of string values
- `dict[str, object]` for untyped JSON-like data
- Ellipsis (`...`) for required fields in Typer: `planfile: Path = ...`

## State Management

**React/Zustand:**
- Store actions are methods that call `set()` to update state
- Selectors use arrow functions: `useStore(s => s.graph)`
- Immutable state updates with spread operator: `...s.filters`
- Filter arrays handled with `.includes()` and `.filter()`

**Python:**
- Pydantic models immutable by default
- Configuration loaded into dataclasses or Pydantic models
- No mutable global state; passed as parameters

---

*Convention analysis: 2026-04-15*
