'use client'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import type { ResourceDiff } from '@/lib/types'

interface Props {
  diff: ResourceDiff
}

/**
 * Findings-delta section card.
 *
 * The current backend `ResourceDiff.summary` exposes resource-level counts
 * (added / removed / changed / unchanged). A per-finding-severity delta is not
 * yet on the wire — when the backend ships it, swap this body for a real
 * severity breakdown. For now we surface the resource net-change so the row
 * count never disagrees with the section chips above.
 */
export function FindingsDeltaSection({ diff }: Props) {
  const net = diff.summary.added - diff.summary.removed
  const totalDelta = diff.summary.added + diff.summary.removed + diff.summary.changed

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-base flex items-center gap-2">
          <span className="inline-block w-2 h-2 rounded-full bg-slate-400" />
          Findings
        </CardTitle>
        <span className="text-sm text-slate-500 tabular-nums">{totalDelta}</span>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-slate-500">
          Net change of {net >= 0 ? '+' : ''}
          {net} resource{net === 1 || net === -1 ? '' : 's'} between scans
          {' '}
          ({diff.summary.added} added, {diff.summary.removed} removed,{' '}
          {diff.summary.changed} changed).
        </p>
      </CardContent>
    </Card>
  )
}
