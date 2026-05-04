'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'

import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import type { ScanGetResp } from '@/lib/types'

export interface ScanPendingClientProps {
  initialScan: ScanGetResp
}

/**
 * Polling shell for pending/failed scan rows.
 *
 * Picks up where ScanTriggerForm (Plan 09) leaves the user
 * (`router.push('/scans/{id}')`) and tracks the row through its
 * terminal state.
 *
 * Polling cadence (CC-14):
 *   - useEffect + setInterval + cancelled-flag teardown — NOT react-query
 *     (PATTERNS A1 correction).
 *   - Polls /api/scan-status?id={scan.id} every 2s while
 *     scan.status === 'pending'.
 *   - On 'ready': clearInterval + router.refresh() so the parent RSC
 *     re-renders the viewer (Phase 7 D-08 path) — UNCHANGED for ready.
 *   - On 'failed': clearInterval + render error_message + Retry CTA.
 *
 * Retry path (T-07.5-10-03 — params sourced ONLY from server-fetched
 * scan row, never from a client-editable input):
 *   - POST /api/scans/from-github with the scan's github_installation_id,
 *     github_repo, github_branch, source_path columns; on success
 *     router.push to the new scan id.
 *   - When the scan was triggered via CLI (no github_* columns),
 *     surfaces a friendly "re-scan from /settings/integrations" hint.
 */
export function ScanPendingClient({ initialScan }: ScanPendingClientProps) {
  const router = useRouter()
  const [scan, setScan] = useState<ScanGetResp>(initialScan)
  const [retrying, setRetrying] = useState(false)
  const [retryError, setRetryError] = useState<string | null>(null)

  useEffect(() => {
    // If the scan is already ready, refresh the parent RSC once and
    // never start polling.
    if (scan.status === 'ready') {
      router.refresh()
      return
    }
    // Failed is also a terminal state — render the failure UI but don't
    // start an interval.
    if (scan.status === 'failed') {
      return
    }

    let cancelled = false
    const tick = async () => {
      if (cancelled) return
      try {
        const res = await fetch(`/api/scan-status?id=${scan.id}`)
        if (cancelled) return
        if (!res.ok) return
        const data = (await res.json()) as ScanGetResp
        if (cancelled) return
        setScan(data)
        if (data.status === 'ready') {
          router.refresh()
        }
      } catch {
        // Swallow — next tick will retry. Network blips during long
        // pending windows are expected; the worker still owns the row.
      }
    }
    const intervalId = setInterval(tick, 2000)
    return () => {
      cancelled = true
      clearInterval(intervalId)
    }
    // We re-run when the scan id changes OR status transitions out of
    // pending — both are valid teardown triggers.
  }, [scan.id, scan.status, router])

  const canRetry = !!(
    scan.github_installation_id &&
    scan.github_repo &&
    scan.github_branch
  )

  const handleRetry = async () => {
    if (!canRetry || retrying) return
    setRetrying(true)
    setRetryError(null)
    try {
      const res = await fetch('/api/scans/from-github', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          installation_id: scan.github_installation_id,
          repo: scan.github_repo,
          branch: scan.github_branch,
          path: scan.source_path || '.',
        }),
      })
      if (!res.ok) {
        throw new Error(`http_${res.status}`)
      }
      const data = (await res.json()) as { scan_id: string }
      router.push(`/scans/${data.scan_id}`)
    } catch (err) {
      const code = err instanceof Error ? err.message : 'unknown'
      setRetryError(
        code === 'http_503'
          ? 'GitHub is rate-limiting us right now. Please retry in a minute.'
          : 'Failed to re-trigger scan. Please retry.',
      )
      setRetrying(false)
    }
  }

  // ── Render branches ────────────────────────────────────────────────────────

  const repoLabel = scan.github_repo ?? '(unknown repo)'
  const branchLabel = scan.github_branch ?? scan.branch ?? '(unknown branch)'

  if (scan.status === 'failed') {
    return (
      <div
        className="flex flex-col items-center justify-center gap-4 p-8"
        data-testid="scan-pending-failed"
      >
        <div className="text-sm font-semibold text-slate-900">
          Scan failed for {repoLabel}@{branchLabel}
        </div>
        <div className="text-sm text-red-600" role="alert">
          {scan.error_message ?? 'Unknown error'}
        </div>
        {canRetry ? (
          <>
            <Button onClick={handleRetry} disabled={retrying}>
              {retrying ? 'Retrying…' : 'Retry'}
            </Button>
            {retryError && (
              <div className="text-xs text-red-600" role="alert">
                {retryError}
              </div>
            )}
          </>
        ) : (
          <div className="text-xs text-slate-500">
            Cannot retry from here — re-scan from /settings/integrations
          </div>
        )}
      </div>
    )
  }

  if (scan.status === 'ready') {
    // Effect already called router.refresh(); render a placeholder while
    // the parent RSC reloads.
    return (
      <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
        Loading scan…
      </div>
    )
  }

  // Pending (default)
  return (
    <div
      className="flex flex-col gap-3 p-6"
      data-testid="scan-pending-loading"
    >
      <div className="text-sm font-semibold text-slate-900">
        Scanning {repoLabel}@{branchLabel}…
      </div>
      <div className="text-xs text-slate-500">
        This usually takes under a minute. We&apos;ll refresh automatically.
      </div>
      <div className="space-y-2 mt-2">
        <Skeleton className="h-6 w-2/3" />
        <Skeleton className="h-6 w-1/2" />
        <Skeleton className="h-32 w-full" />
      </div>
    </div>
  )
}
