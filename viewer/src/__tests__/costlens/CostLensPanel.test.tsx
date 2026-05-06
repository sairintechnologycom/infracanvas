import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { CostLensPanel } from '../../components/costlens/CostLensPanel'
import type { CostLensData } from '../../types'

const mockData: CostLensData = {
  workloads: [
    {
      name: 'payments',
      total_monthly_usd: 412.0,
      line_items: [
        {
          resource_id: 'aws_ec2_transit_gateway.main',
          resource_type: 'aws_ec2_transit_gateway',
          label: 'TGW',
          monthly_usd: 18.25,
          share_pct: 50.0,
        },
      ],
    },
    {
      name: 'untagged',
      total_monthly_usd: 89.0,
      line_items: [],
    },
  ],
  shared_resources: [],
  recommendations: [
    {
      resource_id: 'aws_nat_gateway.main',
      resource_type: 'aws_nat_gateway',
      description: 'No routes reference this NAT GW',
      monthly_waste_usd: 32.85,
    },
  ],
}

describe('CostLensPanel', () => {
  it('renders empty state when costlens is null', () => {
    render(<CostLensPanel data={null} />)
    expect(screen.getByText('No cost allocation data')).toBeTruthy()
  })

  it('renders workload cards with correct names and amounts', () => {
    render(<CostLensPanel data={mockData} />)
    expect(screen.getByText('payments')).toBeTruthy()
    expect(screen.getByText(/412\.00\/mo/)).toBeTruthy()
  })

  it('renders untagged workload card', () => {
    render(<CostLensPanel data={mockData} />)
    expect(screen.getByText('untagged')).toBeTruthy()
  })

  it('renders idle recommendations section', () => {
    render(<CostLensPanel data={mockData} />)
    expect(screen.getByText('Idle / Oversized')).toBeTruthy()
    expect(screen.getByText('aws_nat_gateway.main')).toBeTruthy()
  })

  it('WorkloadCard shows correct line-item breakdown', () => {
    render(<CostLensPanel data={mockData} />)
    expect(screen.getByText('TGW')).toBeTruthy()
    expect(screen.getByText(/18\.25/)).toBeTruthy()
  })

  it('does not render idle section when no recommendations', () => {
    const dataNoRecs: CostLensData = { ...mockData, recommendations: [] }
    render(<CostLensPanel data={dataNoRecs} />)
    expect(screen.queryByText('Idle / Oversized')).toBeNull()
  })
})
