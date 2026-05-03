import { NextResponse } from 'next/server'
import { isUUID } from '@/lib/utils'
import { backendFetch } from '@/lib/backend'
import { fetchScanJson } from '@/lib/r2'
import type { ScanGetResp } from '@/lib/types'

/**
 * GET /api/top-findings?scan_id={uuid}
 *
 * Returns up to 3 critical findings for the scan, mirroring the home-page
 * `TopFindings` card. The scan ResourceGraph attaches findings per-node, so
 * we walk node.findings[] and short-circuit at 3 to bound DoS surface.
 *
 * Returns 404 (not 403) for cross-team or unknown scan IDs to avoid existence
 * leaks (D-18). UUID-validated up-front via the same helper used by the
 * /scans/compare path (T-07-08-01 mitigation).
 */
export async function GET(req: Request) {
  const { searchParams } = new URL(req.url)
  const scanId = searchParams.get('scan_id')

  if (!isUUID(scanId ?? undefined)) {
    return NextResponse.json({ error: 'invalid scan_id' }, { status: 400 })
  }

  let scanMeta: ScanGetResp
  try {
    scanMeta = await backendFetch<ScanGetResp>(`/v1/scans/${scanId}`)
  } catch (err) {
    const status = err instanceof Error && err.message === '404' ? 404 : 500
    return NextResponse.json(
      { error: status === 404 ? 'scan not found' : 'internal error' },
      { status },
    )
  }

  if (!scanMeta.presigned_get_url) {
    return NextResponse.json({ error: 'scan not ready' }, { status: 404 })
  }

  const graph = await fetchScanJson({
    presignedUrl: scanMeta.presigned_get_url,
    onPresignedExpired: async () => {
      const refreshed = await backendFetch<ScanGetResp>(`/v1/scans/${scanId}`)
      return refreshed.presigned_get_url ?? ''
    },
  })

  const findings: Array<{ rule_id: string; title: string; resource_id: string }> = []
  outer: for (const node of graph.nodes ?? []) {
    for (const f of node.findings ?? []) {
      if (f.severity === 'critical') {
        findings.push({ rule_id: f.rule_id, title: f.title, resource_id: node.id })
        if (findings.length >= 3) break outer
      }
    }
  }

  return NextResponse.json({ findings })
}
