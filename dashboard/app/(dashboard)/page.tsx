import { backendFetch } from '@/lib/backend'
import type { ScanListResp } from '@/lib/types'
import { ScoreCard } from '@/components/home/ScoreCard'
import { ScoreSparkline } from '@/components/home/ScoreSparkline'
import { TopFindings } from '@/components/home/TopFindings'
import { RecentScansTable } from '@/components/home/RecentScansTable'

/**
 * Home dashboard — D-04.
 *
 * Server component. Fetches the latest 10 scans server-side with the Clerk
 * Bearer token attached and composes the four home sections (latest score,
 * sparkline, top findings, recent scans table).
 *
 * Empty state (no scans yet) renders the CLI install hint per 07-UI-SPEC.
 */
export default async function HomePage() {
  const data = await backendFetch<ScanListResp>('/v1/scans?limit=10')

  if (data.items.length === 0) {
    return (
      <div className="max-w-md mx-auto p-8 bg-white border border-slate-200 rounded-lg text-center mt-20">
        <p className="text-base font-semibold text-slate-900">No scans yet</p>
        <p className="text-sm text-slate-500 mt-2">
          Run a scan from the CLI to see your infrastructure here.
        </p>
        <code className="block font-mono text-sm bg-slate-100 px-4 py-3 rounded-md mt-4 text-left">
          {'$ pip install infracanvas'}
          <br />
          {'$ infracanvas scan ./terraform --upload'}
        </code>
      </div>
    )
  }

  const latestScan = data.items[0]

  return (
    <div className="max-w-7xl mx-auto px-6 py-6 flex flex-col gap-4">
      <header className="flex items-baseline justify-between">
        <h1 className="text-xl font-semibold text-slate-900">Overview</h1>
        <p className="text-xs text-slate-500">
          Latest scan from <span className="font-mono">{latestScan.branch ?? 'main'}</span>
        </p>
      </header>
      <ScoreCard scan={latestScan} />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <ScoreSparkline scans={data.items} />
        <TopFindings scan={latestScan} />
      </div>
      <RecentScansTable scans={data.items} />
    </div>
  )
}
