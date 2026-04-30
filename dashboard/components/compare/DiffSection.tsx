'use client'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import type { NodeDiff } from '@/lib/types'

interface Props {
  title: 'Added' | 'Removed'
  rows: NodeDiff[]
  dotClass: string
  onRowDrillDown: (id: string) => void
}

/**
 * Generic single-section card used for the Added and Removed diff sections.
 *
 * Header: coloured dot + title + count chip on the right.
 * Body: divided list of resource rows, each with the resource id (font-mono),
 * the resource type (slate-500), and an "Open ->" affordance on the right that
 * fires `onRowDrillDown(node.id)`.
 *
 * Renders an empty-state line when `rows.length === 0`.
 */
export function DiffSection({ title, rows, dotClass, onRowDrillDown }: Props) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-base flex items-center gap-2">
          <span className={`inline-block w-2 h-2 rounded-full ${dotClass}`} />
          {title}
        </CardTitle>
        <span className="text-sm text-slate-500 tabular-nums">{rows.length}</span>
      </CardHeader>
      <CardContent className="p-0">
        {rows.length === 0 ? (
          <p className="px-6 py-4 text-sm text-slate-500">
            No {title.toLowerCase()} resources.
          </p>
        ) : (
          <ul className="divide-y divide-slate-100">
            {rows.map((node) => (
              <li
                key={node.id}
                className="px-6 py-2 flex items-center gap-3 hover:bg-slate-50"
              >
                <span className="font-mono text-sm">{node.id}</span>
                <button
                  type="button"
                  aria-label={`Open ${node.id} in viewer`}
                  onClick={() => onRowDrillDown(node.id)}
                  className="ml-auto text-xs text-slate-500 hover:text-slate-900"
                >
                  Open →
                </button>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}
