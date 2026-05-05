import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { MetadataHeader } from './MetadataHeader'

const baseScan = {
  id: 'abc',
  created_at: '2026-05-05T10:00:00Z',
  status: 'ready',
  source: 'github',
  branch: 'main',
  commit_sha: 'abc1234567890',
  summary_json: { score: 90, findings: { critical: 0, high: 0 } },
}

describe('MetadataHeader', () => {
  it('shows Auto-scan badge when source is webhook', () => {
    render(<MetadataHeader scan={{ ...baseScan, source: 'webhook' } as any} />)
    expect(screen.getByTestId('auto-scan-badge')).toBeTruthy()
    expect(screen.getByText('Auto-scan')).toBeTruthy()
  })

  it('does not show Auto-scan badge when source is github', () => {
    render(<MetadataHeader scan={baseScan as any} />)
    expect(screen.queryByTestId('auto-scan-badge')).toBeNull()
  })
})
