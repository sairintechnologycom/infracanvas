'use client'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import type { NodeDiff } from '@/lib/types'
import { ChangedDiffRow } from './ChangedDiffRow'

interface Props {
  rows: NodeDiff[]
  onRowDrillDown: (id: string) => void
}

/**
 * Wraps a list of ChangedDiffRow inside a Card. Each row is independently
 * collapsible; the parent only drives the drill-down Sheet via
 * `onRowDrillDown`.
 *
 * Header dot is amber-500 to match the drift `changed` palette token.
 */
export function ChangedDiffSection({ rows, onRowDrillDown }: Props) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-base flex items-center gap-2">
          <span className="inline-block w-2 h-2 rounded-full bg-amber-500" />
          Changed
        </CardTitle>
        <span className="text-sm text-slate-500 tabular-nums">{rows.length}</span>
      </CardHeader>
      <CardContent className="p-0">
        {rows.length === 0 ? (
          <p className="px-6 py-4 text-sm text-slate-500">No changed resources.</p>
        ) : (
          <div className="divide-y divide-slate-100">
            {rows.map((node) => (
              <ChangedDiffRow
                key={node.id}
                node={node}
                onDrillDown={onRowDrillDown}
              />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
