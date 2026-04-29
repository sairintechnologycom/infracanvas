import { NextRequest, NextResponse } from 'next/server'
import { backendFetch } from '@/lib/backend'
import type { ScanGetResp } from '@/lib/types'

/**
 * Route handler that re-fetches a fresh presigned R2 GET URL for a scan.
 *
 * Called by ScanViewerClient when fetchScanJson detects a 403 (presigned URL
 * TTL <=300s per D-12). backendFetch revalidates the Clerk JWT, so this is
 * NOT an auth bypass — unauthenticated requests fail in auth() before
 * backendFetch fires (T-07-07-06).
 *
 * Returns 404 (not 403) for cross-team scan IDs to avoid existence leaks (D-18).
 */
export async function GET(req: NextRequest) {
  const id = req.nextUrl.searchParams.get('id')
  if (!id) {
    return NextResponse.json({ error: 'Missing id' }, { status: 400 })
  }
  try {
    const scan = await backendFetch<ScanGetResp>(`/v1/scans/${id}`)
    return NextResponse.json({ presigned_get_url: scan.presigned_get_url })
  } catch (err) {
    const status = err instanceof Error && err.message === '404' ? 404 : 500
    return NextResponse.json(
      { error: status === 404 ? 'Not found' : 'Internal error' },
      { status },
    )
  }
}
