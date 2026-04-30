'use client'
import { useCallback, useEffect, useRef, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import type { DateRange } from 'react-day-picker'
import { X } from 'lucide-react'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Calendar } from '@/components/ui/calendar'

const SOURCE_OPTIONS = [
  { value: 'all', label: 'All sources' },
  { value: 'cli', label: 'CLI upload' },
  { value: 'manual', label: 'Manual' },
]

const SCORE_OPTIONS = [
  { value: 'any', label: 'Any score' },
  { value: '90', label: 'Below 90 (B+ or worse)' },
  { value: '80', label: 'Below 80 (C or worse)' },
  { value: '70', label: 'Below 70 (D or worse)' },
  { value: '60', label: 'Below 60 (F)' },
]

const DATE_OPTIONS = [
  { value: '7d', label: 'Last 7 days' },
  { value: '30d', label: 'Last 30 days' },
  { value: 'all', label: 'All time' },
  { value: 'custom', label: 'Custom range…' },
]

function isoOffsetDays(days: number): string {
  const d = new Date()
  d.setDate(d.getDate() - days)
  return d.toISOString()
}

function isoDate10(d: Date): string {
  return d.toISOString().slice(0, 10)
}

export function ScanFilters() {
  const router = useRouter()
  const sp = useSearchParams()
  const [branchInput, setBranchInput] = useState(sp.get('branch') ?? '')
  const [dateChoice, setDateChoice] = useState<string>(() => {
    if (sp.get('from') && sp.get('to')) return 'custom'
    return '7d'
  })
  const [range, setRange] = useState<DateRange | undefined>(() => {
    const fromStr = sp.get('from')
    const toStr = sp.get('to')
    if (fromStr && toStr) {
      return { from: new Date(fromStr), to: new Date(toStr) }
    }
    return undefined
  })
  const [customOpen, setCustomOpen] = useState(false)
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
    setDateChoice(value)
    if (value === '30d') pushFilter({ from: isoOffsetDays(30), to: '' })
    else if (value === 'all') pushFilter({ from: '', to: '' })
    else if (value === 'custom') {
      // Open the popover; do not push filter yet — wait for range selection.
      setCustomOpen(true)
    } else pushFilter({ from: isoOffsetDays(7), to: '' })
  }

  const handleSourceChange = (value: string) => {
    pushFilter({ source: value === 'all' ? '' : value })
  }

  const handleScoreChange = (value: string) => {
    pushFilter({ score_lt: value === 'any' ? '' : value })
  }

  const onRangeSelect = (r: DateRange | undefined) => {
    setRange(r)
    if (r?.from && r?.to) {
      pushFilter({ from: r.from.toISOString(), to: r.to.toISOString() })
      setCustomOpen(false)
    }
  }

  const hasActiveFilters = ['branch', 'source', 'from', 'to', 'score_lt'].some(k => sp.get(k))

  const sourceValue = sp.get('source') ?? 'all'
  const scoreValue = sp.get('score_lt') ?? 'any'

  return (
    <div
      className="bg-white border border-slate-200 rounded-lg p-4 flex gap-4 items-center flex-wrap sticky top-12 z-10"
      data-testid="scan-filters"
    >
      <Select value={dateChoice} onValueChange={handleDateRange}>
        <SelectTrigger
          className="w-44 text-sm"
          aria-label="Date range filter"
          data-testid="date-filter"
        >
          <SelectValue placeholder="Last 7 days" />
        </SelectTrigger>
        <SelectContent>
          {DATE_OPTIONS.map(o => (
            <SelectItem key={o.value} value={o.value}>
              {o.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {dateChoice === 'custom' && (
        <Popover open={customOpen} onOpenChange={setCustomOpen}>
          <PopoverTrigger asChild>
            <button
              type="button"
              className="text-sm border border-slate-300 rounded-md px-3 py-1.5 bg-white text-slate-700"
              data-testid="custom-range-trigger"
            >
              {range?.from
                ? `${isoDate10(range.from)} → ${range.to ? isoDate10(range.to) : '…'}`
                : 'Pick range'}
            </button>
          </PopoverTrigger>
          <PopoverContent className="w-auto p-0" align="start">
            <Calendar
              mode="range"
              numberOfMonths={2}
              selected={range}
              onSelect={onRangeSelect}
            />
          </PopoverContent>
        </Popover>
      )}

      <input
        type="text"
        className="text-sm border border-slate-300 rounded-md px-3 py-1.5 bg-white text-slate-700 w-48"
        placeholder="Filter by branch"
        value={branchInput}
        onChange={e => handleBranchChange(e.target.value)}
        aria-label="Branch filter"
        data-testid="branch-filter"
      />

      <Select value={sourceValue} onValueChange={handleSourceChange}>
        <SelectTrigger
          className="w-44 text-sm"
          aria-label="Source filter"
          data-testid="source-filter"
        >
          <SelectValue placeholder="All sources" />
        </SelectTrigger>
        <SelectContent>
          {SOURCE_OPTIONS.map(o => (
            <SelectItem key={o.value} value={o.value}>
              {o.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select value={scoreValue} onValueChange={handleScoreChange}>
        <SelectTrigger
          className="w-56 text-sm"
          aria-label="Score threshold filter"
          data-testid="score-filter"
        >
          <SelectValue placeholder="Any score" />
        </SelectTrigger>
        <SelectContent>
          {SCORE_OPTIONS.map(o => (
            <SelectItem key={o.value} value={o.value}>
              {o.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

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
