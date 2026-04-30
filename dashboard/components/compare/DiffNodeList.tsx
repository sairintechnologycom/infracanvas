'use client'
import type { NodeDiff } from '@/lib/types'

interface Props {
  nodes: NodeDiff[]
  onSelect?: (id: string) => void
}

/**
 * Per-kind row styles — left border + tinted background, drift palette tokens
 * (see @infracanvas/viewer/styles.css for sev-* tokens). 'unchanged' rows are
 * filtered out before rendering — D-10 says the compare view emphasises change.
 */
const KIND_STYLES: Record<NodeDiff['kind'], string> = {
  added: 'bg-green-50 border-l-2 border-green-500',
  removed: 'bg-red-50 border-l-2 border-red-500',
  changed: 'bg-amber-50 border-l-2 border-amber-500',
  unchanged: 'bg-white',
}

const KIND_BADGE_STYLES: Record<NodeDiff['kind'], string> = {
  added: 'bg-green-100 text-green-700',
  removed: 'bg-red-100 text-red-700',
  changed: 'bg-amber-100 text-amber-700',
  unchanged: 'bg-slate-100 text-slate-500',
}

/**
 * Windowed list of resource-level diff rows.
 *
 * Uses CSS `overflow-y-auto max-h-[60vh]` for windowing per planning context —
 * no virtualization library. The 5000-node cap upstream (Plan 07-03) keeps
 * DOM size bounded (T-07-08-03 — DoS via large diff response).
 *
 * Rows of kind='unchanged' are filtered out — the compare view is for changes.
 *
 * Each row exposes `data-testid="diff-node-row"` and `data-kind="{kind}"` for
 * E2E + a11y selectors. Clicking a row invokes `onSelect(node.id)` if provided.
 *
 * NOTE: This component is no longer rendered by CompareLayout (which now uses
 * the 4-section diff card layout per Plan 07.1-05). It is kept temporarily
 * because legacy tests still exercise it. Will be deleted in a follow-up
 * plan once the test file is split.
 */
export function DiffNodeList({ nodes, onSelect }: Props) {
  const visible = nodes.filter((n) => n.kind !== 'unchanged')

  return (
    <div
      data-testid="diff-node-list"
      className="overflow-y-auto max-h-[60vh] divide-y divide-slate-100 border border-slate-200 rounded-md bg-white"
    >
      {visible.map((node) => {
        const label =
          node.kind === 'changed'
            ? `changed (${node.changed_fields.length} attr${node.changed_fields.length === 1 ? '' : 's'})`
            : node.kind
        return (
          <div
            key={node.id}
            data-testid="diff-node-row"
            data-kind={node.kind}
            className={`flex items-center gap-3 px-4 py-2 cursor-pointer hover:opacity-80 ${KIND_STYLES[node.kind]}`}
            onClick={() => onSelect?.(node.id)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault()
                onSelect?.(node.id)
              }
            }}
          >
            <span className="font-mono text-sm text-slate-900 truncate flex-1">{node.id}</span>
            <span
              className={`px-2 py-0.5 rounded-sm text-xs font-semibold ${KIND_BADGE_STYLES[node.kind]} whitespace-nowrap`}
            >
              {label}
            </span>
          </div>
        )
      })}
    </div>
  )
}
