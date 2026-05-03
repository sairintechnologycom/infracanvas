'use client'
import { useRouter } from 'next/navigation'
import { Terminal, Upload } from 'lucide-react'
import type { ScanListResp, ScanListItem } from '@/lib/types'
import { gradeInfo } from '@/lib/grade'
import { SeverityBadge } from './SeverityBadge'
import { Pagination } from './Pagination'

interface Props {
  data: ScanListResp
  currentParams: Record<string, string | undefined>
}

function ScoreGradePill({ score }: { score: number }) {
  const letter = gradeInfo(score).letter
  let cls: string
  if (letter === 'A+' || letter === 'A') cls = 'bg-green-100 text-green-700'
  else if (letter === 'B+' || letter === 'B') cls = 'bg-sky-100 text-sky-700'
  else if (letter === 'C') cls = 'bg-amber-100 text-amber-700'
  else if (letter === 'D') cls = 'bg-orange-100 text-orange-700'
  else cls = 'bg-red-100 text-red-700'
  return (
    <span
      className={`inline-flex items-center justify-center w-7 h-6 rounded-sm text-xs font-semibold ${cls}`}
    >
      {letter}
    </span>
  )
}

function SourceCell({ source }: { source: ScanListItem['source'] }) {
  if (source === 'cli') {
    return (
      <div className="flex items-center gap-1.5">
        <Terminal size={14} className="text-slate-500" />
        <span className="text-sm text-slate-600">CLI</span>
      </div>
    )
  }
  if (source === 'manual') {
    return (
      <div className="flex items-center gap-1.5">
        <Upload size={14} className="text-slate-500" />
        <span className="text-sm text-slate-600">Manual</span>
      </div>
    )
  }
  if (source === 'github_webhook') {
    return (
      <div className="flex items-center gap-1.5">
        <Upload size={14} className="text-slate-500" />
        <span className="text-sm text-slate-600">GitHub</span>
      </div>
    )
  }
  return <span className="text-sm text-slate-400">—</span>
}

function formatDate(iso: string): string {
  const d = new Date(iso)
  return d.toISOString().slice(0, 10) + ' ' + d.toISOString().slice(11, 16)
}

const COLUMNS = ['Date', 'Source', 'Commit', 'Branch', 'Score', 'Crit', 'High', 'Drift']

export function ScansTable({ data, currentParams }: Props) {
  const router = useRouter()
  const { items, next_cursor } = data

  if (items.length === 0) {
    const hasActiveFilters = Object.values(currentParams).some(Boolean)
    if (hasActiveFilters) {
      return (
        <div className="bg-white border border-slate-200 rounded-lg p-12 text-center mt-4">
          <p className="text-base font-semibold text-slate-900">No scans match your filters</p>
          <p className="text-sm text-slate-500 mt-2">
            Try widening the date range or clearing the branch filter.
          </p>
          <a
            href="/scans"
            className="text-sm text-slate-900 hover:text-slate-700 hover:underline mt-3 inline-block"
          >
            Clear all filters
          </a>
        </div>
      )
    }
    return (
      <div className="bg-white border border-slate-200 rounded-lg p-12 text-center mt-4">
        <p className="text-base font-semibold text-slate-900">No scans yet</p>
        <p className="text-sm text-slate-500 mt-2">
          Run a scan from the CLI to see your infrastructure here.
        </p>
        <code className="block font-mono text-sm bg-slate-100 px-4 py-3 rounded-md mt-4 text-left max-w-xs mx-auto">
          {'$ pip install infracanvas'}
          <br />
          {'$ infracanvas scan ./terraform --upload'}
        </code>
      </div>
    )
  }

  return (
    <div className="mt-4 overflow-x-auto">
      <div
        className="bg-white border border-slate-200 rounded-lg overflow-hidden"
        data-testid="scans-table"
      >
        <table className="w-full">
          <thead className="bg-slate-50 border-b border-slate-200">
            <tr>
              {COLUMNS.map(col => {
                const isSource = col === 'Source'
                return (
                  <th
                    key={col}
                    className={[
                      'px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500',
                      isSource ? 'hidden lg:table-cell' : '',
                    ].join(' ').trim()}
                  >
                    {col}
                  </th>
                )
              })}
            </tr>
          </thead>
          <tbody>
            {items.map(scan => (
              <tr
                key={scan.id}
                onClick={() => router.push(`/scans/${scan.id}`)}
                className="border-b border-slate-100 last:border-b-0 hover:bg-slate-50 cursor-pointer"
                data-testid="scan-row"
              >
                <td className="px-4 py-3 font-mono text-sm tabular-nums text-slate-900 whitespace-nowrap">
                  {formatDate(scan.created_at)}
                </td>
                <td className="hidden lg:table-cell px-4 py-3">
                  <SourceCell source={scan.source} />
                </td>
                <td className="px-4 py-3 font-mono text-sm text-slate-600">
                  {scan.commit_sha ? scan.commit_sha.slice(0, 7) : '—'}
                </td>
                <td className="px-4 py-3 text-sm text-slate-700">
                  {scan.branch ?? '—'}
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    {scan.summary_json ? (
                      <>
                        <ScoreGradePill score={scan.summary_json.score} />
                        <span className="text-sm tabular-nums">{scan.summary_json.score}</span>
                      </>
                    ) : (
                      <span className="text-slate-400 text-sm">—</span>
                    )}
                  </div>
                </td>
                <td className="px-4 py-3">
                  <SeverityBadge
                    severity="critical"
                    count={scan.summary_json?.findings.critical ?? 0}
                  />
                </td>
                <td className="px-4 py-3">
                  <SeverityBadge
                    severity="high"
                    count={scan.summary_json?.findings.high ?? 0}
                  />
                </td>
                <td className="px-4 py-3 text-sm tabular-nums text-slate-700">
                  {scan.summary_json
                    ? Object.values(scan.summary_json.drift).reduce((a, b) => a + b, 0)
                    : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Pagination nextCursor={next_cursor} currentParams={currentParams} />
    </div>
  )
}
