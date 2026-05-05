import { NextResponse } from 'next/server'
import { backendFetch } from '@/lib/backend'

/**
 * PATCH /api/integrations/slack — proxy to backend PATCH /v1/integrations/slack.
 *
 * Forwards { webhook_url } to the backend which validates the URL prefix
 * and saves to teams.slack_webhook_url (Phase 8 WBH-03).
 *
 * Status mapping mirrors from-github/route.ts:
 *   422 (invalid URL) → preserve
 *   401 (unauthenticated) → preserve
 *   everything else → 500
 */
export async function PATCH(req: Request) {
  let body: unknown
  try {
    body = await req.json()
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 })
  }

  try {
    const data = await backendFetch<{ message: string }>(
      '/v1/integrations/slack',
      { method: 'PATCH', body: JSON.stringify(body) },
    )
    return NextResponse.json(data)
  } catch (err) {
    const message = err instanceof Error ? err.message : '500'
    const httpStatus = ['401', '422'].includes(message) ? Number(message) : 500
    return NextResponse.json({ error: 'request_failed' }, { status: httpStatus })
  }
}
