'use client'
import { useRouter, useSearchParams } from 'next/navigation'
import { ChevronLeft, ChevronRight } from 'lucide-react'

interface Props {
  nextCursor: string | null
  currentParams: Record<string, string | undefined>
}

// Cursor-based pagination: read next_cursor from props, encode as `cursor` URL param.
// Prev is enabled iff a cursor is currently in the URL.
export function Pagination({ nextCursor, currentParams }: Props) {
  const router = useRouter()
  const sp = useSearchParams()
  const hasPrev = Boolean(sp.get('cursor'))

  const navigate = (cursor: string | null) => {
    const next = new URLSearchParams()
    Object.entries(currentParams).forEach(([k, v]) => {
      if (k !== 'cursor' && v) next.set(k, v)
    })
    if (cursor) next.set('cursor', cursor)
    router.push(`/scans?${next}`)
  }

  if (!hasPrev && !nextCursor) return null

  return (
    <div
      className="bg-slate-50 border border-t-0 border-slate-200 rounded-b-lg px-6 py-3 flex items-center justify-end gap-2"
      data-testid="pagination"
    >
      <button
        onClick={() => navigate(null)}
        disabled={!hasPrev}
        className="flex items-center gap-1 px-3 py-1.5 text-sm border border-slate-300 rounded-md text-slate-600 hover:bg-slate-100 disabled:opacity-40 disabled:cursor-not-allowed"
        aria-label="Previous page"
      >
        <ChevronLeft size={14} /> Prev
      </button>
      <button
        onClick={() => navigate(nextCursor)}
        disabled={!nextCursor}
        className="flex items-center gap-1 px-3 py-1.5 text-sm border border-slate-300 rounded-md text-slate-600 hover:bg-slate-100 disabled:opacity-40 disabled:cursor-not-allowed"
        aria-label="Next page"
      >
        Next <ChevronRight size={14} />
      </button>
    </div>
  )
}
