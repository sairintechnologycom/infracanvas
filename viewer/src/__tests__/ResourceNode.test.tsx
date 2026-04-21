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

  test('renders Azure resource name', () => {
    const props = makeNodeProps({
      id: 'azurerm_storage_account.data',
      type: 'azurerm_storage_account',
      name: 'data',
      provider: 'azurerm',
    })
    render(<ResourceNodeMemo {...props} />)
    expect(screen.getByText('data')).toBeInTheDocument()
  })

  test('title-cases type label and strips provider prefix', () => {
    const props = makeNodeProps({
      id: 'azurerm_storage_account.data',
      type: 'azurerm_storage_account',
      name: 'data',
      provider: 'azurerm',
    })
    render(<ResourceNodeMemo {...props} />)
    expect(screen.getByText('Storage Account')).toBeInTheDocument()
  })

  test('renders azurerm resource icon as an svg', () => {
    const props = makeNodeProps({
      id: 'azurerm_virtual_network.vnet',
      type: 'azurerm_virtual_network',
      name: 'vnet',
      provider: 'azurerm',
    })
    const { container } = render(<ResourceNodeMemo {...props} />)
    expect(container.querySelector('svg')).toBeInTheDocument()
    expect(screen.getByText('Virtual Network')).toBeInTheDocument()
  })

  test('applies NEW badge for added drift', () => {
    const props = makeNodeProps({ drift: 'added' })
    render(<ResourceNodeMemo {...props} />)
    expect(screen.getByText('NEW')).toBeInTheDocument()
  })
})

describe('ResourceNode — Phase 5.1 badges', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setupStoreMock()
  })

  test('5.1-K: renders ⚠ unresolved marker when type is _infracanvas_unresolved_module', () => {
    const props = makeNodeProps({
      id: '_infracanvas_unresolved_module.broken',
      type: '_infracanvas_unresolved_module',
      name: 'broken',
      provider: 'unresolved',
      attributes: { source: '../../modules/broken', _parse_error: 'main.tf: invalid HCL' },
    })
    render(<ResourceNodeMemo {...props} />)
    const marker = screen.getByTestId('resource-node-unresolved-marker')
    expect(marker).toBeInTheDocument()
    expect(marker).toHaveTextContent('⚠')
  })

  test('5.1-L: does NOT render ⚠ marker for a normal resource type', () => {
    const props = makeNodeProps({ type: 'aws_vpc' })
    render(<ResourceNodeMemo {...props} />)
    expect(screen.queryByTestId('resource-node-unresolved-marker')).toBeNull()
  })

  test('5.1-M: renders ×? badge when attributes._unresolved_count is true', () => {
    const props = makeNodeProps({
      id: 'aws_subnet.public',
      type: 'aws_subnet',
      name: 'public',
      attributes: { _unresolved_count: true },
    })
    render(<ResourceNodeMemo {...props} />)
    const badge = screen.getByTestId('resource-node-unresolved-count-badge')
    expect(badge).toBeInTheDocument()
    expect(badge).toHaveTextContent('×?')
  })

  test('5.1-N: does NOT render ×? badge when _unresolved_count is absent', () => {
    const props = makeNodeProps({ type: 'aws_subnet', attributes: {} })
    render(<ResourceNodeMemo {...props} />)
    expect(screen.queryByTestId('resource-node-unresolved-count-badge')).toBeNull()
  })
})
