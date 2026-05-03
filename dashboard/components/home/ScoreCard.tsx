import Link from 'next/link'
import type { ScanListItem } from '@/lib/types'
import { gradeInfo } from '@/lib/grade'

function pillClasses(letter: string): string {
  if (letter === 'A+' || letter === 'A') return 'bg-green-100 text-green-700'
  if (letter === 'B+' || letter === 'B') return 'bg-sky-100 text-sky-700'
  if (letter === 'C') return 'bg-amber-100 text-amber-700'
  if (letter === 'D') return 'bg-orange-100 text-orange-700'
  return 'bg-red-100 text-red-700'
}

function formatTimestamp(iso: string): string {
  const d = new Date(iso)
  // e.g. "Apr 28, 2026 · 14:32 UTC"
  const monthDay = d.toLocaleString('en-US', {
    month: 'short',
    day: '2-digit',
    year: 'numeric',
    timeZone: 'UTC',
  })
  const hh = String(d.getUTCHours()).padStart(2, '0')
  const mm = String(d.getUTCMinutes()).padStart(2, '0')
  return `${monthDay} · ${hh}:${mm} UTC`
}

interface Props {
  scan: ScanListItem
}

export function ScoreCard({ scan }: Props) {
  const summary = scan.summary_json
  const score = summary?.score ?? 0
  const letter = gradeInfo(score).letter
  const pillCls = pillClasses(letter)
  const critCount = summary?.findings.critical ?? 0
  const highCount = summary?.findings.high ?? 0
  const driftTotal = summary
    ? Object.values(summary.drift).reduce((a, b) => a + b, 0)
    : 0

  return (
    <section
      className="bg-white border border-slate-200 rounded-lg p-6 flex flex-wrap items-center gap-x-10 gap-y-4"
      data-testid="score-card"
    >
      {/* Col 1: grade + score */}
      <div className="flex flex-col items-center">
        <div className="flex items-center gap-3">
          <span
            className={`inline-flex items-center justify-center w-7 h-7 rounded-md text-sm font-semibold ${pillCls}`}
          >
            {letter}
          </span>
          <span className="text-[28px] font-semibold tabular-nums text-slate-900">
            {summary ? score : '—'}
          </span>
        </div>
        <span className="text-xs text-slate-500 mt-1">Score</span>
      </div>

      {/* Col 2: finding counts */}
      <div className="flex items-center gap-6">
        <div className="flex flex-col items-center" data-testid="score-card-critical">
          <span className="text-base font-semibold text-sev-critical tabular-nums">
            {critCount}
          </span>
          <span className="text-xs text-slate-500 mt-1">Critical</span>
        </div>
        <div className="flex flex-col items-center" data-testid="score-card-high">
          <span className="text-base font-semibold text-sev-high tabular-nums">
            {highCount}
          </span>
          <span className="text-xs text-slate-500 mt-1">High</span>
        </div>
        <div className="flex flex-col items-center" data-testid="score-card-drift">
          <span className="text-base font-semibold text-sev-medium tabular-nums">
            {driftTotal}
          </span>
          <span className="text-xs text-slate-500 mt-1">Drift</span>
        </div>
      </div>

      {/* Col 3: metadata + open scan link */}
      <div className="ml-auto flex flex-col items-end text-sm">
        <span className="text-slate-700">{formatTimestamp(scan.created_at)}</span>
        <span className="font-mono text-xs text-slate-500 mt-1">
          {scan.branch ?? '—'}
          {scan.commit_sha ? ` @ ${scan.commit_sha.slice(0, 7)}` : ''}
        </span>
        <Link
          href={`/scans/${scan.id}`}
          className="text-xs text-amber-600 hover:underline mt-2"
        >
          Open scan →
        </Link>
      </div>
    </section>
  )
}
