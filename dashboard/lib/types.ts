// Re-export shared types from the viewer package — no duplication
export type {
  ResourceGraph,
  GraphSummary,
  Finding,
  Severity,
  DriftStatus,
} from '@infracanvas/viewer'

// ── Scan API response types (mirror backend Pydantic schemas) ────────────────

export interface ScanListItem {
  id: string
  team_id: string
  status: 'pending' | 'ready' | 'failed'
  created_at: string
  size_bytes: number | null
  summary_json: {
    score: number
    findings: { critical: number; high: number; medium: number; info: number }
    drift: Record<string, number>
    total_resources: number
  } | null
  branch: string | null
  commit_sha: string | null
  source: 'cli' | 'manual' | 'github_webhook' | null
}

export interface ScanListResp {
  items: ScanListItem[]
  next_cursor: string | null
}

export interface ScanGetResp {
  id: string
  team_id: string
  status: string
  presigned_get_url: string
  size_bytes: number | null
  created_at: string
  summary_json: ScanListItem['summary_json']
  branch: string | null
  commit_sha: string | null
  source: string | null
}

// ── Compare API response types ────────────────────────────────────────────────

export interface ResourceDiff {
  added: Array<{ id: string; type: string; attributes: Record<string, unknown> }>
  removed: Array<{ id: string; type: string; attributes: Record<string, unknown> }>
  changed: Array<{
    id: string
    type: string
    attribute_deltas: Array<{ key: string; before: unknown; after: unknown }>
  }>
  findings_delta: { critical: number; high: number; medium: number; info: number }
}

// ── Share-link API response types ─────────────────────────────────────────────
// Mirrors backend/app/schemas/share.py — keep in sync.

export interface ShareLink {
  id: string
  expires_at: string | null
  created_by: string
  has_password: boolean
  created_at: string
}

/** Request body for POST /v1/scans/{scan_id}/share-links. */
export interface ShareCreateReq {
  password?: string | null
  expires_at?: string | null   // ISO datetime; null = never
}

/** 201 response from POST /v1/scans/{scan_id}/share-links. */
export interface ShareCreateResp {
  id: string
  token: string                // raw token — returned ONCE, never stored raw (D-08)
  share_url: string            // canonical URL — frontend may rebuild via NEXT_PUBLIC_DASHBOARD_URL
  expires_at: string | null
}

/**
 * Response from GET /v1/share-links/{token} (public, no auth).
 *
 * D-09 / D-15 zero-metadata gate: when has_password === true, scan_id,
 * presigned_get_url, branch, commit_sha, created_at, summary_json are ALL
 * absent. The dashboard PasswordGate must not display any pre-auth metadata.
 */
export interface ShareLandingResp {
  has_password: boolean
  scan_id?: string
  presigned_get_url?: string
  branch?: string | null
  commit_sha?: string | null
  created_at?: string
  summary_json?: ScanListItem['summary_json']
}

/** 200 response from POST /v1/share-links/{token}/unlock. */
export interface ShareVerifyResp {
  scan_id: string
  presigned_get_url: string
  branch?: string | null
  commit_sha?: string | null
  created_at?: string
  summary_json?: ScanListItem['summary_json']
}
