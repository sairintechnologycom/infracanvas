import { NextRequest, NextResponse } from 'next/server'
import { backendFetch } from '@/lib/backend'
import type { InstallationResp } from '@/lib/types'

/**
 * Route handler proxy for GET /v1/github/installations (D-10a).
 *
 * Used by client components on /settings/integrations (Plan 09) that cannot
 * import `lib/backend.ts` directly — that module pulls in
 * `@clerk/nextjs/server` which is server-only.
 *
 * Returns the installation list scoped to the caller's team via RLS.
 */
export async function GET(_req: NextRequest) {
  try {
    const data = await backendFetch<InstallationResp[]>(
      '/v1/github/installations',
    )
    return NextResponse.json(data)
  } catch (err) {
    const status = err instanceof Error && err.message === '404' ? 404 : 500
    return NextResponse.json(
      { error: status === 404 ? 'Not found' : 'Internal error' },
      { status },
    )
  }
}
