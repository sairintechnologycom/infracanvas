import React from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom'

// lucide-react icons render as spans for testing
vi.mock('lucide-react', () => ({
  Lock: () => <span data-testid="icon-lock" />,
}))

// ShareViewer is heavy (loads viewer + xyflow); stub it so the test focuses
// purely on the gate's visual contract. We assert that ShareViewer mounts
// after a successful unlock by checking for our stub's marker.
vi.mock('@/components/share/ShareViewer', () => ({
  ShareViewer: ({ presignedUrl }: { presignedUrl: string }) => (
    <div data-testid="share-viewer-stub">{presignedUrl}</div>
  ),
}))

const ORIGINAL_FETCH = global.fetch
const ORIGINAL_BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL

beforeEach(() => {
  process.env.NEXT_PUBLIC_BACKEND_URL = 'https://api.example.com'
})

afterEach(() => {
  global.fetch = ORIGINAL_FETCH
  if (ORIGINAL_BACKEND_URL === undefined) {
    delete process.env.NEXT_PUBLIC_BACKEND_URL
  } else {
    process.env.NEXT_PUBLIC_BACKEND_URL = ORIGINAL_BACKEND_URL
  }
  vi.restoreAllMocks()
})

describe('PasswordGate', () => {
  it('renders no scan-metadata fields before password is verified (D-09 / D-15)', async () => {
    const { PasswordGate } = await import('@/components/share/PasswordGate')
    render(<PasswordGate token="test-token-abc" />)
    // Zero metadata in the visible JSX before unlock.
    expect(screen.queryByText(/branch/i)).toBeNull()
    expect(screen.queryByText(/commit.?sha/i)).toBeNull()
    expect(screen.queryByText(/\bsource\b/i)).toBeNull()
    expect(screen.queryByText(/created.?at/i)).toBeNull()
    expect(screen.queryByText(/\bsummary\b/i)).toBeNull()
  })

  it('renders heading "This scan is password-protected"', async () => {
    const { PasswordGate } = await import('@/components/share/PasswordGate')
    render(<PasswordGate token="test-token-abc" />)
    expect(
      screen.getByText('This scan is password-protected'),
    ).toBeInTheDocument()
  })

  it('renders password input (type=password) and Unlock button', async () => {
    const { PasswordGate } = await import('@/components/share/PasswordGate')
    render(<PasswordGate token="test-token-abc" />)
    const pwd = screen.getByLabelText(/password/i) as HTMLInputElement
    expect(pwd.type).toBe('password')
    expect(screen.getByRole('button', { name: /unlock/i })).toBeInTheDocument()
  })

  it('renders data-testid="password-gate" wrapper', async () => {
    const { PasswordGate } = await import('@/components/share/PasswordGate')
    render(<PasswordGate token="test-token-abc" />)
    expect(screen.getByTestId('password-gate')).toBeInTheDocument()
  })

  it('renders "Made with InfraCanvas" wordmark', async () => {
    const { PasswordGate } = await import('@/components/share/PasswordGate')
    render(<PasswordGate token="test-token-abc" />)
    expect(screen.getByText(/made with/i)).toBeInTheDocument()
    expect(screen.getByText('InfraCanvas')).toBeInTheDocument()
  })

  it('on 401 from /unlock displays "Incorrect password."', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      status: 401,
      ok: false,
      headers: new Headers(),
      json: () => Promise.resolve({ detail: 'invalid_password' }),
    } as unknown as Response)

    const { PasswordGate } = await import('@/components/share/PasswordGate')
    render(<PasswordGate token="test-token-abc" />)

    fireEvent.change(screen.getByLabelText(/password/i), {
      target: { value: 'wrong-pass' },
    })
    fireEvent.click(screen.getByRole('button', { name: /unlock/i }))

    await waitFor(() =>
      expect(screen.getByText('Incorrect password.')).toBeInTheDocument(),
    )
  })

  it('on 429 with Retry-After: 120 shows "Too many attempts" and "2 minutes"', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      status: 429,
      ok: false,
      headers: new Headers({ 'Retry-After': '120' }),
      json: () => Promise.resolve({ detail: 'too_many_attempts' }),
    } as unknown as Response)

    const { PasswordGate } = await import('@/components/share/PasswordGate')
    render(<PasswordGate token="test-token-abc" />)

    fireEvent.change(screen.getByLabelText(/password/i), {
      target: { value: 'whatever' },
    })
    fireEvent.click(screen.getByRole('button', { name: /unlock/i }))

    await waitFor(() => {
      const msg = screen.getByRole('alert').textContent ?? ''
      expect(msg).toMatch(/too many attempts/i)
      expect(msg).toMatch(/2 minute/i)
    })
  })

  it('on 200 mounts ShareViewer with the presigned URL from response', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      status: 200,
      ok: true,
      headers: new Headers(),
      json: () =>
        Promise.resolve({
          scan_id: 'scan-001',
          presigned_get_url: 'https://r2.example.com/scan-001.json?sig=xyz',
          branch: 'main',
          commit_sha: 'abcdef1234567',
          created_at: '2026-04-28T10:00:00Z',
          summary_json: {
            score: 87,
            findings: { critical: 1, high: 2, medium: 0, info: 0 },
            drift: {},
            total_resources: 5,
          },
        }),
    } as unknown as Response)

    const { PasswordGate } = await import('@/components/share/PasswordGate')
    render(<PasswordGate token="test-token-abc" />)

    fireEvent.change(screen.getByLabelText(/password/i), {
      target: { value: 'correct-pass' },
    })
    fireEvent.click(screen.getByRole('button', { name: /unlock/i }))

    await waitFor(() => {
      const viewer = screen.getByTestId('share-viewer-stub')
      expect(viewer).toHaveTextContent('https://r2.example.com/scan-001.json?sig=xyz')
    })
  })
})
