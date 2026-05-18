import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { fetchAsymmetries } from '../../lib/asymmetryFetcher'
import { useStore } from '../../store'
import type { NetworkPath, ResourceGraph } from '../../types'

// Phase 12 FMV-02 — Blocker 3 closure verification.
//
// 1) Offline (no injectable installed) → fetcher returns [] and never throws.
// 2) With a mocked window.__INFRACANVAS_BACKEND_FETCH__, wire-format response
//    is mapped into AsymmetryPayload[] with forward_path_id preserved.
// 3) store.setAsymmetries attaches the payload onto a matching selectedPath
//    (selectedPath.asymmetry becomes populated).
// 4) store.setAsymmetries is a no-op when no path id matches.

type WindowWithInjectable = Window & typeof globalThis & {
  __INFRACANVAS_BACKEND_FETCH__?: <T>(path: string, init?: RequestInit) => Promise<T>
}

describe('asymmetryFetcher (Blocker 3 closure)', () => {
  beforeEach(() => {
    delete (window as WindowWithInjectable).__INFRACANVAS_BACKEND_FETCH__
    // Reset store between tests so setAsymmetries tests start from a clean slate.
    useStore.setState({ graph: null, selectedPath: null })
  })
  afterEach(() => {
    delete (window as WindowWithInjectable).__INFRACANVAS_BACKEND_FETCH__
  })

  it('returns empty array when window.__INFRACANVAS_BACKEND_FETCH__ is not installed (offline mode)', async () => {
    const result = await fetchAsymmetries('site-abc')
    expect(result).toEqual([])
  })

  it('maps wire-format response to AsymmetryPayload[] with forward_path_id preserved', async () => {
    const mockFetch = vi.fn().mockResolvedValue([
      {
        finding_id: 'f1',
        site_id: 'site-abc',
        forward_path_id: 'p-fwd-1',
        return_path_id: 'p-ret-1',
        cause: 'NAT_ASYMMETRY',
        cause_confidence: 0.7,
        evidence: { reason: 'symmetric NAT mismatch' },
        impact_bytes_per_sec: 12345,
        impact_firewall_count: 2,
        first_seen_at: '2026-05-17T00:00:00Z',
        last_seen_at: '2026-05-17T00:15:00Z',
        resolved_at: null,
      },
    ])
    ;(window as WindowWithInjectable).__INFRACANVAS_BACKEND_FETCH__ = mockFetch
    const result = await fetchAsymmetries('site-abc')
    expect(mockFetch).toHaveBeenCalledWith('/v1/sites/site-abc/asymmetries')
    expect(result).toHaveLength(1)
    expect(result[0].finding_id).toBe('f1')
    expect(result[0].forward_path_id).toBe('p-fwd-1')
    expect(result[0].return_path_id).toBe('p-ret-1')
    expect(result[0].cause).toBe('NAT_ASYMMETRY')
    expect(result[0].cause_confidence).toBeCloseTo(0.7)
    expect(result[0].impact_firewall_count).toBe(2)
  })

  it('returns [] on fetch failure (network or auth error) — never throws', async () => {
    const mockFetch = vi.fn().mockRejectedValue(new Error('500'))
    ;(window as WindowWithInjectable).__INFRACANVAS_BACKEND_FETCH__ = mockFetch
    const result = await fetchAsymmetries('site-abc')
    expect(result).toEqual([])
  })

  it('setAsymmetries store action populates selectedPath.asymmetry when forward_path_id matches', () => {
    // Seed store with a graph containing one network_path + matching selectedPath
    const seedPath: NetworkPath = {
      id: 'p-fwd-1',
      source_node_id: 'src',
      dest_node_id: 'dst',
      direction: 'forward',
      hops: [],
      evidence: {},
    }
    useStore.setState({
      graph: { network_paths: [seedPath] } as unknown as ResourceGraph,
      selectedPath: seedPath,
    })
    useStore.getState().setAsymmetries([
      {
        finding_id: 'f1',
        cause: 'NAT_ASYMMETRY',
        cause_confidence: 0.7,
        impact_bytes_per_sec: 12345,
        impact_firewall_count: 2,
        forward_path_id: 'p-fwd-1',
        return_path_id: 'p-ret-1',
      },
    ])
    const after = useStore.getState().selectedPath
    expect(after?.asymmetry).toBeDefined()
    expect(after?.asymmetry?.cause).toBe('NAT_ASYMMETRY')
    expect(after?.asymmetry?.finding_id).toBe('f1')

    // graph.network_paths[0] should also have the asymmetry attached.
    const graphAfter = useStore.getState().graph
    expect(graphAfter?.network_paths?.[0]?.asymmetry?.finding_id).toBe('f1')
  })

  it('setAsymmetries is a no-op when there are no matching paths', () => {
    const otherPath: NetworkPath = {
      id: 'other-path',
      source_node_id: 'src',
      dest_node_id: 'dst',
      direction: 'forward',
      hops: [],
      evidence: {},
    }
    useStore.setState({
      graph: { network_paths: [otherPath] } as unknown as ResourceGraph,
      selectedPath: null,
    })
    useStore.getState().setAsymmetries([
      {
        finding_id: 'f1',
        cause: 'NAT_ASYMMETRY',
        cause_confidence: 0.7,
        impact_bytes_per_sec: 0,
        impact_firewall_count: 0,
        forward_path_id: 'nonexistent-path',
      },
    ])
    const after = useStore.getState().graph
    expect(after?.network_paths?.[0]?.asymmetry).toBeUndefined()
  })
})
