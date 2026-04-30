import type { ScanListItem } from '@/lib/types'
import { Sparkline } from '@/components/scans/Sparkline'

interface Props {
  scans: ScanListItem[]
}

/**
 * Score-over-time sparkline strip for the home dashboard.
 *
 * Reuses the handrolled SVG `<Sparkline/>` component from Plan 07-06. Scores
 * are extracted from each scan's `summary_json.score` (skipping null), and
 * the array is reversed so oldest → newest left-to-right (the API returns
 * scans newest-first).
 */
export function ScoreSparkline({ scans }: Props) {
  // Pair score + created_at, drop scans without a numeric score, take last 10,
  // then reverse so oldest → newest reads left-to-right.
  const pairs = scans
    .map(s => ({ score: s.summary_json?.score, date: s.created_at }))
    .filter((p): p is { score: number; date: string } => typeof p.score === 'number')
    .slice(0, 10)
    .reverse()
  const points = pairs.map(p => p.score)
  const dates = pairs.map(p => p.date)

  return (
    <section
      className="bg-white border border-slate-200 rounded-lg p-6"
      data-testid="score-sparkline"
    >
      <h2 className="text-base font-semibold text-slate-900">
        Score over last 10 scans
      </h2>
      <div className="mt-4 h-[64px] flex items-center text-slate-700">
        {points.length >= 2 ? (
          <Sparkline scores={points} dates={dates} className="w-full h-full" />
        ) : (
          <p className="text-sm text-slate-500">
            Need at least 2 scans to render trend.
          </p>
        )}
      </div>
    </section>
  )
}
