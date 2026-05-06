'use client'
import { useState } from 'react'
import type { WorkloadCost } from '@infracanvas/viewer'
import {
  TooltipProvider,
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from '@/components/ui/tooltip'

interface Props {
  workloads: WorkloadCost[]
}

export function WorkloadTable({ workloads }: Props) {
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set())

  if (workloads.length === 0) {
    return (
      <div className="text-sm text-slate-500 py-8 text-center">
        No cost data yet
      </div>
    )
  }

  function toggleRow(name: string) {
    setExpandedRows((prev) => {
      const next = new Set(prev)
      if (next.has(name)) next.delete(name)
      else next.add(name)
      return next
    })
  }

  return (
    <div data-testid="workload-table" className="mt-4 overflow-x-auto">
      <h2 className="text-base font-semibold text-slate-900 mb-3">Cost Allocation</h2>
      <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
        <table className="w-full">
          <thead className="bg-slate-50 border-b border-slate-200">
            <tr>
              {['Workload', 'Allocated / mo', 'Shared Resources', 'Details'].map((col) => (
                <th
                  key={col}
                  className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {workloads.map((wl) => {
              const isExpanded = expandedRows.has(wl.name)
              const sharedLabels =
                wl.line_items
                  .filter((i) => i.share_pct > 0)
                  .map((i) => i.label)
                  .join(' + ') || '—'

              return (
                <>
                  <tr
                    key={wl.name}
                    className="border-b border-slate-100 last:border-b-0 hover:bg-slate-50"
                  >
                    <td
                      className={[
                        'px-4 py-3 text-sm font-medium text-slate-900',
                        wl.name === 'untagged' ? 'italic text-slate-400' : '',
                      ]
                        .join(' ')
                        .trim()}
                    >
                      {wl.name}
                    </td>
                    <td className="px-4 py-3 font-mono text-sm tabular-nums text-slate-900 min-w-[120px]">
                      ${wl.total_monthly_usd.toFixed(2)}/mo
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-600">{sharedLabels}</td>
                    <td className="px-4 py-3 w-8">
                      <TooltipProvider>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <button
                              aria-label={`View cost breakdown for ${wl.name}`}
                              aria-expanded={isExpanded}
                              aria-controls={`detail-${wl.name}`}
                              onClick={() => toggleRow(wl.name)}
                              className="text-slate-400 hover:text-slate-700 transition-colors"
                            >
                              {isExpanded ? '▾' : '›'}
                            </button>
                          </TooltipTrigger>
                          <TooltipContent>View cost breakdown</TooltipContent>
                        </Tooltip>
                      </TooltipProvider>
                    </td>
                  </tr>
                  {isExpanded && (
                    <tr id={`detail-${wl.name}`} className="bg-slate-50">
                      <td colSpan={4} className="px-8 py-3">
                        <div className="space-y-1">
                          {wl.line_items.map((item) => (
                            <div
                              key={item.resource_id}
                              className="flex justify-between text-xs text-slate-600"
                            >
                              <span>{item.label}</span>
                              <span className="font-mono tabular-nums">
                                ${item.monthly_usd.toFixed(2)}
                                {item.share_pct > 0
                                  ? ` (${item.share_pct.toFixed(0)}%)`
                                  : ''}
                              </span>
                            </div>
                          ))}
                          {wl.line_items.length === 0 && (
                            <p className="text-xs text-slate-400">
                              No shared resources detected for this workload.
                            </p>
                          )}
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
