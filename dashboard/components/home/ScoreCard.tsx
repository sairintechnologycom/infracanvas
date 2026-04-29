import Link from 'next/link'
import type { ScanListItem } from '@/lib/types'

export interface GradeInfo {
  grade: string
  bgClass: string
  textClass: string
}

/**
 * Map a numeric score (0-100) to a letter grade and Tailwind classes for the
 * grade pill. Thresholds match Phase 1 scoring contract and 07-UI-SPEC.
 */
export function gradeInfo(score: number): GradeInfo {
  // Thresholds per 07-UI-SPEC §"Score-grade pills" table:
  //   A / A+ ≥ 90, B / B+ 80–89, C 70–79, D 60–69, F < 60.
  // The plan-frontmatter test expectations (95→A+, 87→B+, 75→B, 72→C, 65→D, 55→F)
  // align with this and with the existing ScansTable + MetadataHeader thresholds.
  if (score >= 95) return { grade: 'A+', bgClass: 'bg-green-100', textClass: 'text-green-700' }
  if (score >= 90) return { grade: 'A', bgClass: 'bg-green-100', textClass: 'text-green-700' }
  if (score >= 85) return { grade: 'B+', bgClass: 'bg-sky-100', textClass: 'text-sky-700' }
  if (score >= 80) return { grade: 'B', bgClass: 'bg-sky-100', textClass: 'text-sky-700' }
  if (score >= 70) return { grade: 'C', bgClass: 'bg-amber-100', textClass: 'text-amber-700' }
  if (score >= 60) return { grade: 'D', bgClass: 'bg-orange-100', textClass: 'text-orange-700' }
  return { grade: 'F', bgClass: 'bg-red-100', textClass: 'text-red-700' }
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
  const info = gradeInfo(score)
  const critCount = summary?.findings.critical ?? 0
  const highCount = summary?.findings.high ?? 0
  const driftTotal = summary
    ? Object.values(summary.drift).reduce((a, b) => a + b, 0)
    : 0

  return (
    <section
      className="bg-white border border-slate-200 rounded-lg p-6 flex items-center gap-8"
      data-testid="score-card"
    >
      {/* Col 1: grade + score */}
      <div className="flex flex-col items-center">
        <div className="flex items-center gap-3">
          <span
            className={`inline-flex items-center justify-center w-7 h-7 rounded-md text-sm font-semibold ${info.bgClass} ${info.textClass}`}
          >
            {info.grade}
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
