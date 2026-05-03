'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import type { ScanListItem } from '@/lib/types'

interface Props {
  scan: ScanListItem
}

interface TopFinding {
  rule_id: string
  title: string
  resource_id: string
}

interface TopFindingsResp {
  findings: TopFinding[]
}

export function TopFindings({ scan }: Props) {
  const [findings, setFindings] = useState<TopFinding[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(false)
    fetch(`/api/top-findings?scan_id=${scan.id}`)
      .then(async (res) => {
        if (!res.ok) throw new Error(`${res.status}`)
        return res.json() as Promise<TopFindingsResp>
      })
      .then((body) => {
        if (cancelled) return
        setFindings(body.findings)
        setLoading(false)
      })
      .catch(() => {
        if (cancelled) return
        setError(true)
        setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [scan.id])

  return (
    <section
      className="bg-white border border-slate-200 rounded-lg p-6"
      data-testid="top-findings"
    >
      <h2 className="text-base font-semibold text-slate-900">
        Top 3 critical findings
      </h2>

      {loading ? (
        <p className="mt-4 text-sm text-slate-500">Loading…</p>
      ) : error ? (
        <p className="mt-4 text-sm text-slate-500">
          Couldn&rsquo;t load critical findings.
        </p>
      ) : !findings || findings.length === 0 ? (
        <p className="mt-4 text-sm text-slate-600">
          No critical findings — nice work.
        </p>
      ) : (
        <div className="mt-4 space-y-3">
          {findings.map((f) => (
            <div
              key={`${f.rule_id}:${f.resource_id}`}
              className="border-l-4 border-sev-critical bg-red-50/40 p-4 rounded-sm"
              data-testid="top-finding-card"
            >
              <div className="flex items-center gap-2">
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-mono bg-slate-100 text-slate-700">
                  {f.rule_id}
                </span>
              </div>
              <p className="mt-2 text-sm font-medium text-slate-900">{f.title}</p>
              <p className="mt-1 text-xs text-slate-600 font-mono">{f.resource_id}</p>
              <Link
                href={`/scans/${scan.id}`}
                className="mt-2 inline-block text-xs text-amber-600 hover:underline"
              >
                Open scan →
              </Link>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
