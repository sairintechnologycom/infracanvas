import React from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

// lucide-react icons render as spans for testing.
// Use importOriginal so any icon NOT in the override list (e.g. XIcon used by
// shadcn DialogContent) still resolves rather than throwing.
vi.mock('lucide-react', async (importOriginal) => {
  const actual = await importOriginal<typeof import('lucide-react')>()
  return {
    ...actual,
    Copy: () => <span data-testid="icon-copy" />,
    Share2: () => <span data-testid="icon-share2" />,
    X: () => <span data-testid="icon-x" />,
    Check: () => <span data-testid="icon-check" />,
  }
})

// Mock sonner so toast assertions work in jsdom (RMD-03)
const toastSuccess = vi.fn()
const toastError = vi.fn()
vi.mock('sonner', () => ({
  toast: { success: toastSuccess, error: toastError },
}))

const SOURCE = readFileSync(
  join(__dirname, '..', 'components', 'share', 'ShareModal.tsx'),
  'utf8',
)

const ORIGINAL_FETCH = global.fetch
const ORIGINAL_DASHBOARD_URL = process.env.NEXT_PUBLIC_DASHBOARD_URL
const ORIGINAL_CLIPBOARD = (navigator as { clipboard?: unknown }).clipboard

beforeEach(() => {
  process.env.NEXT_PUBLIC_DASHBOARD_URL = 'https://app.example.com'
  toastSuccess.mockClear()
  toastError.mockClear()
})

afterEach(() => {
  global.fetch = ORIGINAL_FETCH
  if (ORIGINAL_DASHBOARD_URL === undefined) {
    delete process.env.NEXT_PUBLIC_DASHBOARD_URL
  } else {
    process.env.NEXT_PUBLIC_DASHBOARD_URL = ORIGINAL_DASHBOARD_URL
  }
  // Restore clipboard
  Object.defineProperty(navigator, 'clipboard', {
    value: ORIGINAL_CLIPBOARD,
    configurable: true,
    writable: true,
  })
  vi.restoreAllMocks()
})

function mockClipboard(impl: { writeText: (s: string) => Promise<void> }) {
  Object.defineProperty(navigator, 'clipboard', {
    value: impl,
    configurable: true,
    writable: true,
  })
}

function mockGenerateOk() {
  // URL-aware mock: ShareLinksList fires GET on mount/refresh; ShareModal
  // fires POST on Generate. Both share /api/scan-share so we route by method.
  global.fetch = vi.fn().mockImplementation(((url: RequestInfo, init?: RequestInit) => {
    const method = (init?.method ?? 'GET').toUpperCase()
    const urlStr = String(url)
    if (method === 'GET' && urlStr.includes('/api/scan-share')) {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ links: [] }),
      } as unknown as Response)
    }
    // Default: POST share generation
    return Promise.resolve({
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
  }) as typeof fetch)
}

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
    mockGenerateOk()
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
    expect(
      screen.getByRole('button', { name: 'Copy share link to clipboard' }),
    ).toBeInTheDocument()
  })
})

describe('ShareModal — shadcn Dialog migration + copy toast (RMD-01, RMD-03)', () => {
  it('source no longer contains hand-rolled <div role="dialog">', () => {
    expect(SOURCE).not.toMatch(/<div[^>]*role=["']dialog["']/)
  })

  it('imports Dialog from shadcn primitive', () => {
    expect(SOURCE).toMatch(/from\s+['"]@\/components\/ui\/dialog['"]/)
  })

  it('imports toast from sonner', () => {
    expect(SOURCE).toMatch(/from\s+['"]sonner['"]/)
  })

  it('fires toast.success on successful copy', async () => {
    mockGenerateOk()
    mockClipboard({ writeText: vi.fn().mockResolvedValue(undefined) })

    const { ShareModal } = await import('@/components/share/ShareModal')
    render(<ShareModal scanId="scan-001" isOpen={true} onClose={() => {}} />)

    fireEvent.click(screen.getByRole('button', { name: /generate share link/i }))
    const copyBtn = await screen.findByRole('button', {
      name: 'Copy share link to clipboard',
    })
    fireEvent.click(copyBtn)

    await waitFor(() =>
      expect(toastSuccess).toHaveBeenCalledWith('Link copied to clipboard'),
    )
  })

  it('fires toast.error when clipboard rejects (no silent swallow)', async () => {
    mockGenerateOk()
    mockClipboard({ writeText: vi.fn().mockRejectedValue(new Error('denied')) })

    const { ShareModal } = await import('@/components/share/ShareModal')
    render(<ShareModal scanId="scan-001" isOpen={true} onClose={() => {}} />)

    fireEvent.click(screen.getByRole('button', { name: /generate share link/i }))
    const copyBtn = await screen.findByRole('button', {
      name: 'Copy share link to clipboard',
    })
    fireEvent.click(copyBtn)

    await waitFor(() => expect(toastError).toHaveBeenCalled())
  })
})

describe('ShareModal — Active share-links list mount (RMD-04)', () => {
  it('mounts ShareLinksList passing the scanId — fetches /api/scan-share?scan_id=...', async () => {
    const fetchSpy = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ links: [] }),
    })
    global.fetch = fetchSpy as unknown as typeof fetch

    const { ShareModal } = await import('@/components/share/ShareModal')
    render(<ShareModal scanId="scan-xyz" isOpen={true} onClose={() => {}} />)

    await waitFor(() => {
      const listFetchCall = fetchSpy.mock.calls.find((c) =>
        String(c[0]).includes('/api/scan-share?scan_id=scan-xyz'),
      )
      expect(listFetchCall).toBeDefined()
    })
  })

  it('source no longer contains the Phase 7 placeholder copy or TODO', () => {
    expect(SOURCE).not.toMatch(/No share links yet for this scan\./)
    expect(SOURCE).not.toMatch(/TODO[^\n]*share-links/)
  })

  it('source imports ShareLinksList', () => {
    expect(SOURCE).toMatch(/ShareLinksList/)
  })
})
