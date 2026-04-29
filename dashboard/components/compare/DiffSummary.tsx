'use client'

interface Props {
  summary: { added: number; removed: number; changed: number; unchanged: number }
}

/**
 * Summary chip strip rendered inside the CompareLayout sticky header.
 *
 * Shows: `+N added · −N removed · ~N changed`
 *
 * Color tokens follow UI-SPEC drift palette:
 *   added   → green
 *   removed → red
 *   changed → amber
 *
 * The `unchanged` count is intentionally NOT rendered — it's noise for the
 * compare view per D-10. It is still passed in the props for downstream
 * consumers (export, hover tooltips, future "show unchanged" toggle).
 */
export function DiffSummary({ summary }: Props) {
  return (
    <div data-testid="diff-summary" className="flex items-center gap-2 text-sm">
      <span
        data-testid="chip-added"
        className="bg-green-50 text-green-700 px-2 py-0.5 rounded-sm text-xs font-semibold tabular-nums"
      >
        +{summary.added} added
      </span>
      <span className="text-slate-300">·</span>
      <span
        data-testid="chip-removed"
        className="bg-red-50 text-red-700 px-2 py-0.5 rounded-sm text-xs font-semibold tabular-nums"
      >
        −{summary.removed} removed
      </span>
      <span className="text-slate-300">·</span>
      <span
        data-testid="chip-changed"
        className="bg-amber-50 text-amber-700 px-2 py-0.5 rounded-sm text-xs font-semibold tabular-nums"
      >
        ~{summary.changed} changed
      </span>
    </div>
  )
}
