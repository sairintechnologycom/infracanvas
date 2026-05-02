---
phase: quick-260502-tra
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - dashboard/components/scans/Sparkline.tsx
  - dashboard/__tests__/sparkline.test.tsx
autonomous: true
requirements:
  - QUICK-260502-TRA-01
must_haves:
  truths:
    - "Sparkline wrapper div stretches to fill its parent's width (no collapse to ~80px viewBox natural size)"
    - "Sparkline still renders correctly inside ScoreSparkline's flex row at full available width"
    - "Hover tooltip horizontal position remains correct (still aligned with corresponding data point)"
    - "All existing dashboard tests continue to pass"
    - "Regression test asserts the wrapper div has w-full so the bug cannot silently regress"
  artifacts:
    - path: "dashboard/components/scans/Sparkline.tsx"
      provides: "Sparkline component with width-stretching wrapper"
      contains: "w-full h-full"
    - path: "dashboard/__tests__/sparkline.test.tsx"
      provides: "Regression test for wrapper width"
      contains: "w-full"
  key_links:
    - from: "dashboard/components/scans/Sparkline.tsx (line 58 wrapper)"
      to: "ScoreSparkline.tsx flex row parent"
      via: "Tailwind width class on wrapper"
      pattern: "w-full"
    - from: "tooltip absolute positioning"
      to: "wrapper div width === SVG width"
      via: "left: ${(ptArr[hoverIdx][0] / W) * 100}% calculation depends on wrapper matching SVG width"
      pattern: "left:.*%"
---

<objective>
Fix the sparkline width collapse bug: the wrapper `<div className="relative">` on line 58 of `Sparkline.tsx` has no width class. Inside a flex container, it collapses to its content's natural size (~80px viewBox), so the chart appears tiny with massive empty space inside the score card.

Purpose: Restore the intended full-width sparkline rendering on the home dashboard's score card and prevent silent regression.

Output:
- One-line fix: add `w-full h-full` to the wrapper div.
- Regression test asserting the wrapper carries `w-full`.
- All existing tests still pass.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@CLAUDE.md
@dashboard/components/scans/Sparkline.tsx
@dashboard/components/home/ScoreSparkline.tsx
@dashboard/__tests__/sparkline.test.tsx

<diagnosis>
Confirmed bug from manual investigation:
- File: `dashboard/components/scans/Sparkline.tsx`, line 58: `<div className="relative">` — no width.
- SVG inside has `viewBox="0 0 80 24"` and receives className from parent. From `ScoreSparkline.tsx:37` that className is `"w-full h-full"`.
- The wrapper sits inside a flex row at `ScoreSparkline.tsx:35`: `<div className="mt-4 h-[64px] flex items-center text-slate-700">`.
- Flex items don't auto-stretch on the main axis without `flex-1` or `w-full`, so the wrapper collapses to natural content size (the SVG's intrinsic ~80px viewBox).
- Visual: tiny 80px-wide chart with empty space to the right inside the card.

Tooltip note: line 88 uses absolute positioning relative to the wrapper. Its `left: ${(ptArr[hoverIdx][0] / W) * 100}%` math assumes wrapper width === SVG width. Setting wrapper to `w-full h-full` keeps wrapper and SVG (already `w-full h-full` via className prop) the same width — math stays correct.

Sparkline has only ONE consumer (verified by upstream grep): `dashboard/components/home/ScoreSparkline.tsx`. Both contexts want full-width fill.

Minimal fix: change line 58 from `<div className="relative">` to `<div className="relative w-full h-full">`.
</diagnosis>

<interfaces>
Sparkline current wrapper (Sparkline.tsx:58):
```tsx
<div className="relative">
  <svg
    ref={svgRef}
    viewBox={`0 0 ${W} ${H}`}
    preserveAspectRatio="none"
    className={`overflow-visible ${className}`}
    ...
  >
```

ScoreSparkline call site (ScoreSparkline.tsx:35-37):
```tsx
<div className="mt-4 h-[64px] flex items-center text-slate-700">
  <Sparkline scores={...} dates={...} className="w-full h-full" />
</div>
```

Existing test file (sparkline.test.tsx) already has 4 passing tests. We extend with one regression test.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add wrapper width fix and regression test</name>
  <files>dashboard/components/scans/Sparkline.tsx, dashboard/__tests__/sparkline.test.tsx</files>
  <behavior>
    - Regression test: render `<Sparkline scores={[70,75,82,88,91]} dates={[...]} />`, query the wrapper div (the `.relative` container — parent of the svg), assert its className contains `w-full`.
    - Existing tests (renders an svg, shows tooltip on mousemove, hides on mouseleave, tooltip Tailwind classes) must continue to pass unchanged.
  </behavior>
  <action>
    1. **Add regression test FIRST** in `dashboard/__tests__/sparkline.test.tsx`. Inside the existing `describe('Sparkline hover tooltip (RMD-06)', ...)` block (or a new `describe('Sparkline wrapper width regression', ...)` sibling block — your choice, but keep it in the same file), add:

    ```tsx
    it('wrapper div has w-full so it stretches inside flex parents', () => {
      const { container } = render(<Sparkline scores={scores} dates={dates} />)
      const svg = container.querySelector('svg')!
      const wrapper = svg.parentElement!
      expect(wrapper.className).toMatch(/\bw-full\b/)
    })
    ```

    Run `npm test -- sparkline` from the `dashboard/` directory and confirm this new test FAILS (RED step) before applying the fix.

    2. **Apply the one-line fix** in `dashboard/components/scans/Sparkline.tsx`:
       - Line 58, change:
         ```tsx
         <div className="relative">
         ```
         to:
         ```tsx
         <div className="relative w-full h-full">
         ```
       - Do NOT modify any other line. Do NOT change the SVG, viewBox, tooltip math, or any logic.

    3. Re-run `npm test -- sparkline` and confirm ALL sparkline tests pass (GREEN), including the new regression test.

    4. Run the full dashboard test suite: `npm test` (from `dashboard/`) and confirm 170/170 (or 171/171 with the new test) tests pass.

    Notes:
    - `w-full h-full` is correct (matches the SVG's already-passed `w-full h-full` className from ScoreSparkline.tsx:37) — keeps wrapper and SVG the same dimensions so the tooltip's `left: ${(ptArr[hoverIdx][0] / W) * 100}%` percentage positioning stays accurate.
    - Do not introduce a new prop for the wrapper className — Sparkline has exactly one consumer (verified) and both fix scenarios want full stretch. Keep the change minimal.
  </action>
  <verify>
    <automated>cd dashboard && npm test -- sparkline 2>&1 | tail -20</automated>
  </verify>
  <done>
    - `dashboard/components/scans/Sparkline.tsx` line 58 reads exactly `<div className="relative w-full h-full">`.
    - `grep -c 'w-full' dashboard/__tests__/sparkline.test.tsx` returns >= 1 (regression test present).
    - All sparkline tests pass (existing 4 + new regression test = 5 green).
    - Full dashboard test suite green (no regressions): `npm test` from `dashboard/` exits 0.
  </done>
</task>

</tasks>

<verification>
Run from `/Users/bhushan/Documents/Projects/Infracanvas/dashboard/`:

```bash
# Targeted: sparkline tests pass including the new regression test
npm test -- sparkline

# Full sweep: no other tests regressed
npm test
```

Manual visual check (optional, recommended):
- Start the dashboard dev server, navigate to the home page.
- The score card sparkline should now span the full available width of its container instead of collapsing to ~80px.
- Hover over the sparkline — tooltip should still appear directly above the corresponding data point (no horizontal misalignment).
</verification>

<success_criteria>
- [ ] Sparkline.tsx line 58 wrapper has `w-full h-full` added (and only that change in the file)
- [ ] sparkline.test.tsx contains a new regression test asserting the wrapper has `w-full`
- [ ] New regression test passes
- [ ] All 4 existing sparkline tests still pass
- [ ] Full dashboard test suite still green (170+ passing, 0 failing)
- [ ] No other files in the repo modified
</success_criteria>

<output>
After completion, create `.planning/quick/260502-tra-fix-sparkline-width-bug-wrapper-div-in-s/260502-tra-SUMMARY.md` documenting:
- The one-line CSS fix applied
- The regression test added
- Test results (X/X passing)
- Note: sole consumer is `ScoreSparkline.tsx`; both contexts want full-width stretch, so no prop-based override was needed.
</output>
