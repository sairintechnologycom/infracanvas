import Link from 'next/link'
import type { ScanListItem } from '@/lib/types'

interface Props {
  scan: ScanListItem
}

/**
 * Renders a summary of the latest scan's critical findings on the home dashboard.
 *
 * NOTE: The list endpoint (GET /v1/scans?limit=10) returns `summary_json.findings`
 * as a count map (`{ critical, high, medium, info }`), not the full Finding
 * objects (rule_id, title, resource_id) that 07-UI-SPEC §"/" item 3 originally
 * contemplated. To render rule-id/title/resource-id we would need to download
 * the full per-scan JSON from R2, which the home dashboard intentionally avoids
 * (10× R2 fetches per page load = D-17 violation).
 *
 * Resolution (Rule 1 deviation): show the count + a CTA to open the scan
 * detail page where the full findings list lives. When count is 0, render the
 * "well done" green pill per UI-SPEC item 3.
 */
export function TopFindings({ scan }: Props) {
  const summary = scan.summary_json
  const critCount = summary?.findings.critical ?? 0

  return (
    <section
      className="bg-white border border-slate-200 rounded-lg p-6"
      data-testid="top-findings"
    >
      <h2 className="text-base font-semibold text-slate-900">
        Top 3 critical findings
      </h2>

      {critCount === 0 ? (
        <div className="mt-4 flex">
          <span className="bg-green-100 text-green-700 text-sm px-3 py-1.5 rounded-full">
            0 critical findings — well done
          </span>
        </div>
      ) : (
        <div className="mt-4 border-l-4 border-sev-critical bg-red-50/40 p-4 rounded-sm">
          <p className="text-sm font-semibold text-slate-900">
            <span data-testid="top-findings-critical-count">{critCount}</span>{' '}
            critical {critCount === 1 ? 'finding' : 'findings'} in the latest scan
          </p>
          <p className="text-xs text-slate-500 mt-1">
            Per-finding details (rule, title, resource) load with the full scan
            graph.
          </p>
          <Link
            href={`/scans/${scan.id}`}
            className="text-xs text-amber-600 hover:underline mt-2 inline-block"
          >
            Open scan →
          </Link>
        </div>
      )}
    </section>
  )
}
