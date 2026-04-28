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

export interface ShareLink {
  id: string
  expires_at: string | null
  created_by: string
  has_password: boolean
  created_at: string
}

export interface ShareLinkCreateResp {
  id: string
  token: string  // raw token — returned ONCE, never stored raw on frontend
  url: string
  expires_at: string | null
}

export interface ShareLandingResp {
  password_required: true
}

export interface ShareLandingUnlockedResp {
  password_required: false
  team_name: string
  scan: ScanGetResp
}
