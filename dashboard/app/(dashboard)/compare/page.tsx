import Link from 'next/link'
import { GitCompare, ArrowRight } from 'lucide-react'

/**
 * /compare — landing page that explains compare is contextual from a scan.
 *
 * The actual diff route is /scans/compare?a={uuid}&b={uuid} (Plan 07-08).
 * Users land here from the sidebar nav and we route them to pick a scan.
 */
export default function CompareLandingPage() {
  return (
    <div className="max-w-2xl mx-auto px-8 py-16">
      <div className="bg-white border border-slate-200 rounded-lg p-8 flex flex-col items-center text-center gap-4">
        <GitCompare className="h-6 w-6 text-slate-500" />
        <h1 className="text-base font-semibold text-slate-900">Compare two scans</h1>
        <p className="text-sm text-slate-500 max-w-md">
          Pick a scan from your history, then click <span className="font-mono text-slate-700">Compare against…</span> in
          the header to choose a target. We&apos;ll show resource diffs side-by-side.
        </p>
        <Link
          href="/scans"
          className="mt-2 inline-flex items-center gap-1.5 bg-amber-400 hover:bg-amber-300 text-slate-900 text-sm font-medium px-4 py-2 rounded-md transition-colors"
        >
          Browse scans
          <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
    </div>
  )
}
