import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

import type { RepoResp } from '@/lib/types'

// ── Mocks ────────────────────────────────────────────────────────────────────
// Captures for spying on calls between renders.
const pushMock = vi.fn()
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: pushMock, replace: vi.fn(), refresh: vi.fn() }),
}))

// Mock RepoCombobox: render a button that, on click, calls onSelect with a
// known repo. Lets us drive the parent form's "user picks repo" transition
// without entangling the cmdk popover.
const MOCK_REPO: RepoResp = {
  full_name: 'acme/api',
  default_branch: 'main',
  private: false,
}
vi.mock('@/components/integrations/RepoCombobox', () => ({
  RepoCombobox: ({
    onSelect,
    value,
  }: {
    onSelect: (r: RepoResp) => void
    value?: RepoResp | null
  }) => (
    <button
      type="button"
      data-testid="mock-repo-combobox"
      onClick={() => onSelect(MOCK_REPO)}
    >
      repo-combobox:{value?.full_name ?? 'none'}
    </button>
  ),
}))

// Mock BranchPicker: render an element that auto-fires onChange when the
// parent passes a selectedRepo. Surfaces visibility as "rendered" / "hidden".
vi.mock('@/components/integrations/BranchPicker', () => ({
  BranchPicker: ({
    selectedRepo,
    value,
    onChange,
  }: {
    selectedRepo: RepoResp | null
    value: string
    onChange: (b: string) => void
  }) => {
    if (!selectedRepo) return null
    return (
      <div data-testid="mock-branch-picker">
        branch-picker:{value || 'empty'}
        <button
          type="button"
          data-testid="mock-branch-pick-main"
          onClick={() => onChange('main')}
        >
          pick main
        </button>
      </div>
    )
  },
}))

import { ScanTriggerForm } from '@/components/integrations/ScanTriggerForm'

beforeEach(() => {
  pushMock.mockReset()
  vi.unstubAllGlobals()
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('ScanTriggerForm', () => {
  it('renders subform skeleton: RepoCombobox + path input default ".", BranchPicker hidden', () => {
    render(<ScanTriggerForm installationId={42} />)
    // RepoCombobox rendered
    expect(screen.getByTestId('mock-repo-combobox')).toBeInTheDocument()
    // BranchPicker hidden initially (no selectedRepo)
    expect(screen.queryByTestId('mock-branch-picker')).not.toBeInTheDocument()
    // Path input present, default to "."
    const pathInput = screen.getByLabelText(/subdirectory path/i) as HTMLInputElement
    expect(pathInput).toBeInTheDocument()
    expect(pathInput.value).toBe('.')
  })

  it('shows branch picker after a repo is selected', () => {
    render(<ScanTriggerForm installationId={42} />)
    expect(screen.queryByTestId('mock-branch-picker')).not.toBeInTheDocument()
    fireEvent.click(screen.getByTestId('mock-repo-combobox'))
    expect(screen.getByTestId('mock-branch-picker')).toBeInTheDocument()
  })

  it('submit button disabled until both repo and branch are picked', () => {
    render(<ScanTriggerForm installationId={42} />)
    const button = screen.getByRole('button', { name: /^scan$/i })
    expect(button).toBeDisabled()
    // Pick repo only — still disabled (no branch).
    fireEvent.click(screen.getByTestId('mock-repo-combobox'))
    expect(button).toBeDisabled()
    // Pick branch — enabled.
    fireEvent.click(screen.getByTestId('mock-branch-pick-main'))
    expect(button).not.toBeDisabled()
  })

  it('submits with correct payload to /api/scans/from-github', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ scan_id: 'abc' }),
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<ScanTriggerForm installationId={42} />)
    fireEvent.click(screen.getByTestId('mock-repo-combobox'))
    fireEvent.click(screen.getByTestId('mock-branch-pick-main'))
    // Path defaults to "."
    fireEvent.click(screen.getByRole('button', { name: /^scan$/i }))

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(1)
    })
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/scans/from-github')
    expect(init.method).toBe('POST')
    expect(init.headers['Content-Type']).toBe('application/json')
    const body = JSON.parse(init.body)
    expect(body).toEqual({
      installation_id: 42,
      repo: 'acme/api',
      branch: 'main',
      path: '.',
    })
  })

  it('redirects on success: router.push("/scans/abc") after POST returns scan_id', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ scan_id: 'abc' }),
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<ScanTriggerForm installationId={42} />)
    fireEvent.click(screen.getByTestId('mock-repo-combobox'))
    fireEvent.click(screen.getByTestId('mock-branch-pick-main'))
    fireEvent.click(screen.getByRole('button', { name: /^scan$/i }))

    await waitFor(() => {
      expect(pushMock).toHaveBeenCalledWith('/scans/abc')
    })
  })

  it('shows inline error on 503; does NOT call router.push', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
      json: async () => ({ error: 'request_failed' }),
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<ScanTriggerForm installationId={42} />)
    fireEvent.click(screen.getByTestId('mock-repo-combobox'))
    fireEvent.click(screen.getByTestId('mock-branch-pick-main'))
    fireEvent.click(screen.getByRole('button', { name: /^scan$/i }))

    await waitFor(() => {
      const alert = screen.getByRole('alert')
      expect(alert).toBeInTheDocument()
      // 503 → friendly rate-limit copy
      expect(alert.textContent ?? '').toMatch(/rate-?limit/i)
    })
    expect(pushMock).not.toHaveBeenCalled()
  })

  it('default path is "." and visible in the DOM', () => {
    render(<ScanTriggerForm installationId={42} />)
    const pathInput = screen.getByLabelText(/subdirectory path/i) as HTMLInputElement
    expect(pathInput.value).toBe('.')
  })
})
