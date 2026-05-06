import type { CostLensData } from '@infracanvas/viewer'
import { WorkloadTable } from '@/components/scans/WorkloadTable'
import { IdleRecommendationsList } from '@/components/scans/IdleRecommendationsList'

interface Props {
  data: CostLensData | null
}

export function CostTab({ data }: Props) {
  if (!data) {
    return (
      <div
        className="flex items-center justify-center h-full text-sm text-slate-500"
        aria-live="polite"
      >
        No cost data yet. Run{' '}
        <code className="mx-1 px-1 bg-slate-100 rounded text-xs font-mono">
          infracanvas scan
        </code>{' '}
        to generate cost allocation. Make sure{' '}
        <code className="mx-1 px-1 bg-slate-100 rounded text-xs font-mono">
          costlens.workload_tag_key
        </code>{' '}
        is set in{' '}
        <code className="mx-1 px-1 bg-slate-100 rounded text-xs font-mono">
          infracanvas.yaml
        </code>
        .
      </div>
    )
  }
  return (
    <div className="p-6 space-y-8">
      <WorkloadTable workloads={data.workloads} />
      {data.recommendations.length > 0 && (
        <IdleRecommendationsList recommendations={data.recommendations} />
      )}
    </div>
  )
}
