import React from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, cleanup } from '@testing-library/react'
import '@testing-library/jest-dom'

// lucide-react icons render as inert spans — keep tests deterministic.
vi.mock('lucide-react', () => ({
  Menu: () => <span data-testid="icon-menu" />,
}))

// Default mock for next/navigation; tests override per-case via vi.doMock + dynamic import.
let MOCK_PATH = '/'
vi.mock('next/navigation', () => ({
  usePathname: () => MOCK_PATH,
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn() }),
}))

async function renderAt(pathname: string) {
  MOCK_PATH = pathname
  const { TopBar } = await import('@/components/layout/TopBar')
  const { TopBarActionsProvider } = await import('@/components/layout/TopBarActions')
  return render(
    <TopBarActionsProvider>
      <TopBar onMenuToggle={() => {}} />
    </TopBarActionsProvider>,
  )
}

beforeEach(() => {
  cleanup()
})

describe('TopBar breadcrumb — RMD-06 fix', () => {
  it("renders 'Scans' on /scans", async () => {
    await renderAt('/scans')
    expect(screen.getByText('Scans')).toBeInTheDocument()
  })

  it('does NOT render raw UUID for /scans/<uuid>', async () => {
    await renderAt('/scans/0a1b2c3d-4e5f-6789-abcd-ef0123456789')
    const uuidRe = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
    const all = screen.queryAllByText(uuidRe)
    expect(all).toHaveLength(0)
    // 'Scans' crumb still rendered
    expect(screen.getByText('Scans')).toBeInTheDocument()
  })

  it('renders sentence-case static labels for /settings/billing', async () => {
    await renderAt('/settings/billing')
    expect(screen.getByText(/Settings/)).toBeInTheDocument()
    expect(screen.getByText(/Billing/)).toBeInTheDocument()
  })
})
