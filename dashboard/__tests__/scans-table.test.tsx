import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, act } from '@testing-library/react'
import '@testing-library/jest-dom'
import type { ScanListItem, ScanListResp } from '@/lib/types'

const mockPush = vi.fn()
const mockReplace = vi.fn()
const mockGet = vi.fn((_key: string) => null as string | null)

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush, replace: mockReplace }),
  useSearchParams: () => ({ get: mockGet, toString: () => '' }),
  usePathname: () => '/scans',
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
    drift: {},
    total_resources: 42,
  },
  branch: 'main',
  commit_sha: 'a1b2c3d4e5f6',
  source: 'cli',
  ...overrides,
})

describe('SeverityBadge', () => {
  it('renders zero count with text-slate-400 class', async () => {
    const { SeverityBadge } = await import('@/components/scans/SeverityBadge')
    const { container } = render(<SeverityBadge severity="critical" count={0} />)
    const el = container.querySelector('[data-testid="severity-badge-critical"]')
    expect(el).toHaveTextContent('0')
    expect(el?.className).toContain('text-slate-400')
  })

  it('renders non-zero critical count without slate-400 class', async () => {
    const { SeverityBadge } = await import('@/components/scans/SeverityBadge')
    const { container } = render(<SeverityBadge severity="critical" count={3} />)
    const el = container.querySelector('[data-testid="severity-badge-critical"]')
    expect(el).toHaveTextContent('3')
    expect(el?.className).not.toContain('text-slate-400')
  })
})

describe('ScansTable', () => {
  it('renders empty state (no scans, no filters)', async () => {
    const { ScansTable } = await import('@/components/scans/ScansTable')
    const empty: ScanListResp = { items: [], next_cursor: null }
    render(<ScansTable data={empty} currentParams={{}} />)
    expect(screen.getByText('No scans yet')).toBeInTheDocument()
  })

  it('renders filtered-empty state with clear-filters link', async () => {
    const { ScansTable } = await import('@/components/scans/ScansTable')
    const empty: ScanListResp = { items: [], next_cursor: null }
    render(<ScansTable data={empty} currentParams={{ branch: 'main' }} />)
    expect(screen.getByText('No scans match your filters')).toBeInTheDocument()
    expect(screen.getByText('Clear all filters')).toBeInTheDocument()
  })

  it('renders scans-table with one scan row', async () => {
    const { ScansTable } = await import('@/components/scans/ScansTable')
    const data: ScanListResp = { items: [makeScan()], next_cursor: null }
    render(<ScansTable data={data} currentParams={{}} />)
    expect(screen.getByTestId('scans-table')).toBeInTheDocument()
    expect(screen.getAllByTestId('scan-row')).toHaveLength(1)
  })

  it('navigates to /scans/{id} on row click', async () => {
    const { ScansTable } = await import('@/components/scans/ScansTable')
    mockPush.mockClear()
    const data: ScanListResp = { items: [makeScan({ id: 'scan-abc' })], next_cursor: null }
    render(<ScansTable data={data} currentParams={{}} />)
    fireEvent.click(screen.getByTestId('scan-row'))
    expect(mockPush).toHaveBeenCalledWith('/scans/scan-abc')
  })
})

describe('ScanFilters debounce', () => {
  beforeEach(() => {
    mockReplace.mockClear()
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  it(
    'branch input waits 300ms before calling router.replace',
    async () => {
      const { ScanFilters } = await import('@/components/scans/ScanFilters')
      render(<ScanFilters />)
      // Switch to fake timers AFTER render so Radix Select's layout effects
      // (which depend on the real microtask queue) finish first.
      vi.useFakeTimers({ shouldAdvanceTime: true })
      const input = screen.getByTestId('branch-filter')
      fireEvent.change(input, { target: { value: 'feat/my-branch' } })
      expect(mockReplace).not.toHaveBeenCalled()
      await act(async () => {
        vi.advanceTimersByTime(300)
      })
      expect(mockReplace).toHaveBeenCalledWith(expect.stringContaining('branch=feat'))
    },
    // 3× Radix Select render under jsdom takes ~3-5s; allow headroom.
    15000,
  )
})
