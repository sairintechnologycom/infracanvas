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

/**
 * Single per-node diff row in a ResourceDiff.nodes list.
 *
 * Mirrors backend `NodeDiff` in `backend/app/schemas/scan.py` (Plan 07-03 — D-11).
 *
 *  - kind='added'     → present in scan B but not A; before is null
 *  - kind='removed'   → present in scan A but not B; after is null
 *  - kind='changed'   → present in both, at least one attribute differs;
 *                       changed_fields lists the attribute keys that differ
 *  - kind='unchanged' → present in both, all attributes equal
 */
export interface NodeDiff {
  id: string
  kind: 'added' | 'removed' | 'changed' | 'unchanged'
  before: Record<string, unknown> | null
  after: Record<string, unknown> | null
  changed_fields: string[]
}

/**
 * Mirrors backend `ResourceDiffResp` (Plan 07-03 — D-11).
 *
 * Returned by GET /v1/scans/{a}/compare/{b}. `nodes` is capped at 5000 entries
 * upstream by `compute_diff` to keep response sizes bounded.
 */
export interface ResourceDiff {
  scan_a_id: string
  scan_b_id: string
  nodes: NodeDiff[]
  edges_added: Array<{ source: string; target: string; relationship: string }>
  edges_removed: Array<{ source: string; target: string; relationship: string }>
  summary: { added: number; removed: number; changed: number; unchanged: number }
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
