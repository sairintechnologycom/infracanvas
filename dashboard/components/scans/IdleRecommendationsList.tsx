import type { IdleRecommendation } from '@infracanvas/viewer'

interface Props {
  recommendations: IdleRecommendation[]
}

export function IdleRecommendationsList({ recommendations }: Props) {
  return (
    <div data-testid="idle-recommendations-list" className="mt-12">
      <hr className="border-slate-200 mb-8" />
      <h2 className="text-base font-semibold text-slate-900 mb-3">
        Idle &amp; Oversized Recommendations
      </h2>
      <div className="mt-4 overflow-x-auto">
        <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
          <table className="w-full">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                {['Resource', 'Signal', 'Monthly Waste'].map((col) => (
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
              {recommendations.map((rec) => (
                <tr
                  key={rec.resource_id}
                  className="border-b border-slate-100 last:border-b-0 hover:bg-slate-50"
                >
                  <td className="px-4 py-3 text-sm font-mono text-slate-900">
                    {rec.resource_id}
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-600">{rec.description}</td>
                  <td className="px-4 py-3 font-mono text-sm font-semibold text-amber-600">
                    ${rec.monthly_waste_usd.toFixed(2)}/mo
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
