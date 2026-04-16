import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import type { ResourceNode } from '../types'

// Mock the store module so we can control gateMode
vi.mock('../store', () => ({
  useStore: vi.fn(),
}))

// Mock lucide-react icons used in DetailPanel
vi.mock('lucide-react', async (importOriginal) => {
  const actual = await importOriginal<typeof import('lucide-react')>()
  return {
    ...actual,
    Lock: () => <svg data-testid="lock-icon" />,
    X: () => <svg />,
    FileText: () => <svg />,
    Shield: () => <svg />,
    Code: () => <svg />,
    GitCompare: () => <svg />,
  }
})

// Mock ResourceIcon to avoid complex icon resolution
vi.mock('../components/icons/ResourceIcon', () => ({
  ResourceIcon: () => <div />,
}))

// Mock FindingCard to track renders
vi.mock('../components/FindingCard', () => ({
  FindingCard: ({ finding }: { finding: { title: string } }) => (
    <div data-testid="finding-card">{finding.title}</div>
  ),
}))

import { useStore } from '../store'
import { DetailPanel } from '../components/DetailPanel'

const mockSetSelectedNode = vi.fn()

const nodeWithFindings: ResourceNode = {
  id: 'aws_s3_bucket.main',
  type: 'aws_s3_bucket',
  name: 'main-bucket',
  provider: 'aws',
  module: '',
  region: 'us-east-1',
  group: '',
  attributes: {},
  dependencies: [],
  findings: [
    {
      rule_id: 'SEC-001',
      severity: 'critical',
      title: 'S3 Bucket Publicly Accessible',
      description: 'The S3 bucket allows public access',
      remediation: 'Enable S3 Block Public Access',
      evidence: { acl: 'public-read' },
    },
    {
      rule_id: 'SEC-002',
      severity: 'high',
      title: 'S3 Bucket Logging Disabled',
      description: 'Access logging is not enabled',
      remediation: 'Enable server access logging',
      evidence: {},
    },
    {
      rule_id: 'SEC-003',
      severity: 'high',
      title: 'S3 Bucket Versioning Disabled',
      description: 'Versioning is not enabled on this bucket',
      remediation: 'Enable versioning on the S3 bucket',
      evidence: {},
    },
  ],
  cost: { monthly_usd: 5.0, currency: 'USD', basis: 'storage' },
  drift: 'unchanged',
  position: { x: 0, y: 0 },
}

function setupStoreMock(gateMode: boolean) {
  const mockUseStore = vi.mocked(useStore)
  mockUseStore.mockImplementation((selector: (state: unknown) => unknown) => {
    const state = {
      selectedNode: nodeWithFindings,
      setSelectedNode: mockSetSelectedNode,
      gateMode,
    }
    return selector(state)
  })
}

describe('FreeGate (VWR-06)', () => {
  describe('when gateMode is true', () => {
    beforeEach(() => {
      vi.clearAllMocks()
      setupStoreMock(true)
    })

    it('renders gate overlay instead of FindingCard list', () => {
      render(<DetailPanel />)
      // Switch to Findings tab — use the button role to be specific
      const findingsTab = screen.getByRole('button', { name: /Findings \(3\)/i })
      findingsTab.click()

      // Gate CTA must appear
      expect(screen.getByText(/Unlock details/i)).toBeInTheDocument()
      // Lock icon must appear
      expect(screen.getByTestId('lock-icon')).toBeInTheDocument()
      // Finding cards must NOT appear
      expect(screen.queryAllByTestId('finding-card')).toHaveLength(0)
      // Finding titles must NOT appear as readable text
      expect(screen.queryByText('S3 Bucket Publicly Accessible')).not.toBeInTheDocument()
    })

    it('shows finding count and severity badges', () => {
      render(<DetailPanel />)
      const findingsTab = screen.getByRole('button', { name: /Findings \(3\)/i })
      findingsTab.click()

      // Finding count text
      expect(screen.getByText(/3 findings/i)).toBeInTheDocument()
      // Severity badges
      expect(screen.getByText(/1 critical/i)).toBeInTheDocument()
      expect(screen.getByText(/2 high/i)).toBeInTheDocument()
    })

    it('CTA links to https://infracanvas.dev/founding in new tab', () => {
      render(<DetailPanel />)
      const findingsTab = screen.getByRole('button', { name: /Findings \(3\)/i })
      findingsTab.click()

      const ctaLink = screen.getByRole('link', { name: /Unlock details/i })
      expect(ctaLink).toHaveAttribute('href', 'https://infracanvas.dev/founding')
      expect(ctaLink).toHaveAttribute('target', '_blank')
      expect(ctaLink).toHaveAttribute('rel', expect.stringContaining('noopener'))
    })

    it('blurred placeholders do not leak finding text to DOM', () => {
      render(<DetailPanel />)
      const findingsTab = screen.getByRole('button', { name: /Findings \(3\)/i })
      findingsTab.click()

      // Finding detail strings must not appear as readable DOM text
      expect(screen.queryByText('S3 Bucket Publicly Accessible')).not.toBeInTheDocument()
      expect(screen.queryByText('The S3 bucket allows public access')).not.toBeInTheDocument()
      expect(screen.queryByText('Enable S3 Block Public Access')).not.toBeInTheDocument()

      // Blurred placeholder elements with blur filter must exist
      const blurredElements = document.querySelectorAll('[style*="blur(4px)"]')
      expect(blurredElements.length).toBeGreaterThan(0)
    })
  })

  describe('when gateMode is false', () => {
    beforeEach(() => {
      vi.clearAllMocks()
      setupStoreMock(false)
    })

    it('renders FindingCard list, not gate overlay', () => {
      render(<DetailPanel />)
      const findingsTab = screen.getByRole('button', { name: /Findings \(3\)/i })
      findingsTab.click()

      // Gate CTA must NOT appear
      expect(screen.queryByText(/Unlock details/i)).not.toBeInTheDocument()
      // FindingCards must appear
      expect(screen.getAllByTestId('finding-card').length).toBeGreaterThan(0)
    })
  })
})
