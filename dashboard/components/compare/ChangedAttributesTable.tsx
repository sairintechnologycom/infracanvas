'use client'
import { useState } from 'react'

interface Props {
  fields: string[]
  before: Record<string, unknown> | null
  after: Record<string, unknown> | null
}

const MAX_VISIBLE = 10

/**
 * Inline before/after attribute table used inside ChangedDiffRow.
 *
 * Caps visible rows at MAX_VISIBLE (10). When `fields.length > MAX_VISIBLE` an
 * "+N more attributes" toggle reveals the remainder. Click that toggle to
 * expand to the full list.
 *
 * Values are rendered through `formatValue` — primitives stringify directly,
 * objects/arrays go through `JSON.stringify`. React escapes the resulting text
 * node, so any string content from `before`/`after` is rendered safely as
 * inert text (no raw HTML injection vector — see threat model T-07.1-11 in
 * 07.1-05-PLAN.md).
 */
export function ChangedAttributesTable({ fields, before, after }: Props) {
  const [showAll, setShowAll] = useState(false)
  const visible = showAll ? fields : fields.slice(0, MAX_VISIBLE)
  const hiddenCount = Math.max(0, fields.length - MAX_VISIBLE)

  return (
    <div className="px-6 py-3 bg-slate-50 border-t border-slate-100">
      <table className="w-full text-sm tabular-nums">
        <thead className="text-xs text-slate-500 uppercase">
          <tr>
            <th className="text-left font-medium pb-2">Attribute</th>
            <th className="text-left font-medium pb-2">Before</th>
            <th className="text-left font-medium pb-2">After</th>
          </tr>
        </thead>
        <tbody>
          {visible.map((field) => (
            <tr key={field} className="border-t border-slate-100">
              <td className="py-1.5 font-mono">{field}</td>
              <td className="py-1.5 font-mono text-slate-500">
                {formatValue(before?.[field])}
              </td>
              <td className="py-1.5 font-mono">{formatValue(after?.[field])}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {!showAll && hiddenCount > 0 && (
        <button
          type="button"
          onClick={() => setShowAll(true)}
          className="mt-2 text-xs text-slate-500 hover:text-slate-900"
        >
          +{hiddenCount} more attributes
        </button>
      )}
    </div>
  )
}

function formatValue(v: unknown): string {
  if (v == null) return '—'
  if (typeof v === 'string') return v
  if (typeof v === 'number' || typeof v === 'boolean') return String(v)
  try {
    return JSON.stringify(v)
  } catch {
    return String(v)
  }
}
