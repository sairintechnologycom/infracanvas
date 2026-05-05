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
  source: 'cli' | 'manual' | 'github_webhook' | 'webhook' | null
}

export interface ScanListResp {
  items: ScanListItem[]
  next_cursor: string | null
}

export interface ScanGetResp {
  id: string
  team_id: string
  status: string
  /**
   * R2 presigned GET URL for the scan JSON payload.
   *
   * Null when status != 'ready' (i.e. 'pending' or 'failed') because the
   * payload hasn't been written yet. Plan 11's polling page uses
   * null-vs-non-null as the "still working / show viewer" discriminant.
   */
  presigned_get_url: string | null
  size_bytes: number | null
  created_at: string
  summary_json: ScanListItem['summary_json']
  branch: string | null
  commit_sha: string | null
  source: string | null
  // ── Phase 7.5 extensions (Plan 05) ─────────────────────────────────────────
  /** Set on `failed` scans by worker (clone error, scan error, upload error). */
  error_message?: string | null
  /** Sub-path within the repo that was scanned (default '.'). */
  source_path?: string | null
  /** GitHub install id for github-source scans (D-10e). */
  github_installation_id?: number | null
  /** owner/name of the repo that was scanned. */
  github_repo?: string | null
  /** Branch that was scanned. */
  github_branch?: string | null
  /** Resolved HEAD sha at enqueue time. */
  github_sha?: string | null
}

// ── GitHub integration API response types (Phase 7.5 — Plan 04) ──────────────
// Mirrors backend/app/schemas/github.py — keep in sync.

/**
 * Response item for GET /v1/github/installations (D-10a).
 *
 * Sourced from the local `github_installations` table; no GitHub API call.
 */
export interface InstallationResp {
  installation_id: number
  github_account_login: string
  github_account_type: 'User' | 'Organization'
  installed_at: string
  installed_by_user_id: string
}

/** Response item for GET /v1/github/repos (D-10b). */
export interface RepoResp {
  full_name: string
  default_branch: string
  private: boolean
}

/** Response item for GET /v1/github/branches (D-10c). */
export interface BranchResp {
  name: string
  commit_sha: string
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
