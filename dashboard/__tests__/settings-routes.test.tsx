import React from 'react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import '@testing-library/jest-dom'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

const SETTINGS_LAYOUT_SOURCE = readFileSync(
  join(__dirname, '..', 'app', '(dashboard)', 'settings', 'layout.tsx'),
  'utf8',
)

// Mock next/link → plain anchor
// Mock next/link → forward all props (incl. ref) so Radix Tabs `asChild`
// `Slot` can attach role/data-state attributes to the underlying anchor.
vi.mock('next/link', () => ({
  default: React.forwardRef<HTMLAnchorElement, React.AnchorHTMLAttributes<HTMLAnchorElement>>(
    function Link({ children, ...rest }, ref) {
      return (
        <a ref={ref} {...rest}>
          {children}
        </a>
      )
    },
  ),
}))

// Mock next/navigation pathname (Settings layout uses usePathname for active tab)
const mockPathname = vi.fn(() => '/settings/members')
vi.mock('next/navigation', () => ({
  usePathname: () => mockPathname(),
  useRouter: () => ({ push: vi.fn() }),
  // Phase 7.5 Plan 09 — integrations page reads ?install=success.
  useSearchParams: () => new URLSearchParams(''),
}))

// Phase 7.5 Plan 09 — integrations page now composes child components that
// require Clerk + fetch. Mock both so this layout-level test stays focused.
vi.mock('@/components/integrations/InstallButton', () => ({
  InstallButton: () => <button data-testid="install-button-stub">Install</button>,
}))
vi.mock('@/components/integrations/ScanTriggerForm', () => ({
  ScanTriggerForm: () => <div data-testid="scan-trigger-form-stub" />,
}))

// Mock Clerk OrganizationProfile — lightweight stand-in
vi.mock('@clerk/nextjs', () => ({
  OrganizationProfile: () => <div data-testid="org-profile">Clerk OrganizationProfile</div>,
}))

// Mock lucide-react icons → spans
vi.mock('lucide-react', () => ({
  MessageSquare: () => <span data-testid="icon-slack" />,
  Github: () => <span data-testid="icon-github" />,
}))

describe('settings/members page', () => {
  it('renders Clerk OrganizationProfile', async () => {
    const { default: MembersPage } = await import(
      '@/app/(dashboard)/settings/members/page'
    )
    render(<MembersPage />)
    expect(screen.getByTestId('org-profile')).toBeInTheDocument()
  })
})

describe('settings/billing page', () => {
  it('renders Open billing portal CTA', async () => {
    const { default: BillingPage } = await import(
      '@/app/(dashboard)/settings/billing/page'
    )
    render(<BillingPage />)
    const btn = screen.getByTestId('billing-portal-btn')
    expect(btn).toHaveTextContent(/open billing portal/i)
  })

  it('clicking Open billing portal does not crash (stub)', async () => {
    const { default: BillingPage } = await import(
      '@/app/(dashboard)/settings/billing/page'
    )
    // Suppress alert / log noise
    const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {})
    render(<BillingPage />)
    const btn = screen.getByTestId('billing-portal-btn')
    expect(() => fireEvent.click(btn)).not.toThrow()
    alertSpy.mockRestore()
  })

  it('renders heading "Billing & invoices"', async () => {
    const { default: BillingPage } = await import(
      '@/app/(dashboard)/settings/billing/page'
    )
    render(<BillingPage />)
    expect(screen.getByText(/billing & invoices/i)).toBeInTheDocument()
  })
})

describe('settings/integrations page', () => {
  beforeEach(() => {
    // Stub fetch so the page's mount-time GET /api/github/installations
    // resolves predictably (empty list → InstallButton path).
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => [],
      }),
    )
  })
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders Slack and GitHub cards (live state machine — Plan 07.5-09)', async () => {
    const { default: IntegrationsPage } = await import(
      '@/app/(dashboard)/settings/integrations/page'
    )
    render(<IntegrationsPage />)
    expect(screen.getByRole('heading', { name: /slack/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /github/i })).toBeInTheDocument()
  })

  it('renders Slack webhook input and Save button (preserved)', async () => {
    const { default: IntegrationsPage } = await import(
      '@/app/(dashboard)/settings/integrations/page'
    )
    render(<IntegrationsPage />)
    const input = screen.getByPlaceholderText(/hooks\.slack\.com/i)
    expect(input).toBeInTheDocument()
    expect(screen.getByText(/save webhook url/i)).toBeInTheDocument()
  })
})

describe('settings layout', () => {
  it('renders three tab links to Members / Billing / Integrations', async () => {
    const { default: SettingsLayout } = await import(
      '@/app/(dashboard)/settings/layout'
    )
    render(
      <SettingsLayout>
        <div data-testid="layout-children">child</div>
      </SettingsLayout>,
    )
    // Note: Radix Tabs `asChild` propagates role="tab" onto the anchor,
    // overriding its implicit `link` role. Query by anchor tag instead.
    const anchors = Array.from(
      document.querySelectorAll<HTMLAnchorElement>('a[href^="/settings/"]'),
    )
    const hrefs = anchors.map(a => a.getAttribute('href'))
    expect(hrefs).toContain('/settings/members')
    expect(hrefs).toContain('/settings/billing')
    expect(hrefs).toContain('/settings/integrations')
  })

  it('marks the Members tab active when pathname starts with /settings/members', async () => {
    mockPathname.mockReturnValue('/settings/members')
    const { default: SettingsLayout } = await import(
      '@/app/(dashboard)/settings/layout'
    )
    const { container } = render(
      <SettingsLayout>
        <div />
      </SettingsLayout>,
    )
    // Under shadcn Tabs the active TabsTrigger gets data-state="active"
    // (Radix Tabs primitive). The asChild Link inside it is the descendant.
    const activeTrigger = container.querySelector('[data-state="active"]')
    expect(activeTrigger).not.toBeNull()
    expect(activeTrigger?.textContent).toMatch(/members/i)
  })

  it('renders children below the tab strip', async () => {
    const { default: SettingsLayout } = await import(
      '@/app/(dashboard)/settings/layout'
    )
    render(
      <SettingsLayout>
        <div data-testid="layout-children">child content</div>
      </SettingsLayout>,
    )
    expect(screen.getByTestId('layout-children')).toBeInTheDocument()
  })
})

describe('SettingsLayout — shadcn Tabs migration (RMD-01)', () => {
  it('imports Tabs from @/components/ui/tabs', () => {
    expect(SETTINGS_LAYOUT_SOURCE).toMatch(
      /from\s+['"]@\/components\/ui\/tabs['"]/,
    )
  })

  it('uses <Tabs> wrapper element', () => {
    expect(SETTINGS_LAYOUT_SOURCE).toMatch(/<Tabs\b/)
  })

  it('declares TabsTrigger value="members" / "billing" / "integrations"', () => {
    // Accept either inline JSX (`value="members"`) or object-property form
    // (`value: 'members'`) — both encode the required tab identifier.
    expect(SETTINGS_LAYOUT_SOURCE).toMatch(/value\s*[:=]\s*["']members["']/)
    expect(SETTINGS_LAYOUT_SOURCE).toMatch(/value\s*[:=]\s*["']billing["']/)
    expect(SETTINGS_LAYOUT_SOURCE).toMatch(/value\s*[:=]\s*["']integrations["']/)
  })

  it('does not introduce off-scale headings (no text-xl / text-lg)', () => {
    expect(SETTINGS_LAYOUT_SOURCE).not.toMatch(/text-(xl|lg)/)
  })

  it('renders a tablist with 3 role=tab children at runtime', async () => {
    mockPathname.mockReturnValue('/settings/members')
    const { default: SettingsLayout } = await import(
      '@/app/(dashboard)/settings/layout'
    )
    const { container } = render(
      <SettingsLayout>
        <div />
      </SettingsLayout>,
    )
    const tablist = container.querySelector('[role="tablist"]')
    expect(tablist).not.toBeNull()
    const tabs = container.querySelectorAll('[role="tab"]')
    expect(tabs.length).toBe(3)
  })
})
