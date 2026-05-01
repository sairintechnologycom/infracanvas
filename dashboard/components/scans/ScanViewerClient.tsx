'use client'
import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  ViewerProvider,
  DiagramCanvas,
  createViewerStore,
} from '@infracanvas/viewer'
import '@infracanvas/viewer/styles.css'
import type { ResourceGraph, ViewerStoreApi } from '@infracanvas/viewer'
import { ReactFlowProvider } from '@xyflow/react'
import { fetchScanJson } from '@/lib/r2'

interface Props {
  scanId: string
  /**
   * Presigned URL hint from RSC — used as the first fetch attempt.
   * May already be expired if the page took >300s to hydrate (D-12), but
   * fetchScanJson handles 403 with retry via onPresignedExpired.
   */
  initialPresignedUrl: string
}

export function ScanViewerClient({ scanId, initialPresignedUrl }: Props) {
  const store: ViewerStoreApi = useMemo(() => createViewerStore(), [scanId])
  const [graph, setGraph] = useState<ResourceGraph | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (graph) store.getState().setGraph(graph)
  }, [graph, store])

  const getFreshPresignedUrl = useCallback(async (): Promise<string> => {
    // Re-fetch scan metadata to get a new presigned URL (D-12 retry flow).
    // Calls our own Route Handler at /api/scan-presigned, which re-runs Clerk
    // auth and returns a fresh presigned URL from backendFetch('/v1/scans/{id}').
    const res = await fetch(`/api/scan-presigned?id=${scanId}`)
    if (!res.ok) throw new Error(`Failed to refresh presigned URL: ${res.status}`)
    const data = (await res.json()) as { presigned_get_url: string }
    return data.presigned_get_url
  }, [scanId])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)

    fetchScanJson({
      presignedUrl: initialPresignedUrl,
      onPresignedExpired: getFreshPresignedUrl,
    })
      .then((data) => {
        if (!cancelled) {
          store.getState().setGraph(data)
          setGraph(data)
          setLoading(false)
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load scan diagram')
          setLoading(false)
        }
      })

    return () => {
      cancelled = true
    }
  }, [initialPresignedUrl, getFreshPresignedUrl, store])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full text-sm text-slate-500">
        Loading scan diagram…
      </div>
    )
  }

  if (error || !graph) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3">
        <p className="text-sm text-slate-900 font-semibold">Could not load scan diagram</p>
        <p className="text-xs text-slate-500">{error ?? 'Unknown error'}</p>
        <button
          onClick={() => window.location.reload()}
          className="text-sm text-slate-900 hover:text-slate-700 hover:underline"
        >
          Try again
        </button>
      </div>
    )
  }

  return (
    <div className="h-full w-full" data-testid="scan-viewer-client">
      <ViewerProvider store={store}>
        <ReactFlowProvider>
          <DiagramCanvas />
        </ReactFlowProvider>
      </ViewerProvider>
    </div>
  )
}
