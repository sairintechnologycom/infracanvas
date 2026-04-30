'use client'
import { useEffect, useState, useMemo } from 'react'
import { useRouter } from 'next/navigation'
import * as Dialog from '@radix-ui/react-dialog'
import { Search, X } from 'lucide-react'
import type { ScanListItem, ScanListResp } from '@/lib/types'

interface Props {
  currentScanId: string
  /** Branch of the currently-open scan — drives the "Same branch" group. */
  currentBranch?: string
  isOpen: boolean
  onClose: () => void
}

/**
 * "Compare against…" picker modal opened from MetadataHeader.
 *
 * Flow:
 *   1. On open, fetch `GET /v1/scans?limit=25&sort=created_at&order=desc`.
 *   2. Filter out the currently-open scan (no self-compare).
 *   3. Group rows: "Same branch (latest first)" first, "Other branches" next.
 *   4. Search filters by commit_sha or branch (case-insensitive).
 *   5. Selecting a target scan + clicking Compare → router.push to
 *      `/scans/compare?a={current}&b={selected}`. The destination RSC
 *      validates UUIDs again (T-07-08-01 — defence in depth).
 */
export function ScanPickerModal({ currentScanId, currentBranch, isOpen, onClose }: Props) {
  const router = useRouter()
  const [scans, setScans] = useState<ScanListItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [query, setQuery] = useState('')

  useEffect(() => {
    if (!isOpen) return
    let cancelled = false
    setLoading(true)
    setError(null)
    setSelectedId(null)
    setQuery('')

    fetch('/api/scans-list?limit=25&sort=created_at&order=desc')
      .then(async (res) => {
        if (!res.ok) throw new Error(String(res.status))
        return (await res.json()) as ScanListResp
      })
      .then((data) => {
        if (cancelled) return
        const filtered = data.items.filter((s) => s.id !== currentScanId)
        setScans(filtered)
        setLoading(false)
      })
      .catch((err) => {
        if (cancelled) return
        setError(err instanceof Error ? err.message : 'Failed to load scans')
        setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [isOpen, currentScanId])

  const { sameBranch, otherBranches } = useMemo(() => {
    const q = query.trim().toLowerCase()
    const matchesQuery = (scan: ScanListItem) => {
      if (!q) return true
      return (
        (scan.commit_sha?.toLowerCase().includes(q) ?? false) ||
        (scan.branch?.toLowerCase().includes(q) ?? false)
      )
    }
    const visible = scans.filter(matchesQuery)
    if (!currentBranch) {
      return { sameBranch: [] as ScanListItem[], otherBranches: visible }
    }
    return {
      sameBranch: visible.filter((s) => s.branch === currentBranch),
      otherBranches: visible.filter((s) => s.branch !== currentBranch),
    }
  }, [scans, query, currentBranch])

  const handleCompare = () => {
    if (!selectedId) return
    router.push(`/scans/compare?a=${currentScanId}&b=${selectedId}`)
    onClose()
  }

  return (
    <Dialog.Root open={isOpen} onOpenChange={(o) => !o && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-slate-900/40 z-40" />
        <Dialog.Content
          data-testid="scan-picker-modal"
          className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-[min(560px,90vw)] max-h-[80vh] flex flex-col bg-white rounded-lg shadow-xl border border-slate-200"
        >
          {/* Header */}
          <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200">
            <Dialog.Title className="text-base font-semibold text-slate-900">
              Compare against…
            </Dialog.Title>
            <Dialog.Close
              aria-label="Close"
              className="text-slate-400 hover:text-slate-600 rounded-sm p-1"
            >
              <X className="h-4 w-4" />
            </Dialog.Close>
          </div>

          {/* Search */}
          <div className="px-5 py-3 border-b border-slate-200">
            <div className="relative">
              <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search by commit SHA or branch"
                className="w-full pl-9 pr-3 py-2 text-sm border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-amber-300 focus:border-amber-300"
                data-testid="scan-picker-search"
              />
            </div>
          </div>

          {/* List */}
          <div className="flex-1 overflow-y-auto px-2 py-2 min-h-[200px]">
            {loading && (
              <p className="text-sm text-slate-500 px-4 py-6 text-center">Loading scans…</p>
            )}
            {error && (
              <p className="text-sm text-red-600 px-4 py-6 text-center">
                Could not load scans: {error}
              </p>
            )}
            {!loading && !error && sameBranch.length === 0 && otherBranches.length === 0 && (
              <p className="text-sm text-slate-500 px-4 py-6 text-center">
                No other scans found in this team.
              </p>
            )}
            {!loading && !error && sameBranch.length > 0 && (
              <ScanGroup
                title="Same branch (latest first)"
                scans={sameBranch}
                selectedId={selectedId}
                onSelect={setSelectedId}
              />
            )}
            {!loading && !error && otherBranches.length > 0 && (
              <ScanGroup
                title={sameBranch.length > 0 ? 'Other branches' : 'Recent scans'}
                scans={otherBranches}
                selectedId={selectedId}
                onSelect={setSelectedId}
              />
            )}
          </div>

          {/* Footer */}
          <div className="flex items-center justify-end gap-2 px-5 py-3 border-t border-slate-200 bg-slate-50 rounded-b-lg">
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100 rounded-md"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleCompare}
              disabled={!selectedId}
              className="px-3 py-1.5 text-sm font-semibold rounded-md bg-amber-400 text-slate-900 hover:bg-amber-300 disabled:bg-slate-200 disabled:text-slate-400 disabled:cursor-not-allowed"
              data-testid="scan-picker-confirm"
            >
              Compare
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}

interface ScanGroupProps {
  title: string
  scans: ScanListItem[]
  selectedId: string | null
  onSelect: (id: string) => void
}

function ScanGroup({ title, scans, selectedId, onSelect }: ScanGroupProps) {
  return (
    <div className="py-2">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500 px-3 pb-1">
        {title}
      </h3>
      <ul>
        {scans.map((scan) => {
          const isSelected = selectedId === scan.id
          const created = new Date(scan.created_at)
          const dateLabel = created.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
            timeZone: 'UTC',
          })
          const score = scan.summary_json?.score
          return (
            <li key={scan.id}>
              <button
                type="button"
                onClick={() => onSelect(scan.id)}
                className={`w-full text-left px-3 py-2 rounded-md flex items-center gap-3 ${
                  isSelected ? 'bg-slate-100 font-semibold' : 'hover:bg-slate-50'
                }`}
              >
                <span className="text-xs text-slate-500 w-24 flex-shrink-0">{dateLabel}</span>
                {typeof score === 'number' && (
                  <span className="text-xs tabular-nums text-slate-700 w-8 flex-shrink-0">
                    {score}
                  </span>
                )}
                {scan.branch && (
                  <span className="font-mono text-xs text-slate-700 truncate max-w-[120px]">
                    {scan.branch}
                  </span>
                )}
                {scan.commit_sha && (
                  <span className="font-mono text-xs text-slate-500 ml-auto flex-shrink-0">
                    @{scan.commit_sha.slice(0, 7)}
                  </span>
                )}
              </button>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
