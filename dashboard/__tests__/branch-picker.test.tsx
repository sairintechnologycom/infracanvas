import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

import { BranchPicker } from '@/components/integrations/BranchPicker'
import type { BranchResp, RepoResp } from '@/lib/types'

const REPO_DEV: RepoResp = {
  full_name: 'acme/api',
  default_branch: 'dev',
  private: false,
}

const REPO_MAIN: RepoResp = {
  full_name: 'acme/web',
  default_branch: 'main',
  private: false,
}

const BRANCHES_5: BranchResp[] = [
  { name: 'main', commit_sha: 'a' },
  { name: 'dev', commit_sha: 'b' },
  { name: 'feature/x', commit_sha: 'c' },
  { name: 'feature/y', commit_sha: 'd' },
  { name: 'release/1.0', commit_sha: 'e' },
]

function makeFetchMock(data: unknown = BRANCHES_5, ok = true, status = 200) {
  return vi.fn().mockResolvedValue({
    ok,
    status,
    json: async () => data,
  })
}

describe('BranchPicker', () => {
  beforeEach(() => {
    vi.unstubAllGlobals()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('does not fetch when selectedRepo is null', () => {
    const fetchMock = makeFetchMock()
    vi.stubGlobal('fetch', fetchMock)
    const { container } = render(
      <BranchPicker
        installationId={42}
        selectedRepo={null}
        value=""
        onChange={() => {}}
      />,
    )
    expect(fetchMock).not.toHaveBeenCalled()
    // Renders nothing when no repo selected.
    expect(container.firstChild).toBeNull()
  })

  it('fetches /api/github/branches on selectedRepo change', async () => {
    const fetchMock = makeFetchMock(BRANCHES_5)
    vi.stubGlobal('fetch', fetchMock)
    render(
      <BranchPicker
        installationId={42}
        selectedRepo={REPO_DEV}
        value=""
        onChange={() => {}}
      />,
    )
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(1)
      const url = fetchMock.mock.calls[0][0] as string
      expect(url).toContain('/api/github/branches?installation_id=42')
      expect(url).toContain('repo=acme%2Fapi')
    })
  })

  it('defaults onChange to repo.default_branch on first load', async () => {
    vi.stubGlobal('fetch', makeFetchMock(BRANCHES_5))
    const onChange = vi.fn()
    render(
      <BranchPicker
        installationId={42}
        selectedRepo={REPO_DEV}
        value=""
        onChange={onChange}
      />,
    )
    await waitFor(() => {
      // REPO_DEV.default_branch === 'dev'
      expect(onChange).toHaveBeenCalledWith('dev')
    })
  })

  it('refetches when selectedRepo prop changes', async () => {
    const fetchMock = makeFetchMock(BRANCHES_5)
    vi.stubGlobal('fetch', fetchMock)
    const { rerender } = render(
      <BranchPicker
        installationId={42}
        selectedRepo={REPO_DEV}
        value=""
        onChange={() => {}}
      />,
    )
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1))

    rerender(
      <BranchPicker
        installationId={42}
        selectedRepo={REPO_MAIN}
        value=""
        onChange={() => {}}
      />,
    )
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(2)
      const url2 = fetchMock.mock.calls[1][0] as string
      expect(url2).toContain('repo=acme%2Fweb')
    })
  })

  it('lists all branches as Select options', async () => {
    vi.stubGlobal('fetch', makeFetchMock(BRANCHES_5))
    render(
      <BranchPicker
        installationId={42}
        selectedRepo={REPO_DEV}
        value="dev"
        onChange={() => {}}
      />,
    )
    // Wait for fetch to settle then open the Select
    await waitFor(() =>
      expect(screen.getByRole('combobox')).not.toHaveAttribute('disabled'),
    )
    fireEvent.click(screen.getByRole('combobox'))
    await waitFor(() => {
      // Radix Select renders options as role="option"
      const options = document.querySelectorAll('[role="option"]')
      expect(options.length).toBe(BRANCHES_5.length)
    })
  })

  it('calls onChange when user picks a branch', async () => {
    vi.stubGlobal('fetch', makeFetchMock(BRANCHES_5))
    const onChange = vi.fn()
    render(
      <BranchPicker
        installationId={42}
        selectedRepo={REPO_DEV}
        value="dev"
        onChange={onChange}
      />,
    )
    // Wait for fetch + initial default_branch onChange to fire
    await waitFor(() => expect(onChange).toHaveBeenCalledWith('dev'))
    onChange.mockClear()

    fireEvent.click(screen.getByRole('combobox'))
    await waitFor(() => {
      const options = document.querySelectorAll('[role="option"]')
      expect(options.length).toBe(BRANCHES_5.length)
    })
    // Click "feature/x" option
    const options = Array.from(document.querySelectorAll('[role="option"]'))
    const featureX = options.find((el) =>
      (el.textContent ?? '').includes('feature/x'),
    )
    expect(featureX).toBeTruthy()
    fireEvent.click(featureX!)

    await waitFor(() => {
      expect(onChange).toHaveBeenCalledWith('feature/x')
    })
  })
})
