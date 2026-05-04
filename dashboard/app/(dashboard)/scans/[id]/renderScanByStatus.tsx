import type { ScanGetResp } from '@/lib/types'
import { ScanPendingClient } from '@/components/scans/ScanPendingClient'
import { ScanViewerClient } from '@/components/scans/ScanViewerClient'

/**
 * Pure helper: pick which client component to render given a scan row.
 *
 * Lives in its own module (not page.tsx) because Next.js 15 restricts
 * page modules to a fixed set of exports — exporting anything else
 * tripped TS2344 against `OmitWithTag<...>`.
 *
 * Exported for vitest (see __tests__/scan-detail-polling.test.tsx) so we
 * can assert the gate logic without rendering the full RSC + Clerk
 * server-side import chain.
 *
 *   pending | failed   → <ScanPendingClient> (Plan 10 polling shell)
 *   ready  + URL set   → <ScanViewerClient>  (existing Phase 7 D-08 path)
 *   ready  + URL null  → <ScanPendingClient> (defensive — should not
 *                        happen per Plan 05 invariant; renders
 *                        "Loading scan…" rather than crash viewer)
 */
export function renderScanByStatus(scan: ScanGetResp): React.ReactNode {
  if (scan.status === 'pending' || scan.status === 'failed') {
    return <ScanPendingClient initialScan={scan} />
  }
  if (scan.status === 'ready' && scan.presigned_get_url) {
    return (
      <ScanViewerClient
        scanId={scan.id}
        initialPresignedUrl={scan.presigned_get_url}
      />
    )
  }
  // ready without URL — should never happen per Plan 05; render the
  // polling client so the user sees a stable "Loading scan…" state
  // instead of a viewer crash.
  return <ScanPendingClient initialScan={scan} />
}
