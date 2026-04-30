import { NextRequest, NextResponse } from 'next/server'
import { backendFetch } from '@/lib/backend'
import type { ScanListResp } from '@/lib/types'

/**
 * Route handler proxy for GET /v1/scans.
 *
 * Used by client components (e.g. ScanPickerModal) that cannot import
 * `lib/backend.ts` directly — that module pulls in `@clerk/nextjs/server`
 * which is server-only.
 */
export async function GET(req: NextRequest) {
  const qs = req.nextUrl.searchParams.toString()
  try {
    const data = await backendFetch<ScanListResp>(
      `/v1/scans${qs ? `?${qs}` : ''}`,
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
