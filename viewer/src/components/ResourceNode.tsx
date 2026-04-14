import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import type { ResourceNode as ResourceNodeData } from '../types';
import { ResourceIcon } from './icons/ResourceIcon';
import { severityColors, driftColors, getHighestSeverity, getResourceColor } from '../lib/colors';
import { useStore } from '../store';

type ResourceNodeProps = NodeProps & {
  data: ResourceNodeData;
};

function ResourceNodeComponent({ data, selected }: ResourceNodeProps) {
  const setSelectedNode = useStore(s => s.setSelectedNode);
  const highestSev = getHighestSeverity(data.findings);
  const findingCount = data.findings.length;
  const borderColor = data.drift !== 'unchanged' ? driftColors[data.drift] : (selected ? getResourceColor(data.type) : '#1e293b');
  const typeLabel = data.type.replace(/^aws_/, '').replaceAll('_', ' ');

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
          background: '#111827',
          border: `1.5px solid ${borderColor}`,
          boxShadow: selected ? `0 0 12px ${borderColor}40` : '0 1px 4px #0003',
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

        {/* Icon + type chip */}
        <div className="flex items-center gap-2 mb-1.5">
          <ResourceIcon resourceType={data.type} size={24} />
          <span
            className="text-[10px] font-medium px-1.5 py-0.5 rounded"
            style={{
              background: `${getResourceColor(data.type)}20`,
              color: getResourceColor(data.type),
            }}
          >
            {typeLabel}
          </span>
        </div>

        {/* Resource name */}
        <div
          className="text-xs font-medium truncate"
          style={{ fontFamily: 'var(--font-mono)', color: '#e2e8f0' }}
          title={data.id}
        >
          {data.name}
        </div>

        {/* Cost label */}
        {data.cost.monthly_usd > 0 && (
          <div className="text-[10px] mt-1 text-right" style={{ color: '#94a3b8' }}>
            ${data.cost.monthly_usd.toFixed(0)}/mo
          </div>
        )}
      </div>

      <Handle type="source" position={Position.Bottom} className="!bg-slate-500 !border-slate-600 !w-2 !h-2" />
    </div>
  );
}

export const ResourceNodeMemo = memo(ResourceNodeComponent);
