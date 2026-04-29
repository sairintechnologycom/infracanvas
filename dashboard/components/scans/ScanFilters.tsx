'use client'
import { useCallback, useEffect, useRef, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { X } from 'lucide-react'

const SOURCE_OPTIONS = [
  { value: '', label: 'All sources' },
  { value: 'cli', label: 'CLI upload' },
  { value: 'manual', label: 'Manual' },
]

const SCORE_OPTIONS = [
  { value: '', label: 'Any score' },
  { value: '90', label: 'Below 90 (B+ or worse)' },
  { value: '80', label: 'Below 80 (C or worse)' },
  { value: '70', label: 'Below 70 (D or worse)' },
  { value: '60', label: 'Below 60 (F)' },
]

const DATE_OPTIONS = [
  { value: '', label: 'Last 7 days' },
  { value: '30d', label: 'Last 30 days' },
  { value: 'all', label: 'All time' },
]

function isoOffsetDays(days: number): string {
  const d = new Date()
  d.setDate(d.getDate() - days)
  return d.toISOString()
}

export function ScanFilters() {
  const router = useRouter()
  const sp = useSearchParams()
  const [branchInput, setBranchInput] = useState(sp.get('branch') ?? '')
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const pushFilter = useCallback(
    (updates: Record<string, string>) => {
      const next = new URLSearchParams(sp.toString())
      Object.entries(updates).forEach(([k, v]) => {
        if (v) next.set(k, v)
        else next.delete(k)
      })
      next.delete('cursor')
      router.replace(`/scans?${next}`)
    },
    [router, sp],
  )

  const handleBranchChange = (value: string) => {
    setBranchInput(value)
    if (debounceRef.current) clearTimeout(debounceRef.current)
    // debounce 300ms — see PATTERNS.md "ScanFilters.tsx"
    debounceRef.current = setTimeout(() => {
      pushFilter({ branch: value })
    }, 300)
  }

  useEffect(
    () => () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    },
    [],
  )

  const handleDateRange = (value: string) => {
    if (value === '30d') pushFilter({ from: isoOffsetDays(30), to: '' })
    else if (value === 'all') pushFilter({ from: '', to: '' })
    else pushFilter({ from: isoOffsetDays(7), to: '' })
  }

  const hasActiveFilters = ['branch', 'source', 'from', 'to', 'score_lt'].some(k => sp.get(k))

  return (
    <div
      className="bg-white border border-slate-200 rounded-lg p-4 flex gap-4 items-center flex-wrap sticky top-12 z-10"
      data-testid="scan-filters"
    >
      <select
        className="text-sm border border-slate-300 rounded-md px-3 py-1.5 bg-white text-slate-700"
        onChange={e => handleDateRange(e.target.value)}
        aria-label="Date range filter"
        data-testid="date-filter"
      >
        {DATE_OPTIONS.map(o => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>

      <input
        type="text"
        className="text-sm border border-slate-300 rounded-md px-3 py-1.5 bg-white text-slate-700 w-48"
        placeholder="Filter by branch"
        value={branchInput}
        onChange={e => handleBranchChange(e.target.value)}
        aria-label="Branch filter"
        data-testid="branch-filter"
      />

      <select
        className="text-sm border border-slate-300 rounded-md px-3 py-1.5 bg-white text-slate-700"
        value={sp.get('source') ?? ''}
        onChange={e => pushFilter({ source: e.target.value })}
        aria-label="Source filter"
        data-testid="source-filter"
      >
        {SOURCE_OPTIONS.map(o => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>

      <select
        className="text-sm border border-slate-300 rounded-md px-3 py-1.5 bg-white text-slate-700"
        value={sp.get('score_lt') ?? ''}
        onChange={e => pushFilter({ score_lt: e.target.value })}
        aria-label="Score threshold filter"
        data-testid="score-filter"
      >
        {SCORE_OPTIONS.map(o => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>

      {hasActiveFilters && (
        <button
          onClick={() => router.replace('/scans')}
          className="ml-auto flex items-center gap-1 text-sm text-slate-500 hover:text-slate-900"
          data-testid="clear-filters"
        >
          <X size={14} /> Clear filters
        </button>
      )}
    </div>
  )
}
