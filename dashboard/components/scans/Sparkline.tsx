'use client'

import { useRef, useState } from 'react'

interface Props {
  scores: number[] // up to 10 data points (score 0-100)
  dates: string[] // ISO date strings, same length as scores
  className?: string
}

function formatTooltipDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

export function Sparkline({ scores, dates, className = '' }: Props) {
  const [hoverIdx, setHoverIdx] = useState<number | null>(null)
  const svgRef = useRef<SVGSVGElement>(null)

  if (scores.length < 2) return null
  const W = 80
  const H = 24
  const PAD = 2
  const min = Math.min(...scores)
  const max = Math.max(...scores)
  const range = max - min || 1
  const pts = scores.map((s, i) => {
    const x = PAD + (i / (scores.length - 1)) * (W - PAD * 2)
    const y = H - PAD - ((s - min) / range) * (H - PAD * 2)
    return `${x.toFixed(1)},${y.toFixed(1)}`
  })
  const ptArr = pts.map(p => p.split(',').map(Number))
  const minIdx = scores.indexOf(min)
  const maxIdx = scores.indexOf(max)

  const handleMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    const svg = svgRef.current
    if (!svg) return
    const rect = svg.getBoundingClientRect()
    const width = rect.width || 1
    // Map cursor X to viewBox coordinate space
    const cursorVbX = ((e.clientX - rect.left) / width) * W
    // Find closest data index by x distance in viewBox space
    let closest = 0
    let closestDist = Infinity
    for (let i = 0; i < ptArr.length; i++) {
      const d = Math.abs(ptArr[i][0] - cursorVbX)
      if (d < closestDist) {
        closestDist = d
        closest = i
      }
    }
    setHoverIdx(closest)
  }

  const handleMouseLeave = () => setHoverIdx(null)

  return (
    <div className="relative">
      <svg
        ref={svgRef}
        viewBox={`0 0 ${W} ${H}`}
        preserveAspectRatio="none"
        className={`overflow-visible ${className}`}
        aria-hidden="true"
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
      >
        <polyline
          fill="none"
          stroke="currentColor"
          strokeWidth={1.5}
          points={pts.join(' ')}
          className="text-slate-400"
        />
        <circle cx={ptArr[minIdx][0]} cy={ptArr[minIdx][1]} r={2.5} className="fill-red-400" />
        <circle cx={ptArr[maxIdx][0]} cy={ptArr[maxIdx][1]} r={2.5} className="fill-green-400" />
        {hoverIdx !== null && (
          <circle
            cx={ptArr[hoverIdx][0]}
            cy={ptArr[hoverIdx][1]}
            r={2.5}
            className="fill-slate-900"
          />
        )}
      </svg>
      {hoverIdx !== null && dates[hoverIdx] && (
        <div
          className="absolute bg-slate-900 text-white text-xs px-2 py-1 rounded-sm pointer-events-none whitespace-nowrap"
          style={{ left: `${(ptArr[hoverIdx][0] / W) * 100}%`, top: -28 }}
        >
          Score {scores[hoverIdx]} · {formatTooltipDate(dates[hoverIdx])}
        </div>
      )}
    </div>
  )
}
