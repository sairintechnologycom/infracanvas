import { describe, it, expect, vi, beforeEach } from 'vitest'

// Mock the backend + R2 helpers BEFORE importing the route module.
vi.mock('@/lib/backend', () => ({
  backendFetch: vi.fn(),
}))
vi.mock('@/lib/r2', () => ({
  fetchScanJson: vi.fn(),
}))

import { GET } from './route'
import { backendFetch } from '@/lib/backend'
import { fetchScanJson } from '@/lib/r2'

const VALID_SCAN_ID = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'

const mockBackendFetch = vi.mocked(backendFetch)
const mockFetchScanJson = vi.mocked(fetchScanJson)

function makeNode(id: string, criticalTitles: string[]) {
  return {
    id,
    type: 'aws_s3_bucket',
    name: id,
    provider: 'aws',
    module: '',
    region: 'us-east-1',
    group: '',
    attributes: {},
    dependencies: [],
    findings: criticalTitles.map((t, i) => ({
      rule_id: `SEC-00${i + 1}`,
      severity: 'critical' as const,
      title: t,
      description: '',
      remediation: '',
      evidence: {},
    })),
    cost: { monthly_usd: 0, currency: 'USD', basis: 'storage' },
    drift: 'unchanged' as const,
    position: { x: 0, y: 0 },
  }
}

describe('GET /api/top-findings', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('returns 400 when scan_id missing', async () => {
    const req = new Request('http://localhost/api/top-findings')
    const res = await GET(req)
    expect(res.status).toBe(400)
  })

  it('returns 400 when scan_id is not a valid UUID', async () => {
    const req = new Request('http://localhost/api/top-findings?scan_id=../../etc/passwd')
    const res = await GET(req)
    expect(res.status).toBe(400)
  })

  it('returns 404 when backend returns 404', async () => {
    mockBackendFetch.mockRejectedValueOnce(new Error('404'))
    const req = new Request(`http://localhost/api/top-findings?scan_id=${VALID_SCAN_ID}`)
    const res = await GET(req)
    expect(res.status).toBe(404)
  })

  it('returns top 3 critical findings when scan has 5', async () => {
    mockBackendFetch.mockResolvedValueOnce({
      id: VALID_SCAN_ID,
      team_id: 't1',
      status: 'complete',
      presigned_get_url: 'https://r2.example/scan.json',
      size_bytes: 100,
    })
    mockFetchScanJson.mockResolvedValueOnce({
      nodes: [
        makeNode('aws_s3_bucket.a', ['Bucket A public', 'Bucket A logging off']),
        makeNode('aws_s3_bucket.b', ['Bucket B public', 'Bucket B versioning off']),
        makeNode('aws_s3_bucket.c', ['Bucket C public']),
      ],
      edges: [],
      summary: {},
      metadata: {},
    } as unknown as Parameters<typeof fetchScanJson>[0] extends never ? never : Awaited<ReturnType<typeof fetchScanJson>>)
    const req = new Request(`http://localhost/api/top-findings?scan_id=${VALID_SCAN_ID}`)
    const res = await GET(req)
    expect(res.status).toBe(200)
    const body = await res.json()
    expect(body.findings).toHaveLength(3)
    expect(body.findings[0]).toEqual({
      rule_id: 'SEC-001',
      title: 'Bucket A public',
      resource_id: 'aws_s3_bucket.a',
    })
  })

  it('returns empty array when scan has no critical findings', async () => {
    mockBackendFetch.mockResolvedValueOnce({
      id: VALID_SCAN_ID,
      team_id: 't1',
      status: 'complete',
      presigned_get_url: 'https://r2.example/scan.json',
      size_bytes: 100,
    })
    mockFetchScanJson.mockResolvedValueOnce({
      nodes: [makeNode('aws_s3_bucket.a', [])],
      edges: [],
      summary: {},
      metadata: {},
    } as never)
    const req = new Request(`http://localhost/api/top-findings?scan_id=${VALID_SCAN_ID}`)
    const res = await GET(req)
    expect(res.status).toBe(200)
    const body = await res.json()
    expect(body.findings).toEqual([])
  })
})
