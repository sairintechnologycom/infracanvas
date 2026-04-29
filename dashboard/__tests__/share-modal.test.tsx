import React from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom'

// lucide-react icons render as spans for testing
vi.mock('lucide-react', () => ({
  Copy: () => <span data-testid="icon-copy" />,
  Share2: () => <span data-testid="icon-share2" />,
  X: () => <span data-testid="icon-x" />,
  Check: () => <span data-testid="icon-check" />,
}))

const ORIGINAL_FETCH = global.fetch
const ORIGINAL_DASHBOARD_URL = process.env.NEXT_PUBLIC_DASHBOARD_URL

beforeEach(() => {
  process.env.NEXT_PUBLIC_DASHBOARD_URL = 'https://app.example.com'
})

afterEach(() => {
  global.fetch = ORIGINAL_FETCH
  if (ORIGINAL_DASHBOARD_URL === undefined) {
    delete process.env.NEXT_PUBLIC_DASHBOARD_URL
  } else {
    process.env.NEXT_PUBLIC_DASHBOARD_URL = ORIGINAL_DASHBOARD_URL
  }
  vi.restoreAllMocks()
})

describe('ShareModal', () => {
  it('renders "Share this scan" dialog title when isOpen=true', async () => {
    const { ShareModal } = await import('@/components/share/ShareModal')
    render(<ShareModal scanId="scan-001" isOpen={true} onClose={() => {}} />)
    expect(screen.getByText('Share this scan')).toBeInTheDocument()
  })

  it('renders "Generate share link" primary CTA', async () => {
    const { ShareModal } = await import('@/components/share/ShareModal')
    render(<ShareModal scanId="scan-001" isOpen={true} onClose={() => {}} />)
    expect(screen.getByRole('button', { name: /generate share link/i })).toBeInTheDocument()
  })

  it('does NOT show the "Never" warning when "7 days" is selected (default)', async () => {
    const { ShareModal } = await import('@/components/share/ShareModal')
    render(<ShareModal scanId="scan-001" isOpen={true} onClose={() => {}} />)
    // 7 days is default — warning containing "⚠" should be absent
    expect(screen.queryByText(/⚠/)).toBeNull()
  })

  it('reveals "⚠" warning text when expiry is changed to "Never (not recommended)"', async () => {
    const { ShareModal } = await import('@/components/share/ShareModal')
    render(<ShareModal scanId="scan-001" isOpen={true} onClose={() => {}} />)
    const select = screen.getByLabelText(/expir/i) as HTMLSelectElement
    fireEvent.change(select, { target: { value: 'never' } })
    const warning = await screen.findByText(/⚠/)
    expect(warning).toBeInTheDocument()
  })

  it('renders password input with type="password"', async () => {
    const { ShareModal } = await import('@/components/share/ShareModal')
    render(<ShareModal scanId="scan-001" isOpen={true} onClose={() => {}} />)
    const pwd = screen.getByLabelText(/password/i) as HTMLInputElement
    expect(pwd.type).toBe('password')
  })

  it('after successful POST, shows generated URL containing "/share/" and copy button', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 201,
      json: () =>
        Promise.resolve({
          id: 'link-1',
          token: 'tok-abc-123',
          share_url: 'https://app.example.com/share/tok-abc-123',
          expires_at: null,
        }),
    } as unknown as Response)

    const { ShareModal } = await import('@/components/share/ShareModal')
    render(<ShareModal scanId="scan-001" isOpen={true} onClose={() => {}} />)

    fireEvent.click(screen.getByRole('button', { name: /generate share link/i }))

    const urlInput = (await waitFor(() => {
      const inputs = screen.getAllByDisplayValue(/\/share\//)
      expect(inputs.length).toBeGreaterThan(0)
      return inputs[0]
    })) as HTMLInputElement

    expect(urlInput).toBeInTheDocument()
    expect(urlInput.readOnly).toBe(true)
    expect(urlInput.value).toContain('/share/')

    // Copy button with required aria-label
    expect(
      screen.getByRole('button', { name: 'Copy share link to clipboard' }),
    ).toBeInTheDocument()
  })
})
