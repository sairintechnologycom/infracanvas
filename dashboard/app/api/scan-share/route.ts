import { NextRequest, NextResponse } from 'next/server'
import { backendFetch } from '@/lib/backend'
import type { ShareCreateReq, ShareCreateResp } from '@/lib/types'

/**
 * Route handler that proxies share-link creation to the FastAPI backend.
 *
 * The browser-side ShareModal cannot call the backend directly because
 * `backendFetch` reads the Clerk JWT from `auth()` which is a server-only
 * helper. This route revalidates the JWT and forwards the POST.
 *
 * D-08: raw token is returned ONCE — never persisted on this server.
 */
export async function POST(req: NextRequest) {
  const url = new URL(req.url)
  const scanId = url.searchParams.get('scan_id')
  if (!scanId) {
    return NextResponse.json({ error: 'Missing scan_id' }, { status: 400 })
  }

  let body: ShareCreateReq
  try {
    body = (await req.json()) as ShareCreateReq
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 })
  }

  try {
    const resp = await backendFetch<ShareCreateResp>(
      `/v1/scans/${scanId}/share-links`,
      {
        method: 'POST',
        body: JSON.stringify(body),
      },
    )
    return NextResponse.json(resp, { status: 201 })
  } catch (err) {
    const status = err instanceof Error && /^4\d\d$/.test(err.message)
      ? Number(err.message)
      : 500
    return NextResponse.json(
      { error: status === 404 ? 'Scan not found' : 'Internal error' },
      { status },
    )
  }
}
