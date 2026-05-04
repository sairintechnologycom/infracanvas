import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'

// Mock Clerk's useOrganization — InstallButton reads organization.id from it.
const useOrganizationMock = vi.fn()
vi.mock('@clerk/nextjs', () => ({
  useOrganization: () => useOrganizationMock(),
}))

import { InstallButton } from '@/components/integrations/InstallButton'

describe('InstallButton', () => {
  beforeEach(() => {
    useOrganizationMock.mockReset()
  })

  it('renders when an org is active', () => {
    useOrganizationMock.mockReturnValue({ organization: { id: 'org_abc' } })
    render(<InstallButton />)
    expect(screen.getByRole('button', { name: /install/i })).toBeInTheDocument()
  })

  it('returns null when no org', () => {
    useOrganizationMock.mockReturnValue({ organization: null })
    const { container } = render(<InstallButton />)
    expect(container.firstChild).toBeNull()
  })

  it('constructs install URL with state=clerkOrgId', () => {
    useOrganizationMock.mockReturnValue({ organization: { id: 'org_abc' } })
    const openSpy = vi.spyOn(window, 'open').mockImplementation(() => null)
    render(<InstallButton />)
    fireEvent.click(screen.getByRole('button', { name: /install/i }))
    expect(openSpy).toHaveBeenCalledWith(
      expect.stringContaining('/installations/new?state=org_abc'),
      '_blank',
      'noopener,noreferrer',
    )
    openSpy.mockRestore()
  })

  it('uses env var for slug', () => {
    useOrganizationMock.mockReturnValue({ organization: { id: 'org_abc' } })
    const openSpy = vi.spyOn(window, 'open').mockImplementation(() => null)
    render(<InstallButton />)
    fireEvent.click(screen.getByRole('button', { name: /install/i }))
    const urlArg = openSpy.mock.calls[0]?.[0] as string
    expect(urlArg).toMatch(/apps\/infracanvas-(dev|prod|test)/)
    openSpy.mockRestore()
  })
})
