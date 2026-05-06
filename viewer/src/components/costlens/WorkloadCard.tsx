import type { WorkloadCost } from '../../types'

interface WorkloadCardProps {
  workload: WorkloadCost
}

export function WorkloadCard({ workload }: WorkloadCardProps) {
  const isUntagged = workload.name === 'untagged'

  return (
    <div
      aria-label={`Workload: ${workload.name}, $${workload.total_monthly_usd.toFixed(2)} per month`}
      style={{
        background: '#FFFFFF',
        border: '1px solid #E2E8F0',
        borderLeft: '4px solid #3B82F6',
        borderRadius: 8,
        padding: 16,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span
          style={{
            fontSize: 13,
            fontWeight: 600,
            color: isUntagged ? '#94A3B8' : '#0F172A',
            ...(isUntagged ? { fontStyle: 'italic' } : {}),
          }}
        >
          {workload.name}
        </span>
        <span
          style={{
            fontSize: 13,
            fontWeight: 600,
            color: '#0F172A',
            fontFamily: 'var(--font-mono)',
          }}
        >
          ${workload.total_monthly_usd.toFixed(2)}/mo
        </span>
      </div>

      {workload.line_items.length === 0 ? (
        <p style={{ fontSize: 11, color: '#94A3B8', marginTop: 8 }}>
          No shared resources detected for this workload.
        </p>
      ) : (
        <div style={{ marginTop: 8 }}>
          {workload.line_items.map((item) => (
            <div
              key={item.resource_id}
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                fontSize: 11,
                color: '#64748B',
                padding: '2px 0',
              }}
            >
              <span>{item.label}</span>
              <span style={{ fontFamily: 'var(--font-mono)' }}>
                ${item.monthly_usd.toFixed(2)}
                {item.share_pct > 0 ? ` (${item.share_pct.toFixed(0)}%)` : ''}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
