import { DollarSign } from 'lucide-react'
import type { CostLensData } from '../../types'
import { WorkloadCard } from './WorkloadCard'
import { IdleRecommendations } from './IdleRecommendations'

interface CostLensPanelProps {
  data: CostLensData | null
}

export function CostLensPanel({ data }: CostLensPanelProps) {
  if (data === null) {
    return (
      <div
        role="status"
        aria-live="polite"
        style={{
          flex: 1,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: '#FAFBFC',
        }}
      >
        <div
          style={{
            textAlign: 'center',
            padding: 40,
            maxWidth: 360,
          }}
        >
          <DollarSign size={40} color="#94A3B8" style={{ margin: '0 auto 16px' }} />
          <h2
            style={{
              fontSize: 16,
              fontWeight: 600,
              color: '#0F172A',
              margin: '0 0 8px 0',
            }}
          >
            No cost allocation data
          </h2>
          <p style={{ fontSize: 13, color: '#475569', margin: 0 }}>
            Re-run with the latest CLI version to collect shared cost allocation data.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: 24, background: '#FAFBFC' }}>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
          gap: 16,
        }}
      >
        {data.workloads.map((workload) => (
          <WorkloadCard key={workload.name} workload={workload} />
        ))}
      </div>

      {data.recommendations.length > 0 && (
        <div style={{ marginTop: 48 }}>
          <IdleRecommendations recommendations={data.recommendations} />
        </div>
      )}
    </div>
  )
}
