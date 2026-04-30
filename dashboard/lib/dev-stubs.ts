/**
 * Synthesized backend responses for DEV_BYPASS_AUTH=1 mode.
 * Returns realistic-looking data so the UI shells can render without a live API.
 */

const STUB_SCANS = [
  {
    id: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1',
    team_id: 'team-1',
    status: 'ready' as const,
    created_at: '2026-04-29T08:30:00Z',
    size_bytes: 12345,
    summary_json: {
      score: 87,
      findings: { critical: 1, high: 2, medium: 4, info: 5 },
      drift: { added: 2, removed: 0, changed: 1 },
      total_resources: 47,
    },
    branch: 'main',
    commit_sha: 'a1b2c3d4e5f6789',
    source: 'cli' as const,
  },
  {
    id: 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb2',
    team_id: 'team-1',
    status: 'ready' as const,
    created_at: '2026-04-28T16:12:00Z',
    size_bytes: 11234,
    summary_json: {
      score: 92,
      findings: { critical: 0, high: 1, medium: 3, info: 7 },
      drift: { added: 0, removed: 1, changed: 0 },
      total_resources: 45,
    },
    branch: 'main',
    commit_sha: '9f8e7d6c5b4a321',
    source: 'github_webhook' as const,
  },
  {
    id: 'cccccccc-cccc-cccc-cccc-ccccccccccc3',
    team_id: 'team-1',
    status: 'ready' as const,
    created_at: '2026-04-27T11:05:00Z',
    size_bytes: 10500,
    summary_json: {
      score: 75,
      findings: { critical: 2, high: 5, medium: 8, info: 12 },
      drift: { added: 4, removed: 2, changed: 3 },
      total_resources: 50,
    },
    branch: 'feature/network-acl',
    commit_sha: 'deadbeefcafe123',
    source: 'manual' as const,
  },
]

export async function devStub<T>(path: string, _init?: RequestInit): Promise<T> {
  // GET /v1/scans
  if (path.startsWith('/v1/scans?') || path === '/v1/scans') {
    return { items: STUB_SCANS, next_cursor: null } as T
  }
  // GET /v1/scans/{id}
  const scanGetMatch = path.match(/^\/v1\/scans\/([0-9a-f-]+)$/)
  if (scanGetMatch) {
    const scan = STUB_SCANS.find((s) => s.id === scanGetMatch[1]) ?? STUB_SCANS[0]
    return {
      ...scan,
      r2_key: `scans/${scan.id}.json`,
      presigned_get_url: `/api/dev-stub-scan-json?id=${scan.id}`,
      presigned_expires_at: new Date(Date.now() + 5 * 60 * 1000).toISOString(),
    } as T
  }
  // GET /v1/scans/{a}/compare/{b}
  const compareMatch = path.match(/^\/v1\/scans\/([0-9a-f-]+)\/compare\/([0-9a-f-]+)$/)
  if (compareMatch) {
    return {
      scan_a_id: compareMatch[1],
      scan_b_id: compareMatch[2],
      summary: { added: 2, removed: 1, changed: 3, unchanged: 41 },
      edges_added: [],
      edges_removed: [],
      nodes: [
        {
          id: 'aws_security_group.web',
          kind: 'changed',
          type: 'aws_security_group',
          changed_fields: ['ingress.cidr_blocks', 'tags.Owner'],
        },
        { id: 'aws_s3_bucket.logs', kind: 'added',   type: 'aws_s3_bucket' },
        { id: 'aws_iam_role.legacy', kind: 'removed', type: 'aws_iam_role' },
      ],
    } as T
  }
  // POST /v1/scans/{id}/share-links — create
  if (path.match(/^\/v1\/scans\/[0-9a-f-]+\/share-links$/)) {
    return {
      id: 'share-stub-1',
      token: 'stub-token-aaaa1111',
      url: 'http://localhost:3001/share/stub-token-aaaa1111',
      expires_at: null,
    } as T
  }
  // GET /v1/share-links/{token}
  const shareGetMatch = path.match(/^\/v1\/share-links\/([^/]+)$/)
  if (shareGetMatch) {
    return {
      scan_id: STUB_SCANS[0].id,
      requires_password: false,
      presigned_get_url: `/api/dev-stub-scan-json?id=${STUB_SCANS[0].id}`,
      summary_json: STUB_SCANS[0].summary_json,
      branch: STUB_SCANS[0].branch,
      commit_sha: STUB_SCANS[0].commit_sha,
      created_at: STUB_SCANS[0].created_at,
    } as T
  }
  console.warn(`[dev-stub] Unhandled path: ${path} — returning empty object`)
  return {} as T
}
