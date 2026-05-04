import { NextRequest, NextResponse } from 'next/server'
import { backendFetch } from '@/lib/backend'
import type { BranchResp } from '@/lib/types'

/**
 * Route handler proxy for GET /v1/github/branches (D-10c).
 *
 * Forwards `installation_id` and `repo` query params 1:1 to the backend.
 * No cache (branches change frequently and are usually <30 per repo).
 */
export async function GET(req: NextRequest) {
  const qs = req.nextUrl.searchParams.toString()
  try {
    const data = await backendFetch<BranchResp[]>(
      `/v1/github/branches${qs ? `?${qs}` : ''}`,
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
