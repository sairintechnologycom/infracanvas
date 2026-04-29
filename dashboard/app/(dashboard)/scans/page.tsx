import { Suspense } from 'react'
import { backendFetch } from '@/lib/backend'
import type { ScanListResp } from '@/lib/types'
import { ScansTable } from '@/components/scans/ScansTable'
import { ScanFilters } from '@/components/scans/ScanFilters'

interface PageProps {
  searchParams: Promise<{
    branch?: string
    source?: string
    from?: string
    to?: string
    score_lt?: string
    cursor?: string
    sort?: string
    order?: string
  }>
}

export default async function ScansPage({ searchParams }: PageProps) {
  const sp = await searchParams // MUST await — Next.js 15 breaking change

  const qs = new URLSearchParams()
  if (sp.branch)   qs.set('search', sp.branch)
  if (sp.source)   qs.set('source', sp.source)
  if (sp.from)     qs.set('created_after', sp.from)
  if (sp.to)       qs.set('created_before', sp.to)
  if (sp.score_lt) qs.set('score_lt', sp.score_lt)
  if (sp.cursor)   qs.set('cursor', sp.cursor)
  if (sp.sort)     qs.set('sort', sp.sort)
  if (sp.order)    qs.set('order', sp.order)
  qs.set('limit', '25')

  const data = await backendFetch<ScanListResp>(`/v1/scans?${qs}`)

  return (
    <div className="max-w-7xl mx-auto px-8 py-8">
      <div className="flex items-center gap-3 mb-6">
        <h1 className="text-base font-semibold text-slate-900">Scans</h1>
        <span className="text-xs text-slate-500">{data.items.length} loaded</span>
      </div>
      <ScanFilters />
      <Suspense fallback={<ScansTableSkeleton />}>
        <ScansTable data={data} currentParams={sp} />
      </Suspense>
    </div>
  )
}

function ScansTableSkeleton() {
  return (
    <div className="bg-white border border-slate-200 rounded-lg overflow-hidden mt-4">
      {Array.from({ length: 10 }).map((_, i) => (
        <div
          key={i}
          className="h-12 border-b border-slate-100 animate-pulse bg-slate-100 last:border-b-0"
        />
      ))}
    </div>
  )
}
