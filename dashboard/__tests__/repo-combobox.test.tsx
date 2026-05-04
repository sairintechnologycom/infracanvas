import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, act, waitFor } from '@testing-library/react'

import { RepoCombobox } from '@/components/integrations/RepoCombobox'
import type { RepoResp } from '@/lib/types'

const MOCK_REPOS: RepoResp[] = [
  { full_name: 'acme/api', default_branch: 'main', private: true },
  { full_name: 'acme/web', default_branch: 'main', private: false },
  { full_name: 'acme/docs', default_branch: 'main', private: false },
]

function makeFetchMock(data: unknown = MOCK_REPOS, ok = true, status = 200) {
  return vi.fn().mockResolvedValue({
    ok,
    status,
    json: async () => data,
  })
}

describe('RepoCombobox', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('renders with placeholder', () => {
    vi.stubGlobal('fetch', makeFetchMock([]))
    render(<RepoCombobox installationId={42} onSelect={() => {}} />)
    expect(screen.getByRole('button', { name: /pick a repo/i })).toBeInTheDocument()
  })

  it('opens popover with command input on trigger click', async () => {
    vi.stubGlobal('fetch', makeFetchMock([]))
    render(<RepoCombobox installationId={42} onSelect={() => {}} />)
    fireEvent.click(screen.getByRole('button', { name: /pick a repo/i }))
    await act(async () => {
      vi.advanceTimersByTime(300)
    })
    const input = await screen.findByPlaceholderText(/search repos/i)
    expect(input).toBeInTheDocument()
  })

  it('debounces 250ms — only one fetch fires per query', async () => {
    const fetchMock = makeFetchMock(MOCK_REPOS)
    vi.stubGlobal('fetch', fetchMock)
    render(<RepoCombobox installationId={42} onSelect={() => {}} />)

    // Initial mount fires one debounced fetch (no q yet)
    await act(async () => {
      vi.advanceTimersByTime(250)
    })
    const initialCalls = fetchMock.mock.calls.length

    // Open popover, type quickly: 'f' 'o' 'o' within 100ms — should collapse
    // to a single fetch after 250ms of quiescence.
    fireEvent.click(screen.getByRole('button', { name: /pick a repo/i }))
    await act(async () => {
      vi.advanceTimersByTime(50)
    })
    const input = await screen.findByPlaceholderText(/search repos/i)
    fireEvent.change(input, { target: { value: 'f' } })
    await act(async () => { vi.advanceTimersByTime(50) })
    fireEvent.change(input, { target: { value: 'fo' } })
    await act(async () => { vi.advanceTimersByTime(50) })
    fireEvent.change(input, { target: { value: 'foo' } })
    // Only after 250ms of no further changes should fetch fire.
    await act(async () => { vi.advanceTimersByTime(250) })

    // Exactly one extra fetch beyond the initial mount fetch.
    expect(fetchMock.mock.calls.length).toBe(initialCalls + 1)
    const lastUrl = fetchMock.mock.calls[fetchMock.mock.calls.length - 1][0] as string
    expect(lastUrl).toContain('/api/github/repos?installation_id=42')
    expect(lastUrl).toContain('q=foo')
  })

  it('renders repo list items after fetch resolves', async () => {
    vi.stubGlobal('fetch', makeFetchMock(MOCK_REPOS))
    render(<RepoCombobox installationId={42} onSelect={() => {}} />)
    fireEvent.click(screen.getByRole('button', { name: /pick a repo/i }))
    // Flush initial debounced fetch
    await act(async () => { vi.advanceTimersByTime(300) })
    await waitFor(() => {
      expect(screen.getByText('acme/api')).toBeInTheDocument()
      expect(screen.getByText('acme/web')).toBeInTheDocument()
      expect(screen.getByText('acme/docs')).toBeInTheDocument()
    })
  })

  it('renders private lock icon for private repos', async () => {
    vi.stubGlobal('fetch', makeFetchMock(MOCK_REPOS))
    render(<RepoCombobox installationId={42} onSelect={() => {}} />)
    fireEvent.click(screen.getByRole('button', { name: /pick a repo/i }))
    await act(async () => { vi.advanceTimersByTime(300) })
    await waitFor(() => {
      // Only acme/api is private in MOCK_REPOS
      const locks = screen.getAllByLabelText('private')
      expect(locks).toHaveLength(1)
    })
  })

  it('calls onSelect with the chosen repo on click', async () => {
    vi.stubGlobal('fetch', makeFetchMock(MOCK_REPOS))
    const onSelect = vi.fn()
    render(<RepoCombobox installationId={42} onSelect={onSelect} />)
    fireEvent.click(screen.getByRole('button', { name: /pick a repo/i }))
    await act(async () => { vi.advanceTimersByTime(300) })
    const item = await screen.findByText('acme/web')
    fireEvent.click(item)
    await waitFor(() => {
      expect(onSelect).toHaveBeenCalledTimes(1)
      expect(onSelect).toHaveBeenCalledWith(MOCK_REPOS[1])
    })
  })

  it('cancelled flag suppresses setState after unmount during in-flight fetch', async () => {
    // Build a fetch that we control: deferred resolution.
    let resolveFetch: ((v: unknown) => void) | null = null
    const fetchMock = vi.fn().mockImplementation(
      () => new Promise((resolve) => {
        resolveFetch = resolve
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    const { unmount } = render(
      <RepoCombobox installationId={42} onSelect={() => {}} />,
    )
    // Trigger debounced fetch
    await act(async () => { vi.advanceTimersByTime(300) })
    expect(fetchMock).toHaveBeenCalled()

    // Unmount BEFORE the fetch resolves — the cleanup must set cancelled=true
    // so the .then() guard short-circuits and never calls setState on an
    // unmounted component (would emit a "state update on unmounted component"
    // warning to console.error).
    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    unmount()

    // Now resolve the fetch — the .then chain runs but should be a no-op.
    await act(async () => {
      resolveFetch!({ ok: true, status: 200, json: async () => MOCK_REPOS })
      // give microtasks a tick to flush
      await Promise.resolve()
      await Promise.resolve()
    })

    // No "state update on an unmounted component" warning should have fired.
    const warningCalls = errorSpy.mock.calls.filter((args) =>
      String(args[0]).includes('unmounted'),
    )
    expect(warningCalls).toHaveLength(0)
    errorSpy.mockRestore()
  })
})
