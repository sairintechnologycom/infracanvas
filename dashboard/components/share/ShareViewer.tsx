'use client'
import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  ViewerProvider,
  DiagramCanvas,
  createViewerStore,
} from '@infracanvas/viewer'
import '@infracanvas/viewer/styles.css'
import type { ResourceGraph, ViewerStoreApi } from '@infracanvas/viewer'
import { fetchScanJson } from '@/lib/r2'

export interface ShareViewerScanMetadata {
  created_at?: string
  commit_sha?: string | null
  branch?: string | null
  summary_json?: {
    score?: number
    findings?: { critical?: number; high?: number }
  } | null
}

interface Props {
  presignedUrl: string
  metadata: ShareViewerScanMetadata | null
  teamName: string | null
}

function formatShareDate(iso: string): string {
  const d = new Date(iso)
  const datePart = d.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    timeZone: 'UTC',
  })
  const timePart = d.toISOString().slice(11, 16)
  return `${datePart} · ${timePart} UTC`
}

function ScoreGradePill({ score }: { score: number }) {
  let grade: string
  let cls: string
  if (score >= 90) {
    grade = 'A'
    cls = 'bg-green-100 text-green-700'
  } else if (score >= 80) {
    grade = 'B+'
    cls = 'bg-sky-100 text-sky-700'
  } else if (score >= 70) {
    grade = 'C'
    cls = 'bg-amber-100 text-amber-700'
  } else if (score >= 60) {
    grade = 'D'
    cls = 'bg-orange-100 text-orange-700'
  } else {
    grade = 'F'
    cls = 'bg-red-100 text-red-700'
  }
  return (
    <span
      className={`inline-flex items-center justify-center px-2 h-5 rounded-sm text-xs font-semibold ${cls}`}
    >
      {grade}
    </span>
  )
}

/**
 * ShareViewer — full-bleed, read-only DiagramCanvas for the public share landing.
 *
 * D-08: scan JSON is fetched client-direct from the R2 presigned URL.
 * D-12: the presigned URL TTL is short — but on this public path we have no
 * authenticated way to refresh it. If fetchScanJson returns 403, we surface
 * an actionable error rather than retrying with a stale (now-expired) URL.
 */
export function ShareViewer({ presignedUrl, metadata, teamName }: Props) {
  const store: ViewerStoreApi = useMemo(() => createViewerStore(), [])
  const [graph, setGraph] = useState<ResourceGraph | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const onPresignedExpired = useCallback(async (): Promise<string> => {
    // No way to refresh a presigned URL on the public path without re-verifying
    // the share token; fail loud instead of looping.
    throw new Error(
      'Share link presigned URL expired — please reload the page.',
    )
  }, [])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    fetchScanJson({ presignedUrl, onPresignedExpired })
      .then((data) => {
        if (!cancelled) {
          store.getState().setGraph(data)
          setGraph(data)
          setLoading(false)
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(
            err instanceof Error ? err.message : 'Failed to load scan diagram',
          )
          setLoading(false)
        }
      })
    return () => {
      cancelled = true
    }
  }, [presignedUrl, onPresignedExpired, store])

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <p className="text-sm text-slate-500">Loading scan diagram…</p>
      </div>
    )
  }

  if (error || !graph) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="bg-white border border-slate-200 rounded-lg p-8 max-w-md text-center">
          <h1 className="text-base font-semibold text-slate-900">
            Could not load scan diagram
          </h1>
          <p className="text-sm text-slate-500 mt-2">
            {error ?? 'Unknown error'}
          </p>
        </div>
      </div>
    )
  }

  const score = metadata?.summary_json?.score
  const critical = metadata?.summary_json?.findings?.critical
  const high = metadata?.summary_json?.findings?.high

  return (
    <div className="flex flex-col h-screen" data-testid="share-viewer">
      {/* Top bar — branded, full-width */}
      <div className="h-12 bg-slate-50 border-b border-slate-200 px-6 flex items-center gap-4 flex-shrink-0">
        <span className="text-sm font-semibold text-slate-900">
          {teamName ?? 'InfraCanvas'}
        </span>
        {metadata?.created_at && (
          <span className="text-sm text-slate-500 whitespace-nowrap">
            {formatShareDate(metadata.created_at)}
          </span>
        )}
        {metadata?.commit_sha && (
          <span className="font-mono text-xs text-slate-500 whitespace-nowrap">
            @{metadata.commit_sha.slice(0, 7)}
          </span>
        )}
        {typeof score === 'number' && <ScoreGradePill score={score} />}
        {(typeof critical === 'number' || typeof high === 'number') && (
          <span className="text-xs text-slate-500 whitespace-nowrap">
            <span className={critical && critical > 0 ? 'text-red-600 font-semibold' : ''}>
              {critical ?? 0}c
            </span>
            {' / '}
            <span className={high && high > 0 ? 'text-orange-600 font-semibold' : ''}>
              {high ?? 0}h
            </span>
          </span>
        )}
        <div className="ml-auto text-xs text-slate-500">
          Made with{' '}
          <a
            href="https://infracanvas.dev"
            target="_blank"
            rel="noopener"
            className="hover:text-slate-900 hover:underline underline-offset-2"
          >
            InfraCanvas
          </a>
        </div>
      </div>

      {/* Viewer fills the rest */}
      <div className="flex-1 min-h-0">
        <ViewerProvider store={store}>
          <DiagramCanvas />
        </ViewerProvider>
      </div>
    </div>
  )
}
