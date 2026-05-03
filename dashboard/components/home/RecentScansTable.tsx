'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import type { ScanListItem } from '@/lib/types'
import { gradeInfo } from '@/lib/grade'

function pillClasses(letter: string): string {
  if (letter === 'A+' || letter === 'A') return 'bg-green-100 text-green-700'
  if (letter === 'B+' || letter === 'B') return 'bg-sky-100 text-sky-700'
  if (letter === 'C') return 'bg-amber-100 text-amber-700'
  if (letter === 'D') return 'bg-orange-100 text-orange-700'
  return 'bg-red-100 text-red-700'
}

interface Props {
  scans: ScanListItem[]
}

/**
 * Voice-rules relative-date formatter (UI-SPEC §"Voice rules"):
 *   - < 1 hour:                 'Just now'
 *   - exactly 1 hour ago:       '1 hour ago' (singular)
 *   - 2..23 hours ago:          'X hours ago' (full word, plural)
 *   - 1 calendar day ago:       'Yesterday'
 *   - older:                    'Apr 22' (Intl.DateTimeFormat en-US, short month + day)
 */
export function formatRelativeDate(iso: string, now: Date = new Date()): string {
  const then = new Date(iso)
  const diffMs = now.getTime() - then.getTime()
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60))

  if (diffHours < 1) return 'Just now'
  if (diffHours < 24) return diffHours === 1 ? '1 hour ago' : `${diffHours} hours ago`

  // calendar-day diff (compare midnights so 'Yesterday' is robust to time-of-day)
  const startOfNow = new Date(now)
  startOfNow.setHours(0, 0, 0, 0)
  const startOfThen = new Date(then)
  startOfThen.setHours(0, 0, 0, 0)
  const diffDays = Math.round(
    (startOfNow.getTime() - startOfThen.getTime()) / (1000 * 60 * 60 * 24),
  )

  if (diffDays === 1) return 'Yesterday'
  // older: 'Apr 22' format
  return then.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
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
          className="text-sm text-slate-900 hover:text-slate-700 hover:underline"
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
              const letter = score !== undefined ? gradeInfo(score).letter : null
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
                    {formatRelativeDate(scan.created_at)}
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-700">
                    {scan.branch ?? '—'}
                  </td>
                  <td className="px-4 py-3">
                    {letter && score !== undefined ? (
                      <div className="flex items-center gap-2">
                        <span
                          className={`inline-flex items-center justify-center w-6 h-6 rounded-sm text-xs font-semibold ${pillClasses(letter)}`}
                        >
                          {letter}
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
