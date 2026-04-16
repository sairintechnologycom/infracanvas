import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import type { ResourceNode as ResourceNodeData } from '../types';
import { AwsIcon } from './icons/AwsIcon';
import { severityColors, driftColors, getHighestSeverity } from '../lib/colors';
import { useStore } from '../store';

type ResourceNodeProps = NodeProps & {
  data: ResourceNodeData;
};

function ResourceNodeComponent({ data, selected }: ResourceNodeProps) {
  const setSelectedNode = useStore(s => s.setSelectedNode);
  const graphNodes = useStore(s => s.graph?.nodes);
  const highestSev = getHighestSeverity(data.findings);
  const findingCount = data.findings.length;
  const isShadow = data.drift === 'shadow';
  const borderColor = isShadow ? '#f59e0b' : (data.drift !== 'unchanged' ? driftColors[data.drift] : (selected ? '#60a5fa' : '#1e293b'));
  const typeLabel = data.type.replace(/^aws_/, '').replaceAll('_', ' ');

  // Resolve attached security groups from dependencies
  const securityGroups = (graphNodes ?? []).filter(
    n => n.type === 'aws_security_group' && data.dependencies.includes(n.id),
  );

  return (
    <div
      className="relative cursor-pointer"
      style={{ width: 180 }}
      onClick={() => setSelectedNode(data)}
    >
      <Handle type="target" position={Position.Top} className="!bg-slate-500 !border-slate-600 !w-2 !h-2" />

      <div
        className="rounded-lg p-3 transition-all duration-150"
        style={{
          background: 'rgba(15, 23, 42, 0.95)',
          border: `1.5px ${isShadow ? 'dashed' : 'solid'} ${borderColor}`,
          boxShadow: selected ? `0 0 12px ${borderColor}40` : '0 1px 3px rgba(0,0,0,0.4)',
          opacity: data.drift === 'deleted' ? 0.5 : 1,
        }}
      >
        {/* Finding badge */}
        {findingCount > 0 && highestSev && (
          <div
            className="absolute -top-2 -right-2 flex items-center justify-center rounded-full text-[10px] font-bold text-white"
            style={{
              width: 20, height: 20,
              background: severityColors[highestSev],
              boxShadow: `0 0 6px ${severityColors[highestSev]}80`,
            }}
          >
            {findingCount}
          </div>
        )}

        {/* Icon + name + type */}
        <div className="flex items-start gap-2">
          <div style={{
            width: 32, height: 32,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            flexShrink: 0,
          }}>
            <AwsIcon resourceType={data.type} size={28} />
          </div>
          <div className="min-w-0 flex-1">
            <div
              className="text-xs font-medium truncate"
              style={{ fontFamily: 'var(--font-mono)', color: '#e2e8f0' }}
              title={data.id}
            >
              {data.name}
            </div>
            <div className="text-[10px]" style={{ color: '#64748b' }}>
              {typeLabel}
            </div>
          </div>
        </div>

        {/* Security group badges */}
        {securityGroups.length > 0 && (
          <div style={{ display: 'flex', gap: 4, marginTop: 4, flexWrap: 'wrap' }}>
            {securityGroups.map(sg => (
              <span key={sg.id} style={{
                fontSize: 9, padding: '1px 6px', borderRadius: 3,
                background: 'rgba(239,68,68,0.15)', color: '#f87171',
                border: '0.5px solid rgba(239,68,68,0.3)',
              }}>
                {'\u{1F6E1}'} {sg.name}
              </span>
            ))}
          </div>
        )}

        {/* Cost label */}
        {data.cost.monthly_usd > 0 && (
          <div className="text-[10px] mt-1 text-right" style={{ color: '#94a3b8' }}>
            ${data.cost.monthly_usd.toFixed(0)}/mo
          </div>
        )}
      </div>

      <Handle type="source" position={Position.Bottom} className="!bg-slate-500 !border-slate-600 !w-2 !h-2" />

      {/* Shadow badge */}
      {isShadow && (
        <div className="text-center mt-0.5" style={{ fontSize: 9, color: '#f59e0b' }}>
          Shadow
        </div>
      )}
    </div>
  );
}

export const ResourceNodeMemo = memo(ResourceNodeComponent);
