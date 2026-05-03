import React from 'react'
import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'
import type { ScanListItem } from '@/lib/types'

// next/link renders a plain <a> in jsdom
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

// next/navigation hooks for client components
const mockPush = vi.fn()
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
  usePathname: () => '/',
}))

const makeScan = (overrides: Partial<ScanListItem> = {}): ScanListItem => ({
  id: 'scan-001',
  team_id: 'team-001',
  status: 'ready',
  created_at: '2026-04-28T14:32:00Z',
  size_bytes: 1024,
  summary_json: {
    score: 87,
    findings: { critical: 3, high: 12, medium: 5, info: 2 },
    drift: { added: 1, removed: 0, changed: 2 },
    total_resources: 42,
  },
  branch: 'main',
  commit_sha: 'a1b2c3d4e5f6',
  source: 'cli',
  ...overrides,
})

// gradeInfo() boundary tests are now in dashboard/lib/grade.test.ts (D-05).
// ScoreCard.tsx no longer exports a local gradeInfo — pill styling stays inline,
// the canonical letter source is @/lib/grade.

describe('ScoreCard component', () => {
  it('renders score number, grade, and finding counts', async () => {
    const { ScoreCard } = await import('@/components/home/ScoreCard')
    render(<ScoreCard scan={makeScan()} />)
    expect(screen.getByText('87')).toBeInTheDocument()
    expect(screen.getByText('B+')).toBeInTheDocument()
    expect(screen.getByTestId('score-card-critical')).toHaveTextContent('3')
    expect(screen.getByTestId('score-card-high')).toHaveTextContent('12')
  })

  it('renders Open scan link to /scans/{id}', async () => {
    const { ScoreCard } = await import('@/components/home/ScoreCard')
    render(<ScoreCard scan={makeScan({ id: 'scan-xyz' })} />)
    const link = screen.getByRole('link', { name: /open scan/i })
    expect(link).toHaveAttribute('href', '/scans/scan-xyz')
  })

  it('renders branch@commit metadata', async () => {
    const { ScoreCard } = await import('@/components/home/ScoreCard')
    render(<ScoreCard scan={makeScan()} />)
    // commit_sha truncated to 7 chars
    expect(screen.getByText(/main/)).toBeInTheDocument()
    expect(screen.getByText(/a1b2c3d/)).toBeInTheDocument()
  })

  it('handles null summary_json gracefully', async () => {
    const { ScoreCard } = await import('@/components/home/ScoreCard')
    expect(() =>
      render(<ScoreCard scan={makeScan({ summary_json: null })} />)
    ).not.toThrow()
  })
})

describe('ScoreSparkline component', () => {
  it('renders title "Score over last 10 scans"', async () => {
    const { ScoreSparkline } = await import('@/components/home/ScoreSparkline')
    render(<ScoreSparkline scans={[makeScan(), makeScan({ id: 'scan-002' })]} />)
    expect(screen.getByText('Score over last 10 scans')).toBeInTheDocument()
  })

  it('renders without crashing on empty scans', async () => {
    const { ScoreSparkline } = await import('@/components/home/ScoreSparkline')
    expect(() => render(<ScoreSparkline scans={[]} />)).not.toThrow()
  })

  it('skips scans with null summary_json when extracting scores', async () => {
    const { ScoreSparkline } = await import('@/components/home/ScoreSparkline')
    const scans = [
      makeScan({ id: 'a' }),
      makeScan({ id: 'b', summary_json: null }),
      makeScan({ id: 'c' }),
    ]
    expect(() => render(<ScoreSparkline scans={scans} />)).not.toThrow()
  })
})

describe('TopFindings component (D-07: card-based render via /api/top-findings)', () => {
  // The new TopFindings fetches /api/top-findings on mount and renders cards.
  // Tests mock global.fetch and await render+resolution.
  const realFetch = global.fetch

  function mockFetch(body: { findings: Array<{ rule_id: string; title: string; resource_id: string }> }) {
    global.fetch = vi.fn(async () =>
      new Response(JSON.stringify(body), { status: 200, headers: { 'Content-Type': 'application/json' } }),
    ) as typeof global.fetch
  }

  afterEach(() => {
    global.fetch = realFetch
    vi.restoreAllMocks()
  })

  it('renders empty-state line when 0 critical findings', async () => {
    mockFetch({ findings: [] })
    const { TopFindings } = await import('@/components/home/TopFindings')
    render(<TopFindings scan={makeScan()} />)
    expect(await screen.findByText(/No critical findings — nice work\./i)).toBeInTheDocument()
  })

  it('renders 3 cards when findings exist', async () => {
    mockFetch({
      findings: [
        { rule_id: 'SEC-001', title: 'Bucket public', resource_id: 'aws_s3_bucket.a' },
        { rule_id: 'SEC-002', title: 'Bucket logging off', resource_id: 'aws_s3_bucket.b' },
        { rule_id: 'SEC-003', title: 'Bucket versioning off', resource_id: 'aws_s3_bucket.c' },
      ],
    })
    const { TopFindings } = await import('@/components/home/TopFindings')
    render(<TopFindings scan={makeScan()} />)
    const cards = await screen.findAllByTestId('top-finding-card')
    expect(cards).toHaveLength(3)
    expect(screen.getByText('Bucket public')).toBeInTheDocument()
  })

  it('renders Open scan link inside each card', async () => {
    mockFetch({
      findings: [{ rule_id: 'SEC-001', title: 'Bucket public', resource_id: 'aws_s3_bucket.a' }],
    })
    const { TopFindings } = await import('@/components/home/TopFindings')
    render(<TopFindings scan={makeScan({ id: 'scan-aaa' })} />)
    const link = await screen.findByRole('link', { name: /open scan/i })
    expect(link).toHaveAttribute('href', '/scans/scan-aaa')
  })

  it('renders title "Top 3 critical findings"', async () => {
    mockFetch({ findings: [] })
    const { TopFindings } = await import('@/components/home/TopFindings')
    render(<TopFindings scan={makeScan()} />)
    expect(screen.getByText('Top 3 critical findings')).toBeInTheDocument()
  })

  it('handles fetch error without crashing', async () => {
    global.fetch = vi.fn(async () =>
      new Response('boom', { status: 500 }),
    ) as typeof global.fetch
    const { TopFindings } = await import('@/components/home/TopFindings')
    expect(() => render(<TopFindings scan={makeScan()} />)).not.toThrow()
    expect(await screen.findByText(/Couldn.t load critical findings/i)).toBeInTheDocument()
  })
})

describe('RecentScansTable component', () => {
  it('renders title bar with View all link', async () => {
    const { RecentScansTable } = await import('@/components/home/RecentScansTable')
    render(<RecentScansTable scans={[makeScan()]} />)
    expect(screen.getByText('Recent scans')).toBeInTheDocument()
    const viewAll = screen.getByRole('link', { name: /view all/i })
    expect(viewAll).toHaveAttribute('href', '/scans')
  })

  it('caps at 5 rows even when more scans provided', async () => {
    const { RecentScansTable } = await import('@/components/home/RecentScansTable')
    const scans = Array.from({ length: 8 }, (_, i) =>
      makeScan({ id: `scan-${i}` }),
    )
    render(<RecentScansTable scans={scans} />)
    expect(screen.getAllByTestId('recent-scan-row')).toHaveLength(5)
  })

  it('renders empty body gracefully when scans is empty', async () => {
    const { RecentScansTable } = await import('@/components/home/RecentScansTable')
    expect(() => render(<RecentScansTable scans={[]} />)).not.toThrow()
  })

  it('renders Date / Branch / Score / Crit / High columns', async () => {
    const { RecentScansTable } = await import('@/components/home/RecentScansTable')
    render(<RecentScansTable scans={[makeScan()]} />)
    expect(screen.getByText('Date')).toBeInTheDocument()
    expect(screen.getByText('Branch')).toBeInTheDocument()
    expect(screen.getByText('Score')).toBeInTheDocument()
    expect(screen.getByText('Crit')).toBeInTheDocument()
    expect(screen.getByText('High')).toBeInTheDocument()
  })
})
