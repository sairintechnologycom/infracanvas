import { NextRequest, NextResponse } from 'next/server'
import { backendFetch } from '@/lib/backend'
import type { RepoResp } from '@/lib/types'

/**
 * Route handler proxy for GET /v1/github/repos (D-10b).
 *
 * Forwards `installation_id` and optional `q` query params 1:1 to the backend.
 * Backend caches results for 60s in Upstash Redis keyed by (installation_id, q).
 *
 * Special-cases 503 (GitHub rate-limited) so the UI can show a Retry-After
 * countdown rather than a generic Internal Error toast.
 */
export async function GET(req: NextRequest) {
  const qs = req.nextUrl.searchParams.toString()
  try {
    const data = await backendFetch<RepoResp[]>(
      `/v1/github/repos${qs ? `?${qs}` : ''}`,
    )
    return NextResponse.json(data)
  } catch (err) {
    const isRateLimit = err instanceof Error && err.message === '503'
    if (isRateLimit) {
      return NextResponse.json(
        { error: 'github_rate_limited' },
        { status: 503, headers: { 'Retry-After': '60' } },
      )
    }
    const status = err instanceof Error && err.message === '404' ? 404 : 500
    return NextResponse.json(
      { error: status === 404 ? 'Not found' : 'Internal error' },
      { status },
    )
  }
}
