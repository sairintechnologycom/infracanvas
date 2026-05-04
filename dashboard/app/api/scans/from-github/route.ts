import { NextRequest, NextResponse } from 'next/server'
import { backendFetch } from '@/lib/backend'

/**
 * Route handler proxy for POST /v1/scans/from-github (D-10e).
 *
 * Forwards the JSON body { installation_id, repo, branch, path } 1:1 to the
 * backend. Backend resolves HEAD sha, inserts a `pending` scans row, enqueues
 * the `scan_repo` taskiq job, and returns { scan_id }. Frontend then redirects
 * to /scans/{scan_id} and polls (Plan 11).
 *
 * Status mapping:
 *   - 422 (Pydantic validation): preserve so UI can show field errors
 *   - 503 (GitHub rate-limited / queue overload): preserve so UI can retry
 *   - 404 (installation not found / branch not found): preserve
 *   - everything else → 500
 */
export async function POST(req: NextRequest) {
  let body: unknown
  try {
    body = await req.json()
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 })
  }

  try {
    const data = await backendFetch<{ scan_id: string }>(
      '/v1/scans/from-github',
      { method: 'POST', body: JSON.stringify(body) },
    )
    return NextResponse.json(data)
  } catch (err) {
    const message = err instanceof Error ? err.message : '500'
    const status = ['404', '422', '503'].includes(message) ? Number(message) : 500
    return NextResponse.json({ error: 'request_failed' }, { status })
  }
}
