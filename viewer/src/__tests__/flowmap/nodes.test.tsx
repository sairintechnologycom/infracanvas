import { describe, test, expect } from 'vitest'
import { render } from '@testing-library/react'
import { ReactFlowProvider } from '@xyflow/react'
import type { ResourceNode } from '../../types'
import { CloudHubNodeMemo } from '../../components/flowmap/nodes/CloudHubNode'
import { RouterNodeMemo } from '../../components/flowmap/nodes/RouterNode'
import { FirewallNodeMemo } from '../../components/flowmap/nodes/FirewallNode'
import { DCSiteGroupNodeMemo } from '../../components/flowmap/nodes/DCSiteGroupNode'

function makeNode(id: string, type: string, provider = 'aws', attrs: Record<string, unknown> = {}): ResourceNode {
  return {
    id,
    type,
    name: id.split('.').pop() ?? id,
    provider,
    module: '',
    region: 'us-east-1',
    group: '',
    attributes: attrs,
    dependencies: [],
    findings: [],
    cost: { monthly_usd: 0, currency: 'USD', basis: '' },
    drift: 'unchanged',
    position: { x: 0, y: 0 },
  }
}

// Render a custom node in isolation — ReactFlowProvider is required because
// some nodes subscribe to internal ReactFlow zoom state via useStore.
// We render the component directly (not inside a <ReactFlow>) because the node
// components read their own `data` prop without needing the node-tree wiring.
function renderNode(Component: React.ComponentType<Record<string, unknown>>, data: unknown) {
  return render(
    <ReactFlowProvider>
      <Component
        id="test"
        type="test"
        data={data}
        selected={false}
        dragging={false}
        isConnectable={false}
        xPos={0}
        yPos={0}
        zIndex={0}
        positionAbsoluteX={0}
        positionAbsoluteY={0}
      />
    </ReactFlowProvider>,
  )
}

describe('CloudHubNode', () => {
  test('renders AWS TGW with name', () => {
    const data = makeNode('aws_ec2_transit_gateway.hybrid', 'aws_ec2_transit_gateway')
    const { container } = renderNode(CloudHubNodeMemo as unknown as React.ComponentType<Record<string, unknown>>, data)
    expect(container.textContent).toContain('hybrid')
  })

  test('renders Azure vHub with name', () => {
    const data = makeNode('azurerm_virtual_hub.core', 'azurerm_virtual_hub', 'azure')
    const { container } = renderNode(CloudHubNodeMemo as unknown as React.ComponentType<Record<string, unknown>>, data)
    expect(container.textContent).toContain('core')
  })
})

describe('RouterNode', () => {
  test('renders hostname and BGP dot', () => {
    const data = makeNode('router.dc-edge', 'router', 'dc', { bgp_state: 'Established', vendor: 'cisco' })
    const { container } = renderNode(RouterNodeMemo as unknown as React.ComponentType<Record<string, unknown>>, data)
    expect(container.textContent).toContain('dc-edge')
  })
})

describe('FirewallNode', () => {
  test('renders firewall name', () => {
    const data = makeNode('firewall.fw-1', 'aws_network_firewall', 'aws', {
      throughput_used_bps: 5_000_000_000,
      throughput_limit_bps: 10_000_000_000,
      ip_address: '10.0.0.1',
    })
    const { container } = renderNode(FirewallNodeMemo as unknown as React.ComponentType<Record<string, unknown>>, data)
    expect(container.textContent).toContain('fw-1')
  })

  test('hides gauge when attributes missing', () => {
    const data = makeNode('firewall.fw-2', 'aws_network_firewall')
    const { container } = renderNode(FirewallNodeMemo as unknown as React.ComponentType<Record<string, unknown>>, data)
    // No % sign when gauge absent
    expect(container.textContent).not.toMatch(/\d+%/)
  })
})

describe('DCSiteGroupNode', () => {
  test('renders placeholder copy when hasSites=false', () => {
    const { container } = renderNode(
      DCSiteGroupNodeMemo as unknown as React.ComponentType<Record<string, unknown>>,
      { label: 'On-Prem Data Centre', hasSites: false },
    )
    expect(container.textContent).toContain('DC Agent required')
  })

  test('does not render placeholder when hasSites=true', () => {
    const { container } = renderNode(
      DCSiteGroupNodeMemo as unknown as React.ComponentType<Record<string, unknown>>,
      { label: 'On-Prem Data Centre', hasSites: true },
    )
    expect(container.textContent).not.toContain('DC Agent required')
  })
})
