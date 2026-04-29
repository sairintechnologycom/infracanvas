'use client'
import { useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { ArrowRight, ArrowLeftRight } from 'lucide-react'
import type { ResourceDiff } from '@/lib/types'
import { DiffSummary } from './DiffSummary'
import { DiffNodeList } from './DiffNodeList'
import { CompareViewerPair } from './CompareViewerPair'

interface Props {
  diff: ResourceDiff
  scanAId: string
  scanBId: string
}

/**
 * Two-pane compare layout, mounted by `/scans/compare` RSC.
 *
 * Layout:
 *   ┌────────────────────────────────────────────────────────┐
 *   │ ← Scans / Compare   a1b2c3d → 9f8e7d   +3 −5 ~7   Swap │  52px sticky
 *   ├────────────────────────────┬───────────────────────────┤
 *   │ Resource changes (380px)   │ Viewer pair               │
 *   │  • DiffNodeList            │  ┌────────┬────────┐      │
 *   │                            │  │ Scan A │ Scan B │      │
 *   │                            │  └────────┴────────┘      │
 *   └────────────────────────────┴───────────────────────────┘
 *
 * On <1280px (xl breakpoint) the panes stack vertically (D-19 — desktop only,
 * 1080p+, no mobile fallback).
 *
 * Swap button reverses `a` and `b` in the URL via `router.replace` (NOT push)
 * so the browser back button still goes to the previous page rather than the
 * pre-swap order.
 */
export function CompareLayout({ diff, scanAId, scanBId }: Props) {
  const router = useRouter()
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)

  const handleSwap = useCallback(() => {
    const url = new URL(window.location.href)
    url.searchParams.set('a', scanBId)
    url.searchParams.set('b', scanAId)
    router.replace(`${url.pathname}?${url.searchParams.toString()}`)
  }, [router, scanAId, scanBId])

  return (
    <div data-testid="compare-layout" className="flex flex-col h-full">
      {/* Sticky summary header */}
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

      {/* Body — stacks at <xl, two-pane at xl+ */}
      <div className="flex flex-1 min-h-0 gap-4 p-4 flex-col xl:flex-row">
        {/* Left: diff list */}
        <div className="xl:w-[380px] flex-shrink-0 flex flex-col gap-3 min-h-0">
          <h2 className="text-base font-semibold text-slate-900">Resource changes</h2>
          <DiffNodeList nodes={diff.nodes} onSelect={setSelectedNodeId} />
        </div>
        {/* Right: viewer pair */}
        <div className="flex-1 min-w-0 min-h-0">
          <CompareViewerPair
            scanAId={scanAId}
            scanBId={scanBId}
            focusNodeId={selectedNodeId}
          />
        </div>
      </div>
    </div>
  )
}
