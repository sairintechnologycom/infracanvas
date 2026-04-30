'use client'
import { useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { ArrowRight, ArrowLeftRight } from 'lucide-react'
import type { ResourceDiff } from '@/lib/types'
import { DiffSummary } from './DiffSummary'
import { DiffSection } from './DiffSection'
import { ChangedDiffSection } from './ChangedDiffSection'
import { FindingsDeltaSection } from './FindingsDeltaSection'
import { DrillDownSheet } from './DrillDownSheet'

interface Props {
  diff: ResourceDiff
  scanAId: string
  scanBId: string
}

/**
 * 4-section diff card layout for `/scans/compare`.
 *
 * Replaces the Phase 7 dual-canvas viewer-pair, which D-10 explicitly rejects
 * ("compare layout ships the side-by-side dual canvas D-10 explicitly rejects;
 * no attribute-level expanders" — UI-REVIEW Pillar 2 BLOCKER #2).
 *
 * Layout:
 *   ┌────────────────────────────────────────────────────────┐
 *   │ ← Scans / Compare   a1b2c3d → 9f8e7d   +N −N ~N   Swap │  52px sticky
 *   ├────────────────────────────────────────────────────────┤
 *   │   [Card] Added    (count)                              │
 *   │   [Card] Removed  (count)                              │
 *   │   [Card] Changed  (count) — rows expand to attr table  │
 *   │   [Card] Findings (count)                              │
 *   └────────────────────────────────────────────────────────┘
 *
 * Each row exposes an "Open ->" affordance that opens a right-side <Sheet/>
 * drawer scoped to that resource. The drawer state is owned here so all four
 * sections share a single drill target.
 *
 * Swap button reverses `a` and `b` in the URL via `router.replace` (NOT push)
 * so the browser back button still goes to the previous page rather than the
 * pre-swap order.
 */
export function CompareLayout({ diff, scanAId, scanBId }: Props) {
  const router = useRouter()
  const [drillResourceId, setDrillResourceId] = useState<string | null>(null)

  const handleSwap = useCallback(() => {
    const url = new URL(window.location.href)
    url.searchParams.set('a', scanBId)
    url.searchParams.set('b', scanAId)
    router.replace(`${url.pathname}?${url.searchParams.toString()}`)
  }, [router, scanAId, scanBId])

  const added = diff.nodes.filter((n) => n.kind === 'added')
  const removed = diff.nodes.filter((n) => n.kind === 'removed')
  const changed = diff.nodes.filter((n) => n.kind === 'changed')

  return (
    <div data-testid="compare-layout" className="flex flex-col h-full">
      {/* Sticky summary header — preserved from prior layout */}
      <div className="h-[52px] bg-slate-50 border-b border-slate-200 px-6 flex items-center gap-4 sticky top-0 z-10 flex-shrink-0">
        <span className="text-sm text-slate-500 whitespace-nowrap">
          ←{' '}
          <Link href="/scans" className="hover:text-slate-900">
            Scans
          </Link>{' '}
          / Compare
        </span>
        <span className="text-slate-300">|</span>
        <div className="flex items-center gap-2 font-mono text-sm text-slate-700">
          <span>{scanAId.slice(0, 8)}</span>
          <ArrowRight className="h-4 w-4 text-slate-400" />
          <span>{scanBId.slice(0, 8)}</span>
        </div>
        <DiffSummary summary={diff.summary} />
        <button
          type="button"
          onClick={handleSwap}
          className="ml-auto text-xs text-slate-500 hover:text-slate-900 flex items-center gap-1 px-2 py-1 rounded-sm border border-transparent hover:border-slate-300"
          aria-label="Swap scan comparison order"
        >
          <ArrowLeftRight className="h-3 w-3" /> Swap
        </button>
      </div>

      {/* 4-section vertical stack of diff cards */}
      <div className="flex-1 min-h-0 overflow-y-auto">
        <div className="max-w-7xl mx-auto w-full px-8 py-6 space-y-6">
          <DiffSection
            title="Added"
            rows={added}
            dotClass="bg-green-500"
            onRowDrillDown={setDrillResourceId}
          />
          <DiffSection
            title="Removed"
            rows={removed}
            dotClass="bg-red-500"
            onRowDrillDown={setDrillResourceId}
          />
          <ChangedDiffSection
            rows={changed}
            onRowDrillDown={setDrillResourceId}
          />
          <FindingsDeltaSection diff={diff} />
        </div>
      </div>

      <DrillDownSheet
        resourceId={drillResourceId}
        scanBId={scanBId}
        onClose={() => setDrillResourceId(null)}
      />
    </div>
  )
}
