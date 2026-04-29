'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import type { ScanListItem } from '@/lib/types'
import { gradeInfo } from './ScoreCard'

interface Props {
  scans: ScanListItem[]
}

function formatRelativeOrAbsolute(iso: string): string {
  const d = new Date(iso)
  const now = Date.now()
  const ageMs = now - d.getTime()
  const day = 24 * 60 * 60 * 1000
  if (ageMs < 7 * day && ageMs >= 0) {
    const days = Math.floor(ageMs / day)
    if (days === 0) {
      const hours = Math.floor(ageMs / (60 * 60 * 1000))
      if (hours === 0) return 'just now'
      return `${hours}h ago`
    }
    return `${days}d ago`
  }
  return d.toISOString().slice(0, 10)
}

const COLUMNS = ['Date', 'Branch', 'Score', 'Crit', 'High'] as const

export function RecentScansTable({ scans }: Props) {
  const router = useRouter()
  const rows = scans.slice(0, 5)

  return (
    <section
      className="bg-white border border-slate-200 rounded-lg overflow-hidden"
      data-testid="recent-scans-table"
    >
      <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
        <h2 className="text-base font-semibold text-slate-900">Recent scans</h2>
        <Link
          href="/scans"
          className="text-sm text-amber-600 hover:underline"
        >
          View all →
        </Link>
      </div>

      {rows.length === 0 ? (
        <div className="p-8 text-center text-sm text-slate-500">
          No scans to show.
        </div>
      ) : (
        <table className="w-full">
          <thead className="bg-slate-50 border-b border-slate-200">
            <tr>
              {COLUMNS.map(col => (
                <th
                  key={col}
                  className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map(scan => {
              const score = scan.summary_json?.score
              const info = score !== undefined ? gradeInfo(score) : null
              const crit = scan.summary_json?.findings.critical ?? 0
              const high = scan.summary_json?.findings.high ?? 0
              return (
                <tr
                  key={scan.id}
                  data-testid="recent-scan-row"
                  onClick={() => router.push(`/scans/${scan.id}`)}
                  className="border-b border-slate-100 last:border-b-0 hover:bg-slate-50 cursor-pointer"
                >
                  <td className="px-4 py-3 font-mono text-sm tabular-nums text-slate-900 whitespace-nowrap">
                    {formatRelativeOrAbsolute(scan.created_at)}
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-700">
                    {scan.branch ?? '—'}
                  </td>
                  <td className="px-4 py-3">
                    {info && score !== undefined ? (
                      <div className="flex items-center gap-2">
                        <span
                          className={`inline-flex items-center justify-center w-6 h-6 rounded-sm text-xs font-semibold ${info.bgClass} ${info.textClass}`}
                        >
                          {info.grade}
                        </span>
                        <span className="text-sm tabular-nums">{score}</span>
                      </div>
                    ) : (
                      <span className="text-sm text-slate-400">—</span>
                    )}
                  </td>
                  <td
                    className={`px-4 py-3 text-sm tabular-nums ${crit > 0 ? 'text-sev-critical' : 'text-slate-400'}`}
                  >
                    {crit}
                  </td>
                  <td
                    className={`px-4 py-3 text-sm tabular-nums ${high > 0 ? 'text-sev-high' : 'text-slate-400'}`}
                  >
                    {high}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      )}
    </section>
  )
}
