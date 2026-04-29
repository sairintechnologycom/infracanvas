import React from 'react'
import { describe, it, expect, vi } from 'vitest'
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

describe('ScoreCard.gradeInfo', () => {
  it('returns A+ for score >= 90', async () => {
    const { gradeInfo } = await import('@/components/home/ScoreCard')
    const r = gradeInfo(95)
    expect(r.grade).toBe('A+')
    expect(r.bgClass).toBe('bg-green-100')
    expect(r.textClass).toBe('text-green-700')
  })

  it('returns B+ for score 87', async () => {
    const { gradeInfo } = await import('@/components/home/ScoreCard')
    const r = gradeInfo(87)
    expect(r.grade).toBe('B+')
    expect(r.bgClass).toBe('bg-sky-100')
  })

  it('returns C for score 72', async () => {
    const { gradeInfo } = await import('@/components/home/ScoreCard')
    expect(gradeInfo(72).grade).toBe('C')
  })

  it('returns F for score 55', async () => {
    const { gradeInfo } = await import('@/components/home/ScoreCard')
    const r = gradeInfo(55)
    expect(r.grade).toBe('F')
    expect(r.bgClass).toBe('bg-red-100')
  })

  it('returns A for score 90', async () => {
    const { gradeInfo } = await import('@/components/home/ScoreCard')
    expect(gradeInfo(90).grade).toBe('A')
  })

  it('returns B for score 82', async () => {
    const { gradeInfo } = await import('@/components/home/ScoreCard')
    expect(gradeInfo(82).grade).toBe('B')
  })

  it('returns D for score 65', async () => {
    const { gradeInfo } = await import('@/components/home/ScoreCard')
    expect(gradeInfo(65).grade).toBe('D')
  })
})

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

describe('TopFindings component', () => {
  it('renders green pill when 0 critical findings', async () => {
    const { TopFindings } = await import('@/components/home/TopFindings')
    const scan = makeScan({
      summary_json: {
        score: 95,
        findings: { critical: 0, high: 0, medium: 0, info: 0 },
        drift: {},
        total_resources: 0,
      },
    })
    render(<TopFindings scan={scan} />)
    expect(screen.getByText(/0 critical findings — well done/i)).toBeInTheDocument()
  })

  it('renders critical count when findings exist', async () => {
    const { TopFindings } = await import('@/components/home/TopFindings')
    render(<TopFindings scan={makeScan()} />)
    // 3 critical from default fixture
    expect(screen.getByTestId('top-findings-critical-count')).toHaveTextContent('3')
  })

  it('renders Open scan link to scan detail', async () => {
    const { TopFindings } = await import('@/components/home/TopFindings')
    render(<TopFindings scan={makeScan({ id: 'scan-aaa' })} />)
    const link = screen.getByRole('link', { name: /open scan/i })
    expect(link).toHaveAttribute('href', '/scans/scan-aaa')
  })

  it('renders title "Top 3 critical findings"', async () => {
    const { TopFindings } = await import('@/components/home/TopFindings')
    render(<TopFindings scan={makeScan()} />)
    expect(screen.getByText('Top 3 critical findings')).toBeInTheDocument()
  })

  it('handles null summary_json without crashing', async () => {
    const { TopFindings } = await import('@/components/home/TopFindings')
    expect(() =>
      render(<TopFindings scan={makeScan({ summary_json: null })} />)
    ).not.toThrow()
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
