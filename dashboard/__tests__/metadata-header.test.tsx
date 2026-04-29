import React from 'react'
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'
import type { ScanGetResp } from '@/lib/types'

// next/link renders an <a> in jsdom
vi.mock('next/link', () => ({
  default: ({
    href,
    children,
    className,
  }: {
    href: string
    children: React.ReactNode
    className?: string
  }) => (
    <a href={href} className={className}>
      {children}
    </a>
  ),
}))

// lucide-react icons render as spans for testing
vi.mock('lucide-react', () => ({
  ArrowLeft: () => <span data-testid="icon-arrow-left" />,
  GitCompare: () => <span data-testid="icon-git-compare" />,
  Share2: () => <span data-testid="icon-share2" />,
}))

// Mock ShareButton stub so MetadataHeader tests don't pull console.info on click
vi.mock('@/components/scans/ShareButton', () => ({
  ShareButton: ({ scanId }: { scanId: string }) => (
    <button data-testid="share-button">{scanId}</button>
  ),
}))

// Mock CompareButton — its child (ScanPickerModal) uses useRouter from
// next/navigation, which has no provider in a bare jsdom render.
vi.mock('@/components/scans/CompareButton', () => ({
  CompareButton: ({ scanId }: { scanId: string }) => (
    <button data-testid="compare-button">{scanId}</button>
  ),
}))

const makeScanResp = (overrides: Partial<ScanGetResp> = {}): ScanGetResp => ({
  id: 'scan-001',
  team_id: 'team-001',
  status: 'ready',
  presigned_get_url: 'https://r2.example.com/presigned/scan-001.json?sig=abc',
  size_bytes: 2048,
  created_at: '2026-04-28T14:32:00Z',
  summary_json: {
    score: 87,
    findings: { critical: 3, high: 12, medium: 5, info: 2 },
    drift: {},
    total_resources: 42,
  },
  branch: 'main',
  commit_sha: 'a1b2c3d4e5f6abc',
  source: 'cli',
  ...overrides,
})

describe('MetadataHeader', () => {
  it('renders data-testid="metadata-header"', async () => {
    const { MetadataHeader } = await import('@/components/scans/MetadataHeader')
    render(<MetadataHeader scan={makeScanResp()} />)
    expect(screen.getByTestId('metadata-header')).toBeInTheDocument()
  })

  it('renders branch text', async () => {
    const { MetadataHeader } = await import('@/components/scans/MetadataHeader')
    render(<MetadataHeader scan={makeScanResp({ branch: 'main' })} />)
    expect(screen.getByText('main')).toBeInTheDocument()
  })

  it('renders 7-char abbreviated commit SHA with @ prefix', async () => {
    const { MetadataHeader } = await import('@/components/scans/MetadataHeader')
    render(<MetadataHeader scan={makeScanResp({ commit_sha: 'a1b2c3d4e5f6abc' })} />)
    // commit_sha.slice(0,7) = 'a1b2c3d'; rendered as "@" + "a1b2c3d" — accept either
    // a single combined node or two adjacent text nodes.
    const matches = screen.getAllByText((_, el) => {
      if (!el) return false
      // Match the leaf span that holds both "@" and the 7-char SHA
      return el.tagName === 'SPAN' && el.textContent === '@a1b2c3d'
    })
    expect(matches.length).toBeGreaterThan(0)
  })

  it('renders score number 87', async () => {
    const { MetadataHeader } = await import('@/components/scans/MetadataHeader')
    render(<MetadataHeader scan={makeScanResp()} />)
    expect(screen.getByText('87')).toBeInTheDocument()
  })

  it('renders score grade pill "B+" for score 87', async () => {
    const { MetadataHeader } = await import('@/components/scans/MetadataHeader')
    render(<MetadataHeader scan={makeScanResp({ summary_json: {
      score: 87,
      findings: { critical: 0, high: 0, medium: 0, info: 0 },
      drift: {},
      total_resources: 0,
    } })} />)
    expect(screen.getByText('B+')).toBeInTheDocument()
  })

  it('renders critical and high finding counts with data-testids', async () => {
    const { MetadataHeader } = await import('@/components/scans/MetadataHeader')
    render(<MetadataHeader scan={makeScanResp()} />)
    const crit = screen.getByTestId('header-critical-count')
    const high = screen.getByTestId('header-high-count')
    expect(crit).toHaveTextContent('3c')
    expect(high).toHaveTextContent('12h')
  })

  it('renders without errors when branch, commit_sha, summary_json are all null', async () => {
    const { MetadataHeader } = await import('@/components/scans/MetadataHeader')
    const scan = makeScanResp({ branch: null, commit_sha: null, summary_json: null })
    expect(() => render(<MetadataHeader scan={scan} />)).not.toThrow()
    expect(screen.getByTestId('metadata-header')).toBeInTheDocument()
  })
})

describe('fetchScanJson retry on 403', () => {
  it('calls onPresignedExpired and retries once when first fetch returns 403', async () => {
    const { fetchScanJson } = await import('@/lib/r2')
    const mockGraph = { nodes: [], edges: [], summary: {}, metadata: {} }
    const freshUrl = 'https://r2.example.com/fresh-url'
    const onExpired = vi.fn().mockResolvedValue(freshUrl)

    let callCount = 0
    global.fetch = vi.fn().mockImplementation(() => {
      callCount++
      if (callCount === 1) {
        return Promise.resolve({ status: 403, ok: false } as Response)
      }
      return Promise.resolve({
        status: 200,
        ok: true,
        json: () => Promise.resolve(mockGraph),
      } as Response)
    })

    const result = await fetchScanJson({
      presignedUrl: 'https://r2.example.com/expired-url',
      onPresignedExpired: onExpired,
    })

    expect(onExpired).toHaveBeenCalledTimes(1)
    expect(global.fetch).toHaveBeenCalledTimes(2)
    // Second call must use the fresh URL returned by onPresignedExpired
    const fetchMock = global.fetch as ReturnType<typeof vi.fn>
    expect(fetchMock.mock.calls[1][0]).toBe(freshUrl)
    expect(result).toEqual(mockGraph)
  })
})
