import React from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import '@testing-library/jest-dom'
import { ShareLinksList } from '@/components/share/ShareLinksList'

const mockFetch = vi.fn()
const { toastSuccess, toastError } = vi.hoisted(() => ({
  toastSuccess: vi.fn(),
  toastError: vi.fn(),
}))
vi.mock('sonner', () => ({
  toast: { success: toastSuccess, error: toastError },
}))

beforeEach(() => {
  mockFetch.mockReset()
  global.fetch = mockFetch as unknown as typeof fetch
})

const fixtureLinks = [
  {
    id: 'l1',
    expires_at: '2026-05-15T00:00:00Z',
    created_by: 'sam@example.com',
    has_password: false,
    created_at: '2026-04-28T10:00:00Z',
  },
  {
    id: 'l2',
    expires_at: null,
    created_by: 'alex@example.com',
    has_password: true,
    created_at: '2026-04-27T10:00:00Z',
  },
]

describe('ShareLinksList — Active share links (RMD-04)', () => {
  it('fetches /api/scan-share?scan_id=... on mount', async () => {
    mockFetch.mockResolvedValue({ ok: true, json: async () => ({ links: [] }) })
    render(<ShareLinksList scanId="scan-1" />)
    await waitFor(() => expect(mockFetch).toHaveBeenCalled())
    expect(mockFetch.mock.calls[0][0] as string).toMatch(
      /\/api\/scan-share\?scan_id=scan-1/,
    )
  })

  it('shows empty state copy when there are no links', async () => {
    mockFetch.mockResolvedValue({ ok: true, json: async () => ({ links: [] }) })
    render(<ShareLinksList scanId="scan-1" />)
    expect(await screen.findByText(/no active share links/i)).toBeInTheDocument()
  })

  it('renders one row per link with the spec format', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({ links: fixtureLinks }),
    })
    render(<ShareLinksList scanId="scan-1" />)
    await waitFor(() =>
      expect(screen.getAllByRole('listitem')).toHaveLength(2),
    )
    // Format: Expires {date} · Created by {user} · {with password / no password}
    expect(screen.getByText(/with password/i)).toBeInTheDocument()
    expect(screen.getByText(/no password/i)).toBeInTheDocument()
    expect(screen.getByText(/sam@example\.com/)).toBeInTheDocument()
    expect(screen.getByText(/alex@example\.com/)).toBeInTheDocument()
  })

  it('renders "Never" for null expires_at', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({ links: [fixtureLinks[1]] }),
    })
    render(<ShareLinksList scanId="scan-1" />)
    expect(await screen.findByText(/never/i)).toBeInTheDocument()
  })

  it('refetches when refreshKey prop changes', async () => {
    mockFetch.mockResolvedValue({ ok: true, json: async () => ({ links: [] }) })
    const { rerender } = render(
      <ShareLinksList scanId="scan-1" refreshKey={0} />,
    )
    await waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(1))
    rerender(<ShareLinksList scanId="scan-1" refreshKey={1} />)
    await waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(2))
  })
})

describe('RevokeShareLinkButton — destructive confirm flow (RMD-03, RMD-04)', () => {
  beforeEach(() => {
    toastSuccess.mockClear()
    toastError.mockClear()
    mockFetch.mockReset()
  })

  it('clicking [Revoke] opens AlertDialog with spec copy', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({ links: fixtureLinks }),
    })
    render(<ShareLinksList scanId="scan-1" />)
    const revokeBtns = await screen.findAllByRole('button', {
      name: /revoke/i,
    })
    fireEvent.click(revokeBtns[0])
    expect(await screen.findByRole('alertdialog')).toBeInTheDocument()
    expect(screen.getByText(/Revoke this share link\?/)).toBeInTheDocument()
    expect(screen.getByText(/410 Gone/)).toBeInTheDocument()
  })

  it('Cancel does not call DELETE', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({ links: fixtureLinks }),
    })
    render(<ShareLinksList scanId="scan-1" />)
    fireEvent.click(
      (await screen.findAllByRole('button', { name: /revoke/i }))[0],
    )
    fireEvent.click(await screen.findByRole('button', { name: /cancel/i }))
    const deleteCalls = mockFetch.mock.calls.filter(
      (c) => (c[1] as RequestInit | undefined)?.method === 'DELETE',
    )
    expect(deleteCalls).toHaveLength(0)
  })

  it('Confirm fires DELETE and toast.success', async () => {
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ links: fixtureLinks }),
      })
      .mockResolvedValueOnce({ ok: true })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ links: [fixtureLinks[1]] }),
      })
    render(<ShareLinksList scanId="scan-1" />)
    fireEvent.click(
      (await screen.findAllByRole('button', { name: /revoke/i }))[0],
    )
    const dialog = await screen.findByRole('alertdialog')
    const confirmBtn = within(dialog).getByRole('button', { name: /revoke/i })
    fireEvent.click(confirmBtn)
    await waitFor(() =>
      expect(toastSuccess).toHaveBeenCalledWith('Share link revoked'),
    )
    const deleteCalls = mockFetch.mock.calls.filter(
      (c) => (c[1] as RequestInit | undefined)?.method === 'DELETE',
    )
    expect(deleteCalls).toHaveLength(1)
    expect(deleteCalls[0][0]).toMatch(/scan_id=scan-1/)
    expect(deleteCalls[0][0]).toMatch(/share_id=l1/)
  })

  it('failed DELETE fires toast.error and does not refetch', async () => {
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ links: fixtureLinks }),
      })
      .mockResolvedValueOnce({ ok: false, status: 500, text: async () => 'oops' })
    render(<ShareLinksList scanId="scan-1" />)
    fireEvent.click(
      (await screen.findAllByRole('button', { name: /revoke/i }))[0],
    )
    const dialog = await screen.findByRole('alertdialog')
    fireEvent.click(within(dialog).getByRole('button', { name: /revoke/i }))
    await waitFor(() => expect(toastError).toHaveBeenCalled())
    expect(toastSuccess).not.toHaveBeenCalled()
  })
})
