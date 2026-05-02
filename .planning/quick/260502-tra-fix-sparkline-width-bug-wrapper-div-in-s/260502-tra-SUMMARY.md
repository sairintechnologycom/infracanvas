---
phase: quick-260502-tra
plan: 01
subsystem: dashboard/components/scans
tags: [bug-fix, css, sparkline, tdd, regression-test]
dependency_graph:
  requires: []
  provides: [sparkline-full-width-fix]
  affects: [dashboard/components/home/ScoreSparkline.tsx]
tech_stack:
  added: []
  patterns: [TDD red-green, Tailwind w-full h-full on flex child]
key_files:
  created: []
  modified:
    - dashboard/components/scans/Sparkline.tsx
    - dashboard/__tests__/sparkline.test.tsx
decisions:
  - "No new prop for wrapper className — Sparkline has exactly one consumer (ScoreSparkline.tsx), both contexts want full stretch; hardcoded w-full h-full is the minimal, correct fix"
  - "w-full h-full on wrapper keeps wrapper and SVG (already w-full h-full via className prop) the same dimensions, so tooltip left:% positioning math remains accurate"
metrics:
  duration: "< 5 minutes"
  completed: "2026-05-02"
  tasks_completed: 1
  files_modified: 2
---

# Quick Task 260502-tra: Fix Sparkline Width Collapse in Flex Container

One-line Tailwind fix (`w-full h-full` on wrapper div) plus a regression test to prevent silent re-introduction of the sparkline width collapse bug inside flex parents.

## What Was Done

### The Bug

`dashboard/components/scans/Sparkline.tsx` line 58: `<div className="relative">` had no width class. Inside the flex row in `ScoreSparkline.tsx` (`<div className="mt-4 h-[64px] flex items-center text-slate-700">`), the wrapper collapsed to its content's natural size — the SVG's intrinsic ~80px viewBox — leaving the chart tiny with empty space to the right inside the score card.

### The Fix

Changed line 58 from:
```tsx
<div className="relative">
```
to:
```tsx
<div className="relative w-full h-full">
```

This is a one-character addition that makes the wrapper stretch to fill the flex parent. The SVG child already receives `w-full h-full` via the `className` prop from `ScoreSparkline.tsx:37`, so wrapper and SVG are now the same dimensions — the tooltip's `left: ${(ptArr[hoverIdx][0] / W) * 100}%` math stays accurate.

### Regression Test Added

Added a new `describe('Sparkline wrapper width regression')` block in `dashboard/__tests__/sparkline.test.tsx`:

```tsx
it('wrapper div has w-full so it stretches inside flex parents', () => {
  const { container } = render(<Sparkline scores={scores} dates={dates} />)
  const svg = container.querySelector('svg')!
  const wrapper = svg.parentElement!
  expect(wrapper.className).toMatch(/\bw-full\b/)
})
```

## TDD Execution

| Phase | Result |
|-------|--------|
| RED — test added, fix NOT yet applied | 1 failed / 4 passed — confirmed regression test fails as expected |
| GREEN — fix applied | 5/5 sparkline tests pass |
| Full suite | 171/171 tests pass (0 regressions) |

## Consumer Note

Sole consumer verified: `dashboard/components/home/ScoreSparkline.tsx`. Both the home score card and any future consumers want full-width stretch inside their flex parent. No prop-based override was needed — `w-full h-full` is the correct unconditional default for this component.

## Commits

| Hash | Description |
|------|-------------|
| 373b0d9 | fix(260502-tra): add w-full h-full to Sparkline wrapper div to prevent width collapse in flex containers |

## Deviations from Plan

None — plan executed exactly as written.

## Threat Flags

None — CSS-only change with no new network surface, auth paths, or schema changes.

## Self-Check: PASSED

- `dashboard/components/scans/Sparkline.tsx` modified: FOUND
- `dashboard/__tests__/sparkline.test.tsx` modified: FOUND
- Commit 373b0d9 exists: FOUND
- Line 58 reads `<div className="relative w-full h-full">`: CONFIRMED
- `grep -c 'w-full' dashboard/__tests__/sparkline.test.tsx` >= 1: CONFIRMED (2 occurrences)
- All 5 sparkline tests green: CONFIRMED
- Full suite 171/171 green: CONFIRMED
