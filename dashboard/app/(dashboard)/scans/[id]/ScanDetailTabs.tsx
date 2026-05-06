'use client'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import {
  ViewerProvider,
  ViewerApp,
  createViewerStore,
} from '@infracanvas/viewer'
import '@infracanvas/viewer/styles.css'
import type { ResourceGraph, ViewerStoreApi } from '@infracanvas/viewer'
import { fetchScanJson } from '@/lib/r2'
import { CostTab } from './CostTab'

interface Props {
  scanId: string
  initialPresignedUrl: string
}

export function ScanDetailTabs({ scanId, initialPresignedUrl }: Props) {
  const store: ViewerStoreApi = useMemo(() => createViewerStore(), [scanId])
  const [graph, setGraph] = useState<ResourceGraph | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const getFreshPresignedUrl = useCallback(async (): Promise<string> => {
    const res = await fetch(`/api/scan-presigned?id=${scanId}`)
    if (!res.ok) throw new Error(`Failed to refresh presigned URL: ${res.status}`)
    const data = (await res.json()) as { presigned_get_url: string }
    return data.presigned_get_url
  }, [scanId])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    fetchScanJson({ presignedUrl: initialPresignedUrl, onPresignedExpired: getFreshPresignedUrl })
      .then((data) => {
        if (!cancelled) {
          store.getState().setGraph(data)
          store.getState().setHasFlowMap(Boolean(data.network_paths?.length))
          setGraph(data)
          setLoading(false)
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load scan')
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
        Loading…
      </div>
    )
  }

  if (error || !graph) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3">
        <p className="text-sm text-slate-900 font-semibold">Could not load scan</p>
        <p className="text-xs text-slate-500">{error ?? 'Unknown error'}</p>
      </div>
    )
  }

  return (
    <Tabs defaultValue="viewer" className="h-full flex flex-col">
      <TabsList variant="line" className="px-4 border-b border-slate-200">
        <TabsTrigger value="viewer">Viewer</TabsTrigger>
        <TabsTrigger value="cost">Cost</TabsTrigger>
      </TabsList>
      <TabsContent value="viewer" className="flex-1 min-h-0">
        <ViewerProvider store={store}>
          <ViewerApp />
        </ViewerProvider>
      </TabsContent>
      <TabsContent value="cost" className="flex-1 overflow-auto">
        <CostTab data={graph.costlens ?? null} />
      </TabsContent>
    </Tabs>
  )
}
