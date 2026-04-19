import { memo } from 'react'
import { Building2 } from 'lucide-react'
import type { NodeProps } from '@xyflow/react'

type DCSiteGroupNodeData = { label?: string; hasSites?: boolean }
type DCSiteGroupNodeProps = NodeProps & { data: DCSiteGroupNodeData }

function DCSiteGroupNodeComponent({ data }: DCSiteGroupNodeProps) {
  const label = data.label ?? 'On-Prem Data Centre'
  return (
    <div
      style={{
        minWidth: 480,
        minHeight: 240,
        width: '100%',
        height: '100%',
        background: '#F8FAFC',
        border: '1.5px dashed #94A3B8',
        borderRadius: 8,
        position: 'relative',
        boxSizing: 'border-box',
      }}
    >
      {/* Label tab — AWS/Azure-style straddling top-left */}
      <div
        style={{
          position: 'absolute',
          top: -10,
          left: 14,
          display: 'flex',
          gap: 6,
          alignItems: 'center',
          background: '#FFFFFF',
          padding: '2px 8px',
          border: '1px solid #94A3B8',
          borderRadius: 4,
        }}
      >
        <Building2 size={14} color="#94A3B8" />
        <span style={{ fontSize: 11, fontWeight: 600, color: '#475569' }}>{label}</span>
      </div>
      {!data.hasSites && (
        <div
          style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            display: 'flex',
            flexDirection: 'column',
            gap: 10,
            alignItems: 'center',
            maxWidth: 320,
            textAlign: 'center',
          }}
        >
          <span
            style={{
              fontSize: 11,
              fontWeight: 500,
              padding: '4px 8px',
              borderRadius: 4,
              background: 'rgba(217,119,6,0.12)',
              color: '#D97706',
              border: '1px solid rgba(217,119,6,0.3)',
            }}
          >
            DC Agent required — lands in 3b
          </span>
          <p
            style={{
              fontSize: 11,
              fontWeight: 500,
              color: '#64748B',
              lineHeight: 1.45,
              margin: 0,
            }}
          >
            Physical routers, ASA/FTD firewalls, and Checkpoint policies appear here once the DC
            Collector Agent is installed.
          </p>
        </div>
      )}
    </div>
  )
}

export const DCSiteGroupNodeMemo = memo(DCSiteGroupNodeComponent)
export default DCSiteGroupNodeMemo
