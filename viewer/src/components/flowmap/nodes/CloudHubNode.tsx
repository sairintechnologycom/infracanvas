import { memo } from 'react'
import { Handle, Position, type NodeProps } from '@xyflow/react'
import type { ResourceNode as ResourceNodeData } from '../../../types'
import { useStore } from '../../../store'

const AWS_COLOR = '#FF9900'
const AZURE_COLOR = '#0078D4'

type CloudHubNodeProps = NodeProps & { data: ResourceNodeData }

function CloudHubNodeComponent({ data, selected }: CloudHubNodeProps) {
  const setSelectedNode = useStore((s) => s.setSelectedNode)
  const isAws = data.provider === 'aws'
  const color = isAws ? AWS_COLOR : AZURE_COLOR
  const routes = data.attributes.routes
  const attachments = data.attributes.attachments
  const attachmentCount = Array.isArray(attachments)
    ? (attachments as unknown[]).length
    : Array.isArray(routes)
    ? (routes as unknown[]).length
    : 0

  return (
    <div
      onClick={() => setSelectedNode(data)}
      style={{
        width: 200,
        height: 72,
        padding: '8px 12px',
        borderRadius: 8,
        background: '#FFFFFF',
        border: `1.5px solid ${color}`,
        boxShadow: selected
          ? '0 0 0 2px #3B82F6, 0 0 0 5px rgba(59,130,246,0.18)'
          : '0 1px 3px rgba(15,23,42,0.05)',
        display: 'flex',
        flexDirection: 'column',
        gap: 2,
        cursor: 'pointer',
      }}
    >
      <Handle type="target" position={Position.Left} className="!bg-slate-400 !w-2 !h-2" />
      <div style={{ fontSize: 12, fontWeight: 600, color: '#0F172A' }}>{data.name}</div>
      <div style={{ fontSize: 10, fontFamily: 'ui-monospace,monospace', color: '#64748B' }}>
        {data.region?.toUpperCase() ?? ''}
      </div>
      <div style={{ fontSize: 11, fontFamily: 'ui-monospace,monospace', color: '#64748B' }}>
        {attachmentCount} attachment{attachmentCount === 1 ? '' : 's'}
      </div>
      <Handle type="source" position={Position.Right} className="!bg-slate-400 !w-2 !h-2" />
    </div>
  )
}

export const CloudHubNodeMemo = memo(CloudHubNodeComponent)
export default CloudHubNodeMemo
