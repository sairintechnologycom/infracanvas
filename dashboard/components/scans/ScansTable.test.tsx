import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { SourceCell } from './ScansTable'

describe('SourceCell', () => {
  it('renders Auto-scan for source=webhook', () => {
    render(<SourceCell source="webhook" />)
    expect(screen.getByText('Auto-scan')).toBeTruthy()
  })

  it('does not render Auto-scan for source=github', () => {
    render(<SourceCell source="github" />)
    expect(screen.queryByText('Auto-scan')).toBeNull()
  })
})
