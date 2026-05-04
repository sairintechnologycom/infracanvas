import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'

import type { ScanGetResp } from '@/lib/types'

// ── Mocks ────────────────────────────────────────────────────────────────────
// The mocks here let us assert which client component the page picks
// without dragging in @clerk/nextjs/server (which the real page module
// would import via @/lib/backend in an RSC context).

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn() }),
  notFound: vi.fn(() => {
    throw new Error('NEXT_NOT_FOUND')
  }),
}))

vi.mock('@/components/scans/ScanPendingClient', () => ({
  ScanPendingClient: ({ initialScan }: { initialScan: ScanGetResp }) => (
    <div data-testid="scan-pending-mock">pending-mock:{initialScan.status}</div>
  ),
}))

vi.mock('@/components/scans/ScanViewerClient', () => ({
  ScanViewerClient: ({
    scanId,
    initialPresignedUrl,
  }: {
    scanId: string
    initialPresignedUrl: string
  }) => (
    <div data-testid="scan-viewer-mock">
      viewer-mock:{scanId}:{initialPresignedUrl}
    </div>
  ),
}))

// MetadataHeader + ScanDetailActions render in the ready branch and are
// out of scope for this gate test — stub to keep DOM minimal.
vi.mock('@/components/scans/MetadataHeader', () => ({
  MetadataHeader: () => <div data-testid="metadata-header-mock" />,
}))

vi.mock(
  '@/app/(dashboard)/scans/[id]/ScanDetailActions',
  () => ({
    ScanDetailActions: () => <div data-testid="scan-detail-actions-mock" />,
  }),
  { virtual: true } as never,
)

import { renderScanByStatus } from '@/app/(dashboard)/scans/[id]/page'

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

beforeEach(() => {
  vi.clearAllMocks()
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('scan-detail page status gate', () => {
  it('status_pending_renders_pending_client', () => {
    const scan = makeScan({ status: 'pending' })
    render(<>{renderScanByStatus(scan)}</>)
    expect(screen.getByTestId('scan-pending-mock')).toBeInTheDocument()
    expect(screen.queryByTestId('scan-viewer-mock')).not.toBeInTheDocument()
  })

  it('status_failed_renders_pending_client', () => {
    const scan = makeScan({
      status: 'failed',
      error_message: 'clone_failed',
    })
    render(<>{renderScanByStatus(scan)}</>)
    expect(screen.getByTestId('scan-pending-mock')).toBeInTheDocument()
    expect(screen.queryByTestId('scan-viewer-mock')).not.toBeInTheDocument()
  })

  it('status_ready_renders_viewer', () => {
    const scan = makeScan({
      status: 'ready',
      presigned_get_url: 'https://r2.example/scan-abc.json',
    })
    render(<>{renderScanByStatus(scan)}</>)
    expect(screen.getByTestId('scan-viewer-mock')).toBeInTheDocument()
    expect(screen.queryByTestId('scan-pending-mock')).not.toBeInTheDocument()
  })

  it('status_ready_without_presigned_url_falls_back_to_pending_client', () => {
    // Defensive — Plan 05's invariant ties presigned_get_url to status==='ready',
    // but if the backend ever ships a ready row without a URL we render the
    // pending client (which surfaces "Loading scan…") instead of crashing
    // ScanViewerClient with a null prop.
    const scan = makeScan({ status: 'ready', presigned_get_url: null })
    render(<>{renderScanByStatus(scan)}</>)
    expect(screen.getByTestId('scan-pending-mock')).toBeInTheDocument()
  })
})
