import { memo } from 'react'
import { Handle, Position, useStore as useReactFlowStore, type NodeProps } from '@xyflow/react'
import { ShieldCheck } from 'lucide-react'
import type { ResourceNode as ResourceNodeData } from '../../../types'
import { useViewerStoreOrSingleton } from '../../../store'

type FirewallNodeProps = NodeProps & { data: ResourceNodeData }

function FirewallNodeComponent({ data, selected }: FirewallNodeProps) {
  const setSelectedNode = useViewerStoreOrSingleton((s) => s.setSelectedNode)
  // ReactFlow internal zoom subscription — transform is [x, y, zoom]
  const zoom = useReactFlowStore((s) => s.transform[2])

  const used = Number(data.attributes.throughput_used_bps ?? 0)
  const limit = Number(data.attributes.throughput_limit_bps ?? 0)
  const hasGauge = used > 0 && limit > 0
  const percent = hasGauge ? Math.min(100, Math.round((used / limit) * 100)) : 0
  const gaugeColor = percent >= 80 ? '#EF4444' : percent >= 60 ? '#F59E0B' : '#22C55E'
  const showGauge = hasGauge && zoom >= 0.7

  return (
    <div
      onClick={() => setSelectedNode(data)}
      style={{
        width: 180,
        height: showGauge ? 84 : 64,
        padding: 10,
        borderRadius: 6,
        background: '#FFFFFF',
        border: '1.5px solid #DD344C',
        boxShadow: selected ? '0 0 0 2px #3B82F6' : 'none',
        display: 'flex',
        flexDirection: 'column',
        gap: 6,
        cursor: 'pointer',
      }}
    >
      <Handle type="target" position={Position.Left} className="!bg-slate-400 !w-2 !h-2" />
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <ShieldCheck size={20} color="#DD344C" />
        <div
          style={{
            fontSize: 12,
            fontWeight: 600,
            color: '#0F172A',
            flex: 1,
            minWidth: 0,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
          }}
        >
          {data.name}
        </div>
      </div>
      <div style={{ fontSize: 11, fontFamily: 'ui-monospace,monospace', color: '#64748B' }}>
        {String(data.attributes.ip_address ?? '')}
      </div>
      {showGauge && (
        <div
          title={`Firewall capacity: ${percent}% of ${(limit / 1e9).toFixed(1)} Gbps`}
          style={{ display: 'flex', alignItems: 'center', gap: 6 }}
        >
          <div
            style={{
              width: 140,
              height: 6,
              borderRadius: 3,
              background: '#F1F5F9',
              overflow: 'hidden',
            }}
          >
            <div
              style={{
                width: `${percent}%`,
                height: '100%',
                background: gaugeColor,
                transition: 'width 0.2s',
              }}
            />
          </div>
          <span style={{ fontSize: 10, fontWeight: 600, color: '#475569' }}>{percent}%</span>
        </div>
      )}
      <Handle type="source" position={Position.Right} className="!bg-slate-400 !w-2 !h-2" />
    </div>
  )
}

export const FirewallNodeMemo = memo(FirewallNodeComponent)
export default FirewallNodeMemo
