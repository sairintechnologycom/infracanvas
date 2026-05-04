import { NextRequest, NextResponse } from 'next/server'
import { backendFetch } from '@/lib/backend'
import type { ScanGetResp } from '@/lib/types'

/**
 * Polling-friendly proxy for scan status.
 *
 * GET /api/scan-status?id=<uuid>
 *   → backendFetch('/v1/scans/{id}')
 *   → returns the extended ScanGetResp JSON (status + error_message
 *     + source_path + github_* + presigned_get_url; presigned URL is
 *     null until status === 'ready' per Plan 05).
 *
 * ScanPendingClient (Plan 10) polls this every 2s while the scan is
 * 'pending'; backendFetch attaches the Clerk Bearer token so this is
 * NOT an auth bypass — unauthenticated requests fail in auth() before
 * the backend call fires (same posture as scan-presigned/route.ts).
 *
 * Returns 404 (not 403) for cross-team scan IDs (mirrors backend D-18
 * existence-leak guard); other errors collapse to 500.
 */
export async function GET(req: NextRequest) {
  const id = req.nextUrl.searchParams.get('id')
  if (!id) {
    return NextResponse.json({ error: 'missing_id' }, { status: 400 })
  }
  try {
    const data = await backendFetch<ScanGetResp>(`/v1/scans/${id}`)
    return NextResponse.json(data)
  } catch (err) {
    const status = err instanceof Error && err.message === '404' ? 404 : 500
    return NextResponse.json(
      { error: status === 404 ? 'Not found' : 'Internal error' },
      { status },
    )
  }
}
