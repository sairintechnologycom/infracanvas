import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { WorkloadTable } from './WorkloadTable'
import type { WorkloadCost } from '@infracanvas/viewer'

const mockWorkloads: WorkloadCost[] = [
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
  { name: 'untagged', total_monthly_usd: 89.0, line_items: [] },
]

describe('WorkloadTable', () => {
  it('renders workload rows with correct data', () => {
    render(<WorkloadTable workloads={mockWorkloads} />)
    expect(screen.getByTestId('workload-table')).toBeTruthy()
    expect(screen.getByText('payments')).toBeTruthy()
    expect(screen.getByText('$412.00/mo')).toBeTruthy()
  })

  it('chevron expands detail row with aria-expanded', () => {
    render(<WorkloadTable workloads={mockWorkloads} />)
    const btn = screen.getByLabelText('View cost breakdown for payments')
    expect(btn.getAttribute('aria-expanded')).toBe('false')
    // detail row is not rendered before expansion
    expect(screen.queryByText('$18.25 (50%)')).toBeNull()
    fireEvent.click(btn)
    expect(btn.getAttribute('aria-expanded')).toBe('true')
    // expanded detail row shows the line item amount (unique to expanded state)
    expect(screen.getByText('$18.25 (50%)')).toBeTruthy()
  })

  it('renders empty state when no workloads', () => {
    render(<WorkloadTable workloads={[]} />)
    expect(screen.getByText(/No cost data yet/)).toBeTruthy()
  })

  it.todo('IdleRecommendationsList renders idle recommendations')
  it.todo('CostTab renders skeleton while loading')
})
