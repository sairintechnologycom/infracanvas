'use client'

interface Props {
  scores: number[] // up to 10 data points (score 0-100)
  className?: string
}

export function Sparkline({ scores, className = '' }: Props) {
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
  return (
    <svg
      width={W}
      height={H}
      className={`overflow-visible ${className}`}
      aria-hidden="true"
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
    </svg>
  )
}
