# Phase 5.1 — Deferred Items

Pre-existing issues discovered during plan execution but deliberately out of scope for the current task. Logged here so they are not lost.

## Out-of-Scope Failures Observed During 05.1-04

### Pre-existing failing test — `applies NEW badge for added drift`

- **File:** `viewer/src/__tests__/ResourceNode.test.tsx` (line 93–97)
- **Failure:** `screen.getByText('NEW')` finds no element — the current `ResourceNode.tsx` (`viewer/src/components/ResourceNode.tsx`) renders `added` drift as a ring tint (`#22c55e`), NOT as a textual "NEW" pill.
- **Root cause:** Test was written against an older component shape. A subsequent commit `a869e30 feat(viewer): rewrite ResourceNode for light theme with real service icons` replaced the textual badge with a drift tint ring, and the test was not updated.
- **Impact on 05.1-04:** None. The failing test is unrelated to the unresolved-module and count-badge work. Our changes are additive and do not touch the `added`/`changed`/`deleted` drift paths.
- **Recommended follow-up:** Either update the test to assert the ring style (`boxShadow` or computed `driftTint` via a `data-testid` on the icon wrapper) OR restore the textual "NEW" badge if that's the intended UX. Belongs in a viewer-polish plan, not 05.1.

## Out-of-Scope Ruff Violations Observed During 05.1-02

### Pre-existing ruff errors across the CLI source tree

Running `ruff check infracanvas/` surfaces 34 errors in files that Plan 05.1-02 does NOT touch:

- `infracanvas/export/scorecard.py` — 8 E501 (line length) violations in embedded HTML template.
- `infracanvas/main.py` — 20 mixed violations (E501, F401 unused import, UP045 `Optional[X]` → `X | None`, UP037 remove-quotes, F821 undefined-name).
- `infracanvas/parser/plan.py` — 1 I001 import sort.
- `infracanvas/security/engine.py` — 1 E501.
- `infracanvas/security/scorer.py` — 1 F401 (unused `Severity` import).
- `cli/tests/test_parser.py` — 1 F401 (`import pytest` unused; present before 05.1-02 touched the file — confirmed via `git show HEAD~1:cli/tests/test_parser.py`).

All 34 predate this plan. The four files Plan 05.1-02 modified (`infracanvas/parser/hcl.py`, `infracanvas/parser/module.py`, `infracanvas/graph/builder.py`, `cli/tests/test_parser.py`) are individually ruff-clean when checked in isolation except for the pre-existing `pytest` unused import. Belongs in a hygiene-polish plan.
