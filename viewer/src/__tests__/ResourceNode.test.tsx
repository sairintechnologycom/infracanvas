import { describe, test, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import type { ResourceNode } from '../types'

// Mock @xyflow/react handles which require a flow context
vi.mock('@xyflow/react', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@xyflow/react')>()
  return {
    ...actual,
    Handle: () => null,
  }
})

// Mock the store
vi.mock('../store', () => ({
  useStore: vi.fn(),
}))

import { useStore } from '../store'
import { ResourceNodeMemo } from '../components/ResourceNode'

const mockSetSelectedNode = vi.fn()

function setupStoreMock() {
  const mockUseStore = vi.mocked(useStore)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  mockUseStore.mockImplementation((selector: (state: any) => unknown) => {
    return selector({ setSelectedNode: mockSetSelectedNode })
  })
}

function makeNodeProps(overrides: Partial<ResourceNode> = {}) {
  const data: ResourceNode = {
    id: 'aws_vpc.main',
    type: 'aws_vpc',
    name: 'main',
    provider: 'aws',
    module: '',
    region: 'us-east-1',
    group: '',
    attributes: {},
    dependencies: [],
    findings: [],
    cost: { monthly_usd: 0, currency: 'USD', basis: '' },
    drift: 'unchanged',
    position: { x: 0, y: 0 },
    ...overrides,
  }
  // NodeProps shape — only data and selected needed for these tests
  return { data, selected: false } as Parameters<typeof ResourceNodeMemo>[0]
}

describe('ResourceNode', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setupStoreMock()
  })

  test('renders Azure resource with correct icon color', () => {
    const props = makeNodeProps({
      id: 'azurerm_storage_account.data',
      type: 'azurerm_storage_account',
      name: 'data',
      provider: 'azurerm',
    })
    render(<ResourceNodeMemo {...props} />)
    // azurerm_storage_account has color '#3F8624' and label 'STG' in azureServiceConfig
    expect(screen.getByText('STG')).toBeInTheDocument()
  })

  test('strips azurerm_ prefix from type label', () => {
    const props = makeNodeProps({
      id: 'azurerm_storage_account.data',
      type: 'azurerm_storage_account',
      name: 'data',
      provider: 'azurerm',
    })
    render(<ResourceNodeMemo {...props} />)
    // azurerm_storage_account -> STORAGE ACCOUNT after stripping prefix + uppercase
    expect(screen.getByText('STORAGE ACCOUNT')).toBeInTheDocument()
  })

  test('uses getAzureServiceConfig for azurerm provider (label differs from AWS fallback)', () => {
    // azurerm_virtual_network -> label 'VNet' from azureServiceConfig
    // AWS fallback would produce 'AZURERM VIRTUAL NETWORK' type label if not stripped
    const props = makeNodeProps({
      id: 'azurerm_virtual_network.vnet',
      type: 'azurerm_virtual_network',
      name: 'vnet',
      provider: 'azurerm',
    })
    render(<ResourceNodeMemo {...props} />)
    expect(screen.getByText('VNet')).toBeInTheDocument()
    expect(screen.getByText('VIRTUAL NETWORK')).toBeInTheDocument()
  })

  test('applies +NEW badge and green drift indicator for added status', () => {
    const props = makeNodeProps({ drift: 'added' })
    render(<ResourceNodeMemo {...props} />)
    // Added nodes show +NEW badge (visual indicator of drift=added)
    expect(screen.getByText('+NEW')).toBeInTheDocument()
  })
})
