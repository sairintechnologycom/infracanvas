import { NextRequest, NextResponse } from 'next/server'
import { auth } from '@clerk/nextjs/server'
import { backendFetch } from '@/lib/backend'
import type { ShareCreateReq, ShareCreateResp, ShareLink } from '@/lib/types'

/**
 * Route handlers that proxy share-link operations to the FastAPI backend.
 *
 * The browser-side ShareModal / ShareLinksList components cannot call the
 * backend directly because `backendFetch` reads the Clerk JWT from `auth()`
 * which is a server-only helper. These handlers revalidate the JWT and
 * forward each request.
 *
 * D-08: raw token is returned ONCE on POST — never persisted on this server.
 * D-18: cross-team scan IDs surface as 404 (no existence oracle).
 */

/**
 * GET /api/scan-share?scan_id={id}
 *
 * Lists active (non-revoked, non-expired) share-links for the scan, scoped
 * by the caller's Clerk org → team RLS. Backs Plan 06's ShareLinksList
 * component.
 */
export async function GET(req: NextRequest) {
  const scanId = req.nextUrl.searchParams.get('scan_id')
  if (!scanId) {
    return NextResponse.json({ error: 'Missing scan_id' }, { status: 400 })
  }

  try {
    const resp = await backendFetch<{ links: ShareLink[] }>(
      `/v1/scans/${scanId}/share-links`,
      { method: 'GET' },
    )
    return NextResponse.json(resp, { status: 200 })
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

/**
 * POST /api/scan-share?scan_id={id}
 *
 * Creates a new share-link for the scan. Returns the raw token ONCE — the
 * caller must copy it immediately; it is never stored raw on the server.
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

/**
 * DELETE /api/scan-share?scan_id={id}&share_id={share_id}
 *
 * Revokes a share-link by setting revoked_at. Backend returns 204 No Content;
 * we mirror that here so the client can treat success as "no body".
 */
export async function DELETE(req: NextRequest) {
  const scanId = req.nextUrl.searchParams.get('scan_id')
  const shareId = req.nextUrl.searchParams.get('share_id')
  if (!scanId || !shareId) {
    return NextResponse.json(
      { error: 'Missing scan_id or share_id' },
      { status: 400 },
    )
  }

  // We bypass backendFetch here because it always calls res.json() on success,
  // which would throw on the backend's 204 empty body. Auth-token plumbing is
  // copied 1:1 from backendFetch so the security profile is identical.
  const { getToken } = await auth()
  const token = await getToken()
  const backendUrl = process.env.BACKEND_URL
  if (!backendUrl) {
    return NextResponse.json(
      { error: 'BACKEND_URL not configured' },
      { status: 500 },
    )
  }
  const res = await fetch(
    `${backendUrl}/v1/scans/${scanId}/share-links/${shareId}`,
    {
      method: 'DELETE',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      cache: 'no-store',
    },
  )
  if (res.status === 204) {
    return new NextResponse(null, { status: 204 })
  }
  if (res.status === 404) {
    return NextResponse.json({ error: 'Share link not found' }, { status: 404 })
  }
  return NextResponse.json({ error: 'Internal error' }, { status: 500 })
}
