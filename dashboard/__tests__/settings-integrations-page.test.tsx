import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, act } from '@testing-library/react'

import type { InstallationResp } from '@/lib/types'

// ── Mocks ────────────────────────────────────────────────────────────────────
// Mock InstallButton so we don't recreate Clerk plumbing here — its own tests
// (install-button.test.tsx) already cover its surface.
vi.mock('@/components/integrations/InstallButton', () => ({
  InstallButton: () => (
    <div data-testid="install-button-mock">install-button</div>
  ),
}))

// Mock ScanTriggerForm so the page test focuses on the state machine, not
// on the form. The mock surfaces installationId in DOM text content so
// per-installation rendering can be asserted.
vi.mock('@/components/integrations/ScanTriggerForm', () => ({
  ScanTriggerForm: ({ installationId }: { installationId: number }) => (
    <div data-testid="scan-trigger-form-mock">
      scan-trigger-form:{installationId}
    </div>
  ),
}))

// Mock next/navigation: useSearchParams is reassignable per test.
const searchParamsMock = vi.fn(() => new URLSearchParams(''))
vi.mock('next/navigation', () => ({
  useSearchParams: () => searchParamsMock(),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn() }),
}))

const INSTALLATION_ONE: InstallationResp = {
  installation_id: 7,
  github_account_login: 'acme-org',
  github_account_type: 'Organization',
  installed_at: '2026-05-01T10:00:00Z',
  installed_by_user_id: 'user_abc',
}
const INSTALLATION_TWO: InstallationResp = {
  installation_id: 8,
  github_account_login: 'acme-personal',
  github_account_type: 'User',
  installed_at: '2026-05-02T10:00:00Z',
  installed_by_user_id: 'user_xyz',
}

function makeFetchMock(data: unknown, ok = true, status = 200) {
  return vi.fn().mockResolvedValue({
    ok,
    status,
    json: async () => data,
  })
}

function makeFetchSequence(
  responses: Array<{ data: unknown; ok?: boolean; status?: number }>,
) {
  const fn = vi.fn()
  for (const r of responses) {
    fn.mockResolvedValueOnce({
      ok: r.ok ?? true,
      status: r.status ?? 200,
      json: async () => r.data,
    })
  }
  return fn
}

beforeEach(() => {
  vi.unstubAllGlobals()
  searchParamsMock.mockReturnValue(new URLSearchParams(''))
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('settings/integrations page (live state machine)', () => {
  it('preinstall: empty installations → InstallButton rendered', async () => {
    vi.stubGlobal('fetch', makeFetchMock([] as InstallationResp[]))
    const { default: IntegrationsPage } = await import(
      '@/app/(dashboard)/settings/integrations/page'
    )
    render(<IntegrationsPage />)
    await waitFor(() => {
      expect(screen.getByTestId('install-button-mock')).toBeInTheDocument()
    })
    expect(screen.queryByTestId('scan-trigger-form-mock')).not.toBeInTheDocument()
  })

  it('postinstall: one installation row → renders login + ScanTriggerForm with matching installationId', async () => {
    vi.stubGlobal('fetch', makeFetchMock([INSTALLATION_ONE]))
    const { default: IntegrationsPage } = await import(
      '@/app/(dashboard)/settings/integrations/page'
    )
    render(<IntegrationsPage />)
    await waitFor(() => {
      expect(screen.getByText(/acme-org/)).toBeInTheDocument()
    })
    const form = screen.getByTestId('scan-trigger-form-mock')
    expect(form.textContent).toContain('scan-trigger-form:7')
  })

  it('multiple installations render multiple ScanTriggerForms', async () => {
    vi.stubGlobal('fetch', makeFetchMock([INSTALLATION_ONE, INSTALLATION_TWO]))
    const { default: IntegrationsPage } = await import(
      '@/app/(dashboard)/settings/integrations/page'
    )
    render(<IntegrationsPage />)
    await waitFor(() => {
      expect(screen.getByText(/acme-org/)).toBeInTheDocument()
      expect(screen.getByText(/acme-personal/)).toBeInTheDocument()
    })
    const forms = screen.getAllByTestId('scan-trigger-form-mock')
    expect(forms).toHaveLength(2)
    expect(forms[0].textContent).toContain('scan-trigger-form:7')
    expect(forms[1].textContent).toContain('scan-trigger-form:8')
  })

  it('poll runs while ?install=success and list is empty', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    searchParamsMock.mockReturnValue(new URLSearchParams('install=success'))
    const fetchMock = makeFetchSequence([
      { data: [] },
      { data: [] },
    ])
    vi.stubGlobal('fetch', fetchMock)
    const { default: IntegrationsPage } = await import(
      '@/app/(dashboard)/settings/integrations/page'
    )
    render(<IntegrationsPage />)
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1))
    // Advance 3s — poll fires second fetch.
    await act(async () => {
      vi.advanceTimersByTime(3000)
    })
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
    vi.useRealTimers()
  })

  it('poll stops once installations list becomes non-empty', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    searchParamsMock.mockReturnValue(new URLSearchParams('install=success'))
    const fetchMock = makeFetchSequence([
      { data: [] },
      { data: [INSTALLATION_ONE] },
      // No third response set — if a third fetch fires, it would resolve
      // undefined and crash. Stays useful as a "should not be called" guard.
    ])
    vi.stubGlobal('fetch', fetchMock)
    const { default: IntegrationsPage } = await import(
      '@/app/(dashboard)/settings/integrations/page'
    )
    render(<IntegrationsPage />)
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1))
    // Tick → second fetch returns the row.
    await act(async () => {
      vi.advanceTimersByTime(3000)
    })
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
    // Tick again — poll must stop because list is non-empty.
    await act(async () => {
      vi.advanceTimersByTime(3000)
    })
    expect(fetchMock).toHaveBeenCalledTimes(2)
    vi.useRealTimers()
  })

  it('preserves the Slack stub block', async () => {
    vi.stubGlobal('fetch', makeFetchMock([] as InstallationResp[]))
    const { default: IntegrationsPage } = await import(
      '@/app/(dashboard)/settings/integrations/page'
    )
    render(<IntegrationsPage />)
    await waitFor(() => {
      expect(screen.getByTestId('install-button-mock')).toBeInTheDocument()
    })
    // Slack stub still on the page (heading + webhook input).
    expect(screen.getByRole('heading', { name: /slack/i })).toBeInTheDocument()
    expect(
      screen.getByPlaceholderText(/hooks\.slack\.com/i),
    ).toBeInTheDocument()
  })

  it('initial loading state: neither InstallButton nor ScanTriggerForm yet', async () => {
    // Deferred fetch — never resolves until we let it.
    let resolveFetch: ((v: unknown) => void) = () => {}
    const fetchMock = vi.fn().mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveFetch = resolve
        }),
    )
    vi.stubGlobal('fetch', fetchMock)
    const { default: IntegrationsPage } = await import(
      '@/app/(dashboard)/settings/integrations/page'
    )
    render(<IntegrationsPage />)
    // Loading skeleton present, real surfaces absent.
    expect(screen.queryByTestId('install-button-mock')).not.toBeInTheDocument()
    expect(screen.queryByTestId('scan-trigger-form-mock')).not.toBeInTheDocument()
    // A loading hint must be in the DOM (skeleton or "Loading…" text).
    expect(screen.getByTestId('github-loading')).toBeInTheDocument()
    // Resolve to keep the test deterministic.
    resolveFetch({ ok: true, status: 200, json: async () => [] })
  })
})
