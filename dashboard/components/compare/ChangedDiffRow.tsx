'use client'
import { useState } from 'react'
import type { NodeDiff } from '@/lib/types'
import { ChangedAttributesTable } from './ChangedAttributesTable'

interface Props {
  node: NodeDiff
  onDrillDown: (id: string) => void
}

/**
 * One row in the Changed-section list. Click anywhere on the row body to
 * toggle the inline ChangedAttributesTable expansion. Click the "Open ->"
 * affordance on the right to fire `onDrillDown(node.id)` (parent opens the
 * <Sheet/> drawer scoped to that resource).
 *
 * The Open button stops event propagation so a drill-down click does NOT also
 * toggle expansion.
 */
export function ChangedDiffRow({ node, onDrillDown }: Props) {
  const [expanded, setExpanded] = useState(false)
  const fieldCount = node.changed_fields.length

  return (
    <div data-kind="changed">
      <div
        className="px-6 py-2 flex items-center gap-3 hover:bg-slate-50 cursor-pointer select-none"
        onClick={() => setExpanded((v) => !v)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            setExpanded((v) => !v)
          }
        }}
      >
        <span className="text-xs text-slate-400 w-3 inline-block">
          {expanded ? '▾' : '▸'}
        </span>
        <span className="font-mono text-sm">{node.id}</span>
        <span className="text-xs text-slate-500">
          {fieldCount} attr{fieldCount === 1 ? '' : 's'}
        </span>
        <button
          type="button"
          aria-label={`Open ${node.id} in viewer`}
          onClick={(e) => {
            e.stopPropagation()
            onDrillDown(node.id)
          }}
          className="ml-auto text-xs text-slate-500 hover:text-slate-900"
        >
          Open →
        </button>
      </div>
      {expanded && (
        <ChangedAttributesTable
          fields={node.changed_fields}
          before={node.before}
          after={node.after}
        />
      )}
    </div>
  )
}
