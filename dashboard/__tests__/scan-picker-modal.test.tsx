import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

// Stub out next/navigation so the modal's useRouter doesn't blow up in jsdom.
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn() }),
}))

// Stub backendFetch — modal calls /v1/scans on open.
vi.mock('@/lib/backend', () => ({
  backendFetch: vi.fn().mockResolvedValue({
    items: [
      {
        id: 's2',
        branch: 'main',
        commit_sha: 'b2c3d4e',
        created_at: '2026-04-27T10:00:00Z',
        summary_json: { score: 88 },
      },
    ],
    total: 1,
  }),
}))

const SOURCE = readFileSync(
  join(__dirname, '..', 'components', 'scans', 'ScanPickerModal.tsx'),
  'utf8',
)

import { ScanPickerModal } from '@/components/scans/ScanPickerModal'

beforeEach(() => {
  // Suppress jsdom navigation noise
})

afterEach(() => {
  vi.clearAllMocks()
})

describe('ScanPickerModal — shadcn Dialog migration (RMD-01)', () => {
  it('does NOT import from @radix-ui/react-dialog (raw Radix usage removed)', () => {
    expect(SOURCE).not.toMatch(/from\s+['"]@radix-ui\/react-dialog['"]/)
  })

  it('imports Dialog from shadcn primitive', () => {
    expect(SOURCE).toMatch(/from\s+['"]@\/components\/ui\/dialog['"]/)
  })

  it('uses ring-slate-400 (NOT ring-amber-*)', () => {
    expect(SOURCE).not.toMatch(/ring-amber/)
    expect(SOURCE).toMatch(/ring-slate-400/)
  })

  it('renders search input when open', async () => {
    render(<ScanPickerModal isOpen onClose={() => {}} currentScanId="s1" />)
    const input = await screen.findByPlaceholderText(/search/i)
    expect(input).toBeInTheDocument()
  })

  it('calls onClose when Escape pressed (shadcn Dialog forwards to onOpenChange)', async () => {
    const onClose = vi.fn()
    render(<ScanPickerModal isOpen onClose={onClose} currentScanId="s1" />)
    // Wait for content to mount
    await screen.findByPlaceholderText(/search/i)
    fireEvent.keyDown(document.body, { key: 'Escape', code: 'Escape' })
    await waitFor(() => expect(onClose).toHaveBeenCalled())
  })
})
