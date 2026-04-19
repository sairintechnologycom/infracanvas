import { memo } from 'react'
import { Handle, Position, type NodeProps } from '@xyflow/react'
import { Router } from 'lucide-react'
import type { ResourceNode as ResourceNodeData } from '../../../types'
import { useStore } from '../../../store'

type RouterNodeProps = NodeProps & { data: ResourceNodeData }

function RouterNodeComponent({ data, selected }: RouterNodeProps) {
  const setSelectedNode = useStore((s) => s.setSelectedNode)
  const bgpState = String(data.attributes.bgp_state ?? '') || 'unknown'
  const dotColor =
    bgpState === 'Established'
      ? '#22C55E'
      : bgpState === 'Idle' || bgpState === 'Active'
      ? '#F59E0B'
      : bgpState === 'Failed'
      ? '#EF4444'
      : '#CBD5E1'

  return (
    <div
      onClick={() => setSelectedNode(data)}
      style={{
        width: 160,
        height: 64,
        padding: '8px 12px',
        borderRadius: 6,
        background: '#FFFFFF',
        border: '1px solid #CBD5E1',
        boxShadow: selected ? '0 0 0 2px #3B82F6' : 'none',
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        cursor: 'pointer',
        position: 'relative',
      }}
    >
      <Handle type="target" position={Position.Left} className="!bg-slate-400 !w-2 !h-2" />
      <Router size={24} color="#475569" />
      <div style={{ display: 'flex', flexDirection: 'column', minWidth: 0, flex: 1 }}>
        <div style={{ fontSize: 10, fontFamily: 'ui-monospace,monospace', color: '#64748B' }}>
          {String(data.attributes.vendor ?? '')}
        </div>
        <div
          style={{
            fontSize: 12,
            fontWeight: 600,
            color: '#0F172A',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {data.name}
        </div>
      </div>
      <span
        title={`BGP: ${bgpState}`}
        style={{
          position: 'absolute',
          top: 6,
          right: 6,
          width: 6,
          height: 6,
          borderRadius: 3,
          background: dotColor,
        }}
      />
      <Handle type="source" position={Position.Right} className="!bg-slate-400 !w-2 !h-2" />
    </div>
  )
}

export const RouterNodeMemo = memo(RouterNodeComponent)
export default RouterNodeMemo
