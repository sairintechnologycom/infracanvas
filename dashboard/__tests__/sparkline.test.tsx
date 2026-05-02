import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { Sparkline } from '@/components/scans/Sparkline'

const scores = [70, 75, 82, 88, 91]
const dates = ['2026-04-25', '2026-04-26', '2026-04-27', '2026-04-28', '2026-04-29']

describe('Sparkline wrapper width regression', () => {
  it('wrapper div has w-full so it stretches inside flex parents', () => {
    const { container } = render(<Sparkline scores={scores} dates={dates} />)
    const svg = container.querySelector('svg')!
    const wrapper = svg.parentElement!
    expect(wrapper.className).toMatch(/\bw-full\b/)
  })
})

describe('Sparkline hover tooltip (RMD-06)', () => {
  it('renders an svg', () => {
    const { container } = render(<Sparkline scores={scores} dates={dates} />)
    expect(container.querySelector('svg')).toBeInTheDocument()
  })

  it('shows tooltip on mousemove with Score {n} · {date}', () => {
    const { container } = render(<Sparkline scores={scores} dates={dates} />)
    const svg = container.querySelector('svg')!
    // jsdom mousemove with clientX/Y works; bounding rect default for jsdom is 0,0
    fireEvent.mouseMove(svg, { clientX: 50, clientY: 20 })
    // Tooltip text contains both 'Score' and the score literal
    expect(screen.getByText(/Score \d+ · /)).toBeInTheDocument()
  })

  it('hides tooltip on mouseleave', () => {
    const { container } = render(<Sparkline scores={scores} dates={dates} />)
    const svg = container.querySelector('svg')!
    fireEvent.mouseMove(svg, { clientX: 50, clientY: 20 })
    expect(screen.queryByText(/Score \d+ · /)).toBeInTheDocument()
    fireEvent.mouseLeave(svg)
    expect(screen.queryByText(/Score \d+ · /)).toBeNull()
  })

  it('tooltip has spec Tailwind classes', () => {
    const { container } = render(<Sparkline scores={scores} dates={dates} />)
    const svg = container.querySelector('svg')!
    fireEvent.mouseMove(svg, { clientX: 50, clientY: 20 })
    const tooltip = screen.getByText(/Score \d+ · /)
    const cls = tooltip.className
    expect(cls).toMatch(/bg-slate-900/)
    expect(cls).toMatch(/text-white/)
    expect(cls).toMatch(/text-xs/)
    expect(cls).toMatch(/px-2/)
    expect(cls).toMatch(/py-1/)
    expect(cls).toMatch(/rounded-sm/)
  })
})
