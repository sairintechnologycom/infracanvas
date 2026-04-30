import Link from 'next/link'
import { ArrowLeft } from 'lucide-react'
import type { ScanGetResp } from '@/lib/types'

interface Props {
  scan: ScanGetResp
}

function ScoreGradePill({ score }: { score: number }) {
  let grade: string
  let cls: string
  if (score >= 90) {
    grade = 'A'
    cls = 'bg-green-100 text-green-700'
  } else if (score >= 80) {
    grade = 'B+'
    cls = 'bg-sky-100 text-sky-700'
  } else if (score >= 70) {
    grade = 'C'
    cls = 'bg-amber-100 text-amber-700'
  } else if (score >= 60) {
    grade = 'D'
    cls = 'bg-orange-100 text-orange-700'
  } else {
    grade = 'F'
    cls = 'bg-red-100 text-red-700'
  }
  return (
    <span
      className={`inline-flex items-center justify-center w-7 h-6 rounded-sm text-xs font-semibold ${cls}`}
    >
      {grade}
    </span>
  )
}

function formatHeaderDate(iso: string): string {
  const d = new Date(iso)
  // "Apr 28, 2026 · 14:32 UTC" per UI-SPEC copywriting contract
  const opts: Intl.DateTimeFormatOptions = {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    timeZone: 'UTC',
  }
  const datePart = d.toLocaleDateString('en-US', opts)
  const timePart = d.toISOString().slice(11, 16)
  return `${datePart} · ${timePart} UTC`
}

export function MetadataHeader({ scan }: Props) {
  const findings = scan.summary_json?.findings
  const score = scan.summary_json?.score

  return (
    <div
      className="bg-slate-50 border-b border-slate-200 px-6 h-[52px] flex items-center gap-4 flex-shrink-0"
      data-testid="metadata-header"
    >
      {/* Left: back link */}
      <Link
        href="/scans"
        className="flex items-center gap-1 text-sm text-slate-500 hover:text-slate-900 whitespace-nowrap"
      >
        <ArrowLeft size={14} />
        Scans
      </Link>

      <span className="text-slate-300">|</span>

      {/* Center: scan metadata */}
      <div className="flex items-center gap-3 min-w-0 flex-1">
        <span className="text-sm text-slate-600 whitespace-nowrap">
          {formatHeaderDate(scan.created_at)}
        </span>
        {scan.branch && (
          <span className="font-mono text-sm text-slate-700 truncate max-w-[160px]">
            {scan.branch}
          </span>
        )}
        {scan.commit_sha && (
          <span className="font-mono text-xs text-slate-500 whitespace-nowrap">
            {'@'}
            {scan.commit_sha.slice(0, 7)}
          </span>
        )}
        {score !== undefined && (
          <>
            <ScoreGradePill score={score} />
            <span className="text-sm tabular-nums text-slate-700">{score}</span>
          </>
        )}
        {findings && (
          <span className="text-xs text-slate-500 whitespace-nowrap">
            <span
              className={
                findings.critical > 0
                  ? 'text-[color:var(--color-sev-critical,#ef4444)] font-semibold'
                  : ''
              }
              data-testid="header-critical-count"
            >
              {findings.critical}c
            </span>
            {' / '}
            <span
              className={
                findings.high > 0
                  ? 'text-[color:var(--color-sev-high,#f97316)] font-semibold'
                  : ''
              }
              data-testid="header-high-count"
            >
              {findings.high}h
            </span>
          </span>
        )}
      </div>
      {/* Action buttons (Compare, Share) live in the top-bar slot per RMD-05 —
          mounted by <ScanDetailActions/> on /scans/[id]. */}
    </div>
  )
}
