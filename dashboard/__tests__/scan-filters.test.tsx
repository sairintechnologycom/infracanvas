import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

const SOURCE = readFileSync(
  join(__dirname, '..', 'components', 'scans', 'ScanFilters.tsx'),
  'utf8',
)

const mockReplace = vi.fn()
const mockGet = vi.fn((_key: string) => null as string | null)

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: mockReplace }),
  useSearchParams: () => ({ get: mockGet, toString: () => '' }),
  usePathname: () => '/scans',
}))

describe('ScanFilters — shadcn Select + Custom range (RMD-01, RMD-06)', () => {
  it('source does NOT use a native <select> tag', () => {
    // Allow imports of `Select` (shadcn primitive). Only flag a bare lowercase HTML
    // <select> element opening (e.g. `<select ` or `<select>`).
    expect(SOURCE).not.toMatch(/<select[\s>]/)
  })

  it('imports shadcn Select primitives', () => {
    expect(SOURCE).toMatch(/from\s+['"]@\/components\/ui\/select['"]/)
  })

  it('imports Popover and Calendar for custom range', () => {
    expect(SOURCE).toMatch(/from\s+['"]@\/components\/ui\/popover['"]/)
    expect(SOURCE).toMatch(/from\s+['"]@\/components\/ui\/calendar['"]/)
  })

  it('declares "Custom range" option', () => {
    expect(SOURCE).toMatch(/Custom range/)
  })

  it('Calendar uses mode="range" with numberOfMonths={2}', () => {
    expect(SOURCE).toMatch(/mode=["']range["']/)
    expect(SOURCE).toMatch(/numberOfMonths=\{?2\}?/)
  })

  it('renders combobox-role triggers (shadcn SelectTrigger semantics)', async () => {
    const { ScanFilters } = await import('@/components/scans/ScanFilters')
    render(<ScanFilters />)
    // shadcn SelectTrigger renders as role="combobox" via Radix
    expect(screen.getAllByRole('combobox').length).toBeGreaterThanOrEqual(1)
  })
})
