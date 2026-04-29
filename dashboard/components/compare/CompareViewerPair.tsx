'use client'
import { useEffect, useState, useCallback, useMemo } from 'react'
import { ViewerProvider, DiagramCanvas, createViewerStore } from '@infracanvas/viewer'
import '@infracanvas/viewer/styles.css'
import type { ResourceGraph } from '@infracanvas/viewer'
import { fetchScanJson } from '@/lib/r2'

interface Props {
  scanAId: string
  scanBId: string
  focusNodeId: string | null
}

/**
 * Side-by-side viewer pair for the compare page.
 *
 * Lifecycle:
 *   1. On mount, fetch presigned URLs for BOTH scans concurrently via the
 *      auth'd `/api/scan-presigned` route (re-uses the ScanViewerClient
 *      handler — Plan 07-07).
 *   2. With both presigned URLs in hand, fetch JSON from R2 in parallel
 *      (`Promise.all`) — Pitfall 7: never sequential for two large blobs.
 *      Each fetch retries once on 403 via `fetchScanJson` (Plan 07-07 D-12).
 *   3. Mount two `<ViewerProvider>` instances side-by-side, each with its own
 *      `<DiagramCanvas>`. Drift overlay coloring comes from the global
 *      `@infracanvas/viewer/styles.css` import (D-04 tokens).
 *
 * Layout: side-by-side at xl (1280px+), stacked below.
 *
 * `focusNodeId`: when a row in DiffNodeList is clicked, the parent passes the
 * resource id here. The current `@infracanvas/viewer` API does not expose a
 * `focusNode(id)` imperative method, so we log a TODO and defer scroll-sync
 * to a follow-up plan rather than landing dead UI. Tracked for future plan.
 */
export function CompareViewerPair({ scanAId, scanBId, focusNodeId }: Props) {
  const [scanA, setScanA] = useState<ResourceGraph | null>(null)
  const [scanB, setScanB] = useState<ResourceGraph | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refreshPresigned = useCallback(async (id: string): Promise<string> => {
    const res = await fetch(`/api/scan-presigned?id=${id}`)
    if (!res.ok) throw new Error(`Failed to refresh presigned URL: ${res.status}`)
    const data = (await res.json()) as { presigned_get_url: string }
    return data.presigned_get_url
  }, [])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    setScanA(null)
    setScanB(null)

    const load = async () => {
      // Step 1: fetch both ScanGetResp metadata in parallel — D-08 Pitfall 2,
      // we do NOT trust any RSC-embedded URL because TTL <=300s.
      const [metaA, metaB] = await Promise.all([
        fetch(`/api/scan-presigned?id=${scanAId}`).then(async (r) => {
          if (!r.ok) throw new Error(`scan_a_${r.status}`)
          return (await r.json()) as { presigned_get_url: string }
        }),
        fetch(`/api/scan-presigned?id=${scanBId}`).then(async (r) => {
          if (!r.ok) throw new Error(`scan_b_${r.status}`)
          return (await r.json()) as { presigned_get_url: string }
        }),
      ])

      // Step 2: fetch both R2 blobs in parallel
      const [graphA, graphB] = await Promise.all([
        fetchScanJson({
          presignedUrl: metaA.presigned_get_url,
          onPresignedExpired: () => refreshPresigned(scanAId),
        }),
        fetchScanJson({
          presignedUrl: metaB.presigned_get_url,
          onPresignedExpired: () => refreshPresigned(scanBId),
        }),
      ])

      if (!cancelled) {
        setScanA(graphA)
        setScanB(graphB)
        setLoading(false)
      }
    }

    load().catch((err) => {
      if (!cancelled) {
        setError(err instanceof Error ? err.message : 'Failed to load scan data.')
        setLoading(false)
      }
    })

    return () => {
      cancelled = true
    }
  }, [scanAId, scanBId, refreshPresigned])

  useEffect(() => {
    if (focusNodeId) {
      // TODO: viewer focusNode API not yet exposed — scroll sync deferred.
      // Tracked for follow-up plan once @infracanvas/viewer adds an
      // imperative `useViewerStore.getState().focusNode(id)` action.
      // eslint-disable-next-line no-console
      console.debug('[CompareViewerPair] focusNode requested:', focusNodeId)
    }
  }, [focusNodeId])

  // Per-scan isolated stores — each ViewerProvider gets its own store via
  // createViewerStore() to prevent state bleed between Scan A and Scan B
  // (D-11 from Phase 5: per-page viewer instance). When the scan graph
  // arrives, push it into the store's setGraph action.
  const storeA = useMemo(() => createViewerStore(), [scanAId])
  const storeB = useMemo(() => createViewerStore(), [scanBId])

  useEffect(() => {
    if (scanA) storeA.getState().setGraph(scanA)
  }, [scanA, storeA])

  useEffect(() => {
    if (scanB) storeB.getState().setGraph(scanB)
  }, [scanB, storeB])

  if (loading) {
    return (
      <div className="flex flex-col xl:flex-row gap-4 h-full">
        <div className="flex-1 min-h-[400px] bg-slate-100 animate-pulse rounded-md" />
        <div className="flex-1 min-h-[400px] bg-slate-100 animate-pulse rounded-md" />
      </div>
    )
  }

  if (error || !scanA || !scanB) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-2">
        <p className="text-sm text-red-600 font-semibold">Failed to load scan data.</p>
        {error && <p className="text-xs text-slate-500">{error}</p>}
      </div>
    )
  }

  return (
    <div className="flex flex-col xl:flex-row gap-4 h-full">
      <div className="flex-1 min-h-[400px] flex flex-col gap-2 min-w-0">
        <span className="text-xs text-slate-500 font-mono">
          Scan A · {scanAId.slice(0, 8)}
        </span>
        <div className="flex-1 border border-slate-200 rounded-md overflow-hidden bg-white">
          <ViewerProvider store={storeA}>
            <DiagramCanvas />
          </ViewerProvider>
        </div>
      </div>
      <div className="flex-1 min-h-[400px] flex flex-col gap-2 min-w-0">
        <span className="text-xs text-slate-500 font-mono">
          Scan B · {scanBId.slice(0, 8)}
        </span>
        <div className="flex-1 border border-slate-200 rounded-md overflow-hidden bg-white">
          <ViewerProvider store={storeB}>
            <DiagramCanvas />
          </ViewerProvider>
        </div>
      </div>
    </div>
  )
}
