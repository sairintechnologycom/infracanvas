import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Sidebar } from '@/components/layout/Sidebar'
import { TopBar } from '@/components/layout/TopBar'

// jsdom does not apply Tailwind CSS — responsive tests verify CLASS NAMES are present
// in the DOM, not that the CSS rules fire. Visual/CSS verification is done manually
// at 1440 / 1080 / 768 viewport widths.

vi.mock('next/navigation', () => ({
  usePathname: () => '/scans',
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}))

vi.mock('@clerk/nextjs', () => ({
  ClerkProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  OrganizationSwitcher: () => <div data-testid="org-switcher" />,
  UserButton: () => <div data-testid="user-button" />,
}))

describe('Sidebar responsive classes', () => {
  it('has xl:w-[220px] class (full width at 1440p)', () => {
    render(<Sidebar mobileOpen={false} />)
    const sidebar = screen.getByTestId('sidebar')
    expect(sidebar.className).toMatch(/xl:w-\[220px\]/)
  })

  it('has w-12 class (icon-only at <xl)', () => {
    render(<Sidebar mobileOpen={false} />)
    const sidebar = screen.getByTestId('sidebar')
    expect(sidebar.className).toMatch(/\bw-12\b/)
  })

  it('has hidden md:flex classes (hidden at <768px, visible above)', () => {
    render(<Sidebar mobileOpen={false} />)
    const sidebar = screen.getByTestId('sidebar')
    expect(sidebar.className).toMatch(/\bhidden\b/)
    expect(sidebar.className).toMatch(/md:flex/)
  })

  it('is visible when mobileOpen=true (overrides hidden at <md)', () => {
    render(<Sidebar mobileOpen={true} />)
    const sidebar = screen.getByTestId('sidebar')
    expect(sidebar.className).toMatch(/\bflex\b/)
  })
})

describe('TopBar hamburger', () => {
  it('renders hamburger button', () => {
    render(<TopBar onMenuToggle={vi.fn()} />)
    expect(screen.getByTestId('hamburger-button')).toBeDefined()
  })

  it('hamburger button is md:hidden (hidden above 768px via class)', () => {
    render(<TopBar onMenuToggle={vi.fn()} />)
    const btn = screen.getByTestId('hamburger-button')
    expect(btn.className).toMatch(/md:hidden/)
  })

  it('calls onMenuToggle when hamburger clicked', () => {
    const toggle = vi.fn()
    render(<TopBar onMenuToggle={toggle} />)
    screen.getByTestId('hamburger-button').click()
    expect(toggle).toHaveBeenCalledTimes(1)
  })
})

describe('ScansTable Source column visibility', () => {
  it('Source column th has hidden lg:table-cell class', async () => {
    const { ScansTable } = await import('@/components/scans/ScansTable')
    render(<ScansTable data={{ items: [], next_cursor: null }} currentParams={{}} />)
    // Empty state renders a placeholder, not a table — verify the class is present in source
    // by rendering with one stub item.
    const stubItem = {
      id: '00000000-0000-0000-0000-000000000001',
      team_id: '00000000-0000-0000-0000-000000000010',
      status: 'ready' as const,
      created_at: '2026-04-29T00:00:00.000Z',
      size_bytes: 0,
      summary_json: null,
      branch: 'main',
      commit_sha: 'abc1234',
      source: 'cli' as const,
    }
    const { container } = render(
      <ScansTable
        data={{ items: [stubItem], next_cursor: null }}
        currentParams={{}}
      />,
    )
    const headers = container.querySelectorAll('th')
    const sourceHeader = Array.from(headers).find(
      (th) => th.textContent?.trim() === 'Source',
    )
    expect(sourceHeader).toBeDefined()
    expect(sourceHeader!.className).toMatch(/hidden/)
    expect(sourceHeader!.className).toMatch(/lg:table-cell/)
  })
})
