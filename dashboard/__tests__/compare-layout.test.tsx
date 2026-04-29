import React from 'react'
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'
import type { NodeDiff, ResourceDiff } from '@/lib/types'

// next/link → <a> in jsdom
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

// lucide-react → bare spans
vi.mock('lucide-react', () => ({
  ArrowLeft: () => <span data-testid="icon-arrow-left" />,
  ArrowLeftRight: () => <span data-testid="icon-arrow-leftright" />,
  ArrowRight: () => <span data-testid="icon-arrow-right" />,
  GitCompare: () => <span data-testid="icon-git-compare" />,
  Share2: () => <span data-testid="icon-share2" />,
}))

const fixtureSummary = { added: 3, removed: 5, changed: 7, unchanged: 12 }

const fixtureNodes: NodeDiff[] = [
  {
    id: 'aws_s3_bucket.added_one',
    kind: 'added',
    before: null,
    after: { id: 'aws_s3_bucket.added_one', acl: 'private' },
    changed_fields: [],
  },
  {
    id: 'aws_s3_bucket.removed_one',
    kind: 'removed',
    before: { id: 'aws_s3_bucket.removed_one', acl: 'public-read' },
    after: null,
    changed_fields: [],
  },
  {
    id: 'aws_security_group.changed_one',
    kind: 'changed',
    before: { id: 'aws_security_group.changed_one', cidr_blocks: '0.0.0.0/0' },
    after: { id: 'aws_security_group.changed_one', cidr_blocks: '10.0.0.0/8' },
    changed_fields: ['cidr_blocks'],
  },
  {
    id: 'aws_iam_role.unchanged_one',
    kind: 'unchanged',
    before: { id: 'aws_iam_role.unchanged_one' },
    after: { id: 'aws_iam_role.unchanged_one' },
    changed_fields: [],
  },
]

describe('isUUID validator', () => {
  it('rejects undefined', async () => {
    const { isUUID } = await import('@/lib/utils')
    expect(isUUID(undefined)).toBe(false)
  })

  it('rejects empty string', async () => {
    const { isUUID } = await import('@/lib/utils')
    expect(isUUID('')).toBe(false)
  })

  it('rejects non-uuid strings', async () => {
    const { isUUID } = await import('@/lib/utils')
    expect(isUUID('not-a-uuid')).toBe(false)
    expect(isUUID('123')).toBe(false)
    expect(isUUID('123e4567e89b12d3a456426614174000')).toBe(false) // missing dashes
  })

  it('accepts a canonical UUID', async () => {
    const { isUUID } = await import('@/lib/utils')
    expect(isUUID('123e4567-e89b-12d3-a456-426614174000')).toBe(true)
  })

  it('accepts uppercase UUIDs', async () => {
    const { isUUID } = await import('@/lib/utils')
    expect(isUUID('123E4567-E89B-12D3-A456-426614174000')).toBe(true)
  })
})

describe('DiffSummary', () => {
  it('renders the data-testid wrapper', async () => {
    const { DiffSummary } = await import('@/components/compare/DiffSummary')
    render(<DiffSummary summary={fixtureSummary} />)
    expect(screen.getByTestId('diff-summary')).toBeInTheDocument()
  })

  it('renders +N added with green text class', async () => {
    const { DiffSummary } = await import('@/components/compare/DiffSummary')
    const { container } = render(<DiffSummary summary={fixtureSummary} />)
    const added = container.querySelector('[data-testid="chip-added"]')
    expect(added).toBeTruthy()
    expect(added).toHaveTextContent('+3 added')
    expect(added?.className).toMatch(/text-green/)
    expect(added?.className).not.toMatch(/text-red/)
    expect(added?.className).not.toMatch(/text-amber/)
  })

  it('renders −N removed with red text class', async () => {
    const { DiffSummary } = await import('@/components/compare/DiffSummary')
    const { container } = render(<DiffSummary summary={fixtureSummary} />)
    const removed = container.querySelector('[data-testid="chip-removed"]')
    expect(removed).toBeTruthy()
    expect(removed).toHaveTextContent('−5 removed')
    expect(removed?.className).toMatch(/text-red/)
  })

  it('renders ~N changed with amber text class', async () => {
    const { DiffSummary } = await import('@/components/compare/DiffSummary')
    const { container } = render(<DiffSummary summary={fixtureSummary} />)
    const changed = container.querySelector('[data-testid="chip-changed"]')
    expect(changed).toBeTruthy()
    expect(changed).toHaveTextContent('~7 changed')
    expect(changed?.className).toMatch(/text-amber/)
  })
})

describe('DiffNodeList', () => {
  it('renders the data-testid wrapper', async () => {
    const { DiffNodeList } = await import('@/components/compare/DiffNodeList')
    render(<DiffNodeList nodes={fixtureNodes} />)
    expect(screen.getByTestId('diff-node-list')).toBeInTheDocument()
  })

  it('renders one row per non-unchanged node', async () => {
    const { DiffNodeList } = await import('@/components/compare/DiffNodeList')
    const { container } = render(<DiffNodeList nodes={fixtureNodes} />)
    const rows = container.querySelectorAll('[data-testid="diff-node-row"]')
    // 4 fixture nodes — 1 unchanged (filtered out) → 3 rows
    expect(rows.length).toBe(3)
  })

  it('row with kind=added has bg-green class', async () => {
    const { DiffNodeList } = await import('@/components/compare/DiffNodeList')
    const { container } = render(<DiffNodeList nodes={fixtureNodes} />)
    const row = container.querySelector('[data-kind="added"]')
    expect(row?.className).toMatch(/bg-green/)
  })

  it('row with kind=removed has bg-red class', async () => {
    const { DiffNodeList } = await import('@/components/compare/DiffNodeList')
    const { container } = render(<DiffNodeList nodes={fixtureNodes} />)
    const row = container.querySelector('[data-kind="removed"]')
    expect(row?.className).toMatch(/bg-red/)
  })

  it('row with kind=changed has bg-amber class', async () => {
    const { DiffNodeList } = await import('@/components/compare/DiffNodeList')
    const { container } = render(<DiffNodeList nodes={fixtureNodes} />)
    const row = container.querySelector('[data-kind="changed"]')
    expect(row?.className).toMatch(/bg-amber/)
  })

  it('renders the resource id in each row', async () => {
    const { DiffNodeList } = await import('@/components/compare/DiffNodeList')
    render(<DiffNodeList nodes={fixtureNodes} />)
    expect(screen.getByText('aws_s3_bucket.added_one')).toBeInTheDocument()
    expect(screen.getByText('aws_s3_bucket.removed_one')).toBeInTheDocument()
    expect(screen.getByText('aws_security_group.changed_one')).toBeInTheDocument()
  })

  it('does NOT render unchanged nodes', async () => {
    const { DiffNodeList } = await import('@/components/compare/DiffNodeList')
    render(<DiffNodeList nodes={fixtureNodes} />)
    expect(screen.queryByText('aws_iam_role.unchanged_one')).not.toBeInTheDocument()
  })

  it('renders nothing harmful with an empty nodes array', async () => {
    const { DiffNodeList } = await import('@/components/compare/DiffNodeList')
    expect(() => render(<DiffNodeList nodes={[]} />)).not.toThrow()
    expect(screen.getByTestId('diff-node-list')).toBeInTheDocument()
  })

  it('renders changed-attrs count in changed row label', async () => {
    const { DiffNodeList } = await import('@/components/compare/DiffNodeList')
    const { container } = render(<DiffNodeList nodes={fixtureNodes} />)
    const changedRow = container.querySelector('[data-kind="changed"]')
    expect(changedRow?.textContent).toMatch(/1.*attr/)
  })

  it('invokes onSelect with node id when row is clicked', async () => {
    const { DiffNodeList } = await import('@/components/compare/DiffNodeList')
    const onSelect = vi.fn()
    const { container } = render(<DiffNodeList nodes={fixtureNodes} onSelect={onSelect} />)
    const addedRow = container.querySelector('[data-kind="added"]') as HTMLElement
    addedRow.click()
    expect(onSelect).toHaveBeenCalledWith('aws_s3_bucket.added_one')
  })
})

// ── ComparePage RSC tests — invoke the async server component as a function ──
// next/navigation is mocked at module-level; backendFetch is mocked per-test.

vi.mock('@/lib/backend', () => ({
  backendFetch: vi.fn(),
}))

// CompareLayout & CompareViewerPair are heavy client components that depend on
// browser APIs (window, useRouter, ViewerProvider). Stub them out to keep RSC
// tests focused on validation + 404 paths.
vi.mock('@/components/compare/CompareLayout', () => ({
  CompareLayout: ({ scanAId, scanBId }: { scanAId: string; scanBId: string }) => (
    <div data-testid="compare-layout-stub">
      {scanAId} → {scanBId}
    </div>
  ),
}))

describe('ComparePage RSC validation', () => {
  it('renders 400 message when a is missing without calling backendFetch', async () => {
    const { backendFetch } = await import('@/lib/backend')
    const ComparePage = (await import('@/app/(dashboard)/scans/compare/page')).default
    const ui = await ComparePage({ searchParams: Promise.resolve({ b: '123e4567-e89b-12d3-a456-426614174000' }) })
    render(ui as React.ReactElement)
    expect(screen.getByTestId('error-400')).toBeInTheDocument()
    expect(screen.getByText(/Invalid compare URL/)).toBeInTheDocument()
    expect(backendFetch).not.toHaveBeenCalled()
  })

  it('renders 400 message when both UUIDs are invalid without calling backendFetch', async () => {
    const { backendFetch } = await import('@/lib/backend')
    ;(backendFetch as ReturnType<typeof vi.fn>).mockClear()
    const ComparePage = (await import('@/app/(dashboard)/scans/compare/page')).default
    const ui = await ComparePage({ searchParams: Promise.resolve({ a: 'bad', b: 'also-bad' }) })
    render(ui as React.ReactElement)
    expect(screen.getByTestId('error-400')).toBeInTheDocument()
    expect(backendFetch).not.toHaveBeenCalled()
  })

  it('renders 404 card when backend returns 404', async () => {
    const { backendFetch } = await import('@/lib/backend')
    ;(backendFetch as ReturnType<typeof vi.fn>).mockReset()
    ;(backendFetch as ReturnType<typeof vi.fn>).mockRejectedValueOnce(new Error('404'))
    const ComparePage = (await import('@/app/(dashboard)/scans/compare/page')).default
    const a = '11111111-1111-1111-1111-111111111111'
    const b = '22222222-2222-2222-2222-222222222222'
    const ui = await ComparePage({ searchParams: Promise.resolve({ a, b }) })
    render(ui as React.ReactElement)
    expect(screen.getByText(/Scan not found/)).toBeInTheDocument()
  })

  it('renders CompareLayout on success', async () => {
    const { backendFetch } = await import('@/lib/backend')
    ;(backendFetch as ReturnType<typeof vi.fn>).mockReset()
    const a = '11111111-1111-1111-1111-111111111111'
    const b = '22222222-2222-2222-2222-222222222222'
    const diff: ResourceDiff = {
      scan_a_id: a,
      scan_b_id: b,
      nodes: fixtureNodes,
      edges_added: [],
      edges_removed: [],
      summary: fixtureSummary,
    }
    ;(backendFetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(diff)
    const ComparePage = (await import('@/app/(dashboard)/scans/compare/page')).default
    const ui = await ComparePage({ searchParams: Promise.resolve({ a, b }) })
    render(ui as React.ReactElement)
    expect(screen.getByTestId('compare-layout-stub')).toBeInTheDocument()
    expect(backendFetch).toHaveBeenCalledWith(`/v1/scans/${a}/compare/${b}`)
  })
})
