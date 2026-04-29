import Link from 'next/link'
import { backendFetch } from '@/lib/backend'
import { isUUID } from '@/lib/utils'
import type { ResourceDiff } from '@/lib/types'
import { CompareLayout } from '@/components/compare/CompareLayout'

interface PageProps {
  searchParams: Promise<{ a?: string; b?: string }>
}

/**
 * /scans/compare?a={uuid}&b={uuid}  — RSC entry for two-scan compare.
 *
 * Validation flow (T-07-08-01 — never trust user-controlled URL):
 *   1. Resolve searchParams (Next.js 15 — Pitfall 1, must be awaited).
 *   2. UUID-regex both `a` and `b`. If either fails, render 400 card and DO
 *      NOT touch the backend.
 *   3. Call the compare endpoint via the auth'd backend wrapper (D-11). On
 *      Error('404'), render the standard 404 card per UI-SPEC copywriting
 *      contract — D-18 says cross-team requests return 404 (not 403) so the
 *      dashboard treats 404 uniformly without leaking team/scan existence.
 *   4. On success, render <CompareLayout/> client boundary. The RSC does NOT
 *      fetch presigned URLs (D-08 / Pitfall 2 — presigned URL TTL <=300s,
 *      may expire before JS hydrates) — CompareViewerPair fetches them
 *      client-side on mount.
 */
export default async function ComparePage({ searchParams }: PageProps) {
  const { a, b } = await searchParams

  if (!isUUID(a) || !isUUID(b)) {
    return (
      <div
        data-testid="error-400"
        className="flex flex-col items-center justify-center h-full gap-3 px-6 py-12"
      >
        <h1 className="text-lg font-semibold text-slate-900">Invalid compare URL</h1>
        <p className="text-sm text-slate-500 text-center max-w-md">
          Both scan IDs must be valid UUIDs. Open a scan from the list and use the
          {' '}<span className="font-mono">Compare</span>{' '}button on the header to start a comparison.
        </p>
        <Link
          href="/scans"
          className="text-sm text-amber-600 hover:underline"
        >
          Back to scans
        </Link>
      </div>
    )
  }

  let diff: ResourceDiff
  try {
    diff = await backendFetch<ResourceDiff>(`/v1/scans/${a}/compare/${b}`)
  } catch (err) {
    const status = err instanceof Error ? err.message : ''
    if (status === '404') {
      return (
        <div
          data-testid="error-404"
          className="flex flex-col items-center justify-center h-full gap-3 px-6 py-12"
        >
          <h1 className="text-lg font-semibold text-slate-900">Scan not found</h1>
          <p className="text-sm text-slate-500 text-center max-w-md">
            This scan may have been deleted, or you may not have access to it.
          </p>
          <Link
            href="/scans"
            className="text-sm text-amber-600 hover:underline"
          >
            Back to scans
          </Link>
        </div>
      )
    }
    return (
      <div
        data-testid="error-5xx"
        className="flex flex-col items-center justify-center h-full gap-3 px-6 py-12"
      >
        <h1 className="text-lg font-semibold text-slate-900">Compare failed</h1>
        <p className="text-sm text-slate-500 text-center max-w-md">
          The compare service returned an error{status ? ` (${status})` : ''}. Try again in a moment.
        </p>
        <Link href="/scans" className="text-sm text-amber-600 hover:underline">
          Back to scans
        </Link>
      </div>
    )
  }

  return <CompareLayout diff={diff} scanAId={a} scanBId={b} />
}
