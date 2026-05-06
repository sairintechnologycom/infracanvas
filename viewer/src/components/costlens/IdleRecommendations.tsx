import type { IdleRecommendation } from '../../types'

interface IdleRecommendationsProps {
  recommendations: IdleRecommendation[]
}

export function IdleRecommendations({ recommendations }: IdleRecommendationsProps) {
  return (
    <div style={{ marginTop: 32 }}>
      <h3
        style={{
          fontSize: 12,
          fontWeight: 700,
          color: '#475569',
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
          marginBottom: 12,
          margin: '0 0 12px 0',
        }}
      >
        Idle / Oversized
      </h3>
      <ul role="list" style={{ display: 'flex', flexDirection: 'column', gap: 8, padding: 0, margin: 0, listStyle: 'none' }}>
        {recommendations.map((rec) => (
          <li
            key={rec.resource_id}
            role="listitem"
            style={{
              background: '#FFF7ED',
              border: '1px solid #FED7AA',
              borderRadius: 6,
              padding: '10px 14px',
              display: 'flex',
              flexDirection: 'row',
              justifyContent: 'space-between',
              alignItems: 'flex-start',
            }}
          >
            <div>
              <div
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: 11,
                  fontWeight: 600,
                  color: '#92400E',
                }}
              >
                {rec.resource_id}
              </div>
              <div style={{ fontSize: 11, color: '#78350F', marginTop: 2 }}>
                {rec.description}
              </div>
            </div>
            <span
              style={{
                fontSize: 11,
                fontWeight: 700,
                color: '#B45309',
                fontFamily: 'var(--font-mono)',
                whiteSpace: 'nowrap',
                marginLeft: 16,
              }}
            >
              ${rec.monthly_waste_usd.toFixed(2)} est. monthly waste
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}
