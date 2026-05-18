/**
 * Phase 12 FMV-02 — Blocker 3 closure.
 *
 * Fetches asymmetry findings from the InfraCanvas backend read API
 * (GET /v1/sites/{siteId}/asymmetries — Plan 12-03) and returns them as
 * AsymmetryPayload[] for the viewer store to hydrate onto NetworkPath
 * objects (see store.setAsymmetries).
 *
 * Auth boundary: the viewer is bundled as a standalone HTML asset and
 * cannot import `@clerk/nextjs/server` directly. The dashboard wrapper
 * (dashboard/lib/backend.ts:backendFetch) installs an injectable on
 * `window.__INFRACANVAS_BACKEND_FETCH__` at viewer-mount time (see
 * dashboard/components/viewer/ViewerBootstrap.tsx); this module uses
 * the installed callable when present. When absent (offline scans /
 * standalone bundle), it returns [] — the viewer continues to render
 * the FlowMap without asymmetry data.
 *
 * Never logs the Authorization header (T-12-07-07 mitigation). This
 * module only deals with the JSON response body; auth header attachment
 * happens inside the injected callable.
 */
import type { AsymmetryPayload } from '../types'

// AsymmetryFindingResponse — wire-format from Plan 12-03 GET /asymmetries.
interface AsymmetryFindingResponseWire {
  finding_id: string
  site_id: string
  forward_path_id: string
  return_path_id: string
  cause: string
  cause_confidence: number
  evidence?: Record<string, unknown>
  impact_bytes_per_sec: number
  impact_firewall_count: number
  first_seen_at: string
  last_seen_at: string
  resolved_at: string | null
}

type BackendFetch = <T>(path: string, init?: RequestInit) => Promise<T>

function getInjectableFetch(): BackendFetch | null {
  if (typeof window === 'undefined') return null
  const f = (window as unknown as { __INFRACANVAS_BACKEND_FETCH__?: BackendFetch })
    .__INFRACANVAS_BACKEND_FETCH__
  return typeof f === 'function' ? f : null
}

export async function fetchAsymmetries(siteId: string): Promise<AsymmetryPayload[]> {
  const fetchFn = getInjectableFetch()
  if (!fetchFn) {
    // Offline / standalone bundle — backend not reachable. Return empty list.
    return []
  }
  try {
    const wire = await fetchFn<AsymmetryFindingResponseWire[]>(
      `/v1/sites/${encodeURIComponent(siteId)}/asymmetries`,
    )
    return wire.map((w) => ({
      finding_id: w.finding_id,
      cause: w.cause,
      cause_confidence: w.cause_confidence,
      impact_bytes_per_sec: w.impact_bytes_per_sec,
      impact_firewall_count: w.impact_firewall_count,
      evidence: w.evidence,
      forward_path_id: w.forward_path_id,
      return_path_id: w.return_path_id,
    }))
  } catch {
    // Defensive — network or auth error. Return empty list so the viewer
    // continues to render the graph without the Asymmetry tab.
    return []
  }
}
