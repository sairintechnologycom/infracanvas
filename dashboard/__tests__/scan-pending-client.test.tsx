import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, act, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom'

import type { ScanGetResp } from '@/lib/types'

// ── Mocks ────────────────────────────────────────────────────────────────────
const pushMock = vi.fn()
const refreshMock = vi.fn()
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: pushMock, replace: vi.fn(), refresh: refreshMock }),
}))

import { ScanPendingClient } from '@/components/scans/ScanPendingClient'

// Helper to build a baseline scan row.
const makeScan = (overrides: Partial<ScanGetResp> = {}): ScanGetResp => ({
  id: 'scan-abc',
  team_id: 'team-001',
  status: 'pending',
  presigned_get_url: null,
  size_bytes: null,
  created_at: '2026-05-04T22:00:00Z',
  summary_json: null,
  branch: null,
  commit_sha: null,
  source: 'github_webhook',
  error_message: null,
  source_path: '.',
  github_installation_id: 42,
  github_repo: 'acme/api',
  github_branch: 'main',
  github_sha: 'abc123',
  ...overrides,
})

// Async-fetch helper: returns a thenable Response shape.
const okJson = (body: unknown) => ({
  ok: true,
  status: 200,
  json: async () => body,
})

beforeEach(() => {
  pushMock.mockReset()
  refreshMock.mockReset()
})

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('ScanPendingClient', () => {
  it('renders skeleton + repo/branch header while pending (renders_pending_skeleton)', () => {
    const fetchMock = vi.fn().mockResolvedValue(okJson(makeScan()))
    vi.stubGlobal('fetch', fetchMock)

    render(<ScanPendingClient initialScan={makeScan()} />)
    // Skeleton placeholder visible
    expect(document.querySelector('[data-slot="skeleton"]')).not.toBeNull()
    // Repo + branch text rendered
    expect(screen.getByText(/acme\/api/)).toBeInTheDocument()
    expect(screen.getByText(/main/)).toBeInTheDocument()
    // "Scanning…" copy present
    expect(screen.getByText(/scanning/i)).toBeInTheDocument()
  })

  it('polls /api/scan-status every 2s while pending (polls_every_2s)', async () => {
    const fetchMock = vi.fn().mockResolvedValue(okJson(makeScan()))
    vi.stubGlobal('fetch', fetchMock)
    vi.useFakeTimers({ shouldAdvanceTime: true })

    render(<ScanPendingClient initialScan={makeScan()} />)

    // No fetch on mount — first tick fires after 2s.
    expect(fetchMock).not.toHaveBeenCalled()

    await act(async () => {
      vi.advanceTimersByTime(2000)
    })
    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(fetchMock.mock.calls[0][0]).toBe('/api/scan-status?id=scan-abc')

    await act(async () => {
      vi.advanceTimersByTime(2000)
    })
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('stops polling and calls router.refresh when status flips to ready (stops_polling_on_ready)', async () => {
    const ready = makeScan({ status: 'ready', presigned_get_url: 'https://r2/example' })
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(okJson(makeScan())) // tick 1: still pending
      .mockResolvedValueOnce(okJson(ready)) //         tick 2: ready
      .mockResolvedValue(okJson(ready)) //              should never reach here
    vi.stubGlobal('fetch', fetchMock)
    vi.useFakeTimers({ shouldAdvanceTime: true })

    render(<ScanPendingClient initialScan={makeScan()} />)

    await act(async () => {
      vi.advanceTimersByTime(2000)
    })
    await act(async () => {
      vi.advanceTimersByTime(2000)
    })
    // wait for the refresh to land
    await waitFor(() => expect(refreshMock).toHaveBeenCalled())

    // Advance another 4s — interval should have been cleared, no third fetch.
    const callsAfterReady = fetchMock.mock.calls.length
    await act(async () => {
      vi.advanceTimersByTime(4000)
    })
    expect(fetchMock.mock.calls.length).toBe(callsAfterReady)
  })

  it('stops polling and renders error_message + Retry on failed (stops_polling_on_failed)', async () => {
    const failed = makeScan({
      status: 'failed',
      error_message: 'clone_failed: branch not found',
    })
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(okJson(failed))
      .mockResolvedValue(okJson(failed))
    vi.stubGlobal('fetch', fetchMock)
    vi.useFakeTimers({ shouldAdvanceTime: true })

    render(<ScanPendingClient initialScan={makeScan()} />)

    await act(async () => {
      vi.advanceTimersByTime(2000)
    })
    // Error message + Retry button surface.
    await screen.findByText(/clone_failed: branch not found/)
    expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument()

    // Advance 4s — interval cleared.
    const callsAfterFailed = fetchMock.mock.calls.length
    await act(async () => {
      vi.advanceTimersByTime(4000)
    })
    expect(fetchMock.mock.calls.length).toBe(callsAfterFailed)
  })

  it('Retry button re-POSTs to /api/scans/from-github with derived params (retry_button_reposts)', async () => {
    const failed = makeScan({
      status: 'failed',
      error_message: 'scan_failed',
    })
    // Initial state already failed — no need to wait for a poll tick.
    const fetchMock = vi
      .fn()
      // First call (Retry POST)
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ scan_id: 'scan-xyz' }),
      })
    vi.stubGlobal('fetch', fetchMock)

    render(<ScanPendingClient initialScan={failed} />)
    fireEvent.click(screen.getByRole('button', { name: /retry/i }))

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalled()
    })
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/scans/from-github')
    expect(init.method).toBe('POST')
    const body = JSON.parse(init.body)
    expect(body).toEqual({
      installation_id: 42,
      repo: 'acme/api',
      branch: 'main',
      path: '.',
    })
    await waitFor(() => {
      expect(pushMock).toHaveBeenCalledWith('/scans/scan-xyz')
    })
  })

  it('clears interval on unmount (cleanup_on_unmount)', async () => {
    const fetchMock = vi.fn().mockResolvedValue(okJson(makeScan()))
    vi.stubGlobal('fetch', fetchMock)
    vi.useFakeTimers({ shouldAdvanceTime: true })

    const { unmount } = render(<ScanPendingClient initialScan={makeScan()} />)
    unmount()

    await act(async () => {
      vi.advanceTimersByTime(6000)
    })
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('does not start polling when initial status is ready (no_poll_when_initial_ready)', async () => {
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
    vi.useFakeTimers({ shouldAdvanceTime: true })

    const ready = makeScan({ status: 'ready', presigned_get_url: 'https://r2/example' })
    render(<ScanPendingClient initialScan={ready} />)

    // Advance well past 2s — no polling fetch should fire.
    await act(async () => {
      vi.advanceTimersByTime(6000)
    })
    expect(fetchMock).not.toHaveBeenCalled()
    // Should call router.refresh once so the parent RSC re-renders the viewer.
    expect(refreshMock).toHaveBeenCalled()
  })
})
