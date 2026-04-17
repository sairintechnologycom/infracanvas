import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import type { ResourceNode as ResourceNodeData } from '../types';
import { severityColors, driftColors, getHighestSeverity } from '../lib/colors';
import { detectProvider } from '../lib/providerTheme';
import { ServiceIcon } from './icons/ServiceIcon';
import { useStore } from '../store';

type ResourceNodeProps = NodeProps & {
  data: ResourceNodeData;
};

function ResourceNodeComponent({ data, selected }: ResourceNodeProps) {
  const setSelectedNode = useStore(s => s.setSelectedNode);
  const highestSev = getHighestSeverity(data.findings);
  const findingCount = data.findings.length;
  const isShadow = data.drift === 'shadow';
  const isNew = data.drift === 'added';
  const isChanged = data.drift === 'changed';
  const isDeleted = data.drift === 'deleted';

  const provider = data.provider === 'azurerm' ? 'azurerm' : detectProvider(data.type);

  const typeLabel = data.type
    .replace(/^aws_/, '')
    .replace(/^azurerm_/, '')
    .replaceAll('_', ' ')
    .replace(/\b\w/g, c => c.toUpperCase());

  const borderColor = selected
    ? '#3B82F6'
    : isShadow
    ? '#D97706'
    : isNew
    ? driftColors.added
    : isChanged
    ? driftColors.changed
    : '#E2E8F0';

  return (
    <div
      style={{ width: 160 }}
      className="relative cursor-pointer"
      onClick={() => setSelectedNode(data)}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="!bg-slate-400 !border-slate-500 !w-2 !h-2"
      />

      <div
        style={{
          background: '#FFFFFF',
          border: `${selected ? 2 : 1}px ${isShadow ? 'dashed' : 'solid'} ${borderColor}`,
          borderRadius: 8,
          padding: '14px 12px 10px 12px',
          opacity: isDeleted ? 0.45 : 1,
          boxShadow: selected
            ? '0 0 0 3px rgba(59,130,246,0.18), 0 4px 12px rgba(15,23,42,0.1)'
            : '0 1px 3px rgba(15,23,42,0.06)',
          transition: 'all 0.15s ease',
          textAlign: 'center',
          position: 'relative',
        }}
        onMouseEnter={e => {
          if (selected) return;
          (e.currentTarget as HTMLDivElement).style.boxShadow = '0 4px 12px rgba(15,23,42,0.12)';
          (e.currentTarget as HTMLDivElement).style.borderColor = '#CBD5E1';
        }}
        onMouseLeave={e => {
          if (selected) return;
          (e.currentTarget as HTMLDivElement).style.boxShadow = '0 1px 3px rgba(15,23,42,0.06)';
          (e.currentTarget as HTMLDivElement).style.borderColor = borderColor;
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 8 }}>
          <ServiceIcon provider={provider} type={data.type} size={44} />
        </div>

        <div
          style={{
            fontSize: 13,
            fontWeight: 700,
            color: '#0F172A',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            lineHeight: 1.25,
          }}
          title={data.id}
        >
          {data.name}
        </div>
        <div
          style={{
            fontSize: 10.5,
            fontWeight: 500,
            color: '#64748B',
            letterSpacing: '0.2px',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            marginTop: 2,
          }}
        >
          {typeLabel}
        </div>

        {(data.cost.monthly_usd > 0 || isNew || isChanged) && (
          <div style={{ display: 'flex', justifyContent: 'center', gap: 6, marginTop: 6 }}>
            {data.cost.monthly_usd > 0 && (
              <span
                style={{
                  fontSize: 10,
                  fontFamily: 'ui-monospace, monospace',
                  color: '#16A34A',
                  fontWeight: 600,
                }}
              >
                ${data.cost.monthly_usd.toFixed(0)}/mo
              </span>
            )}
            {isNew && (
              <span
                style={{
                  fontSize: 8,
                  padding: '1px 5px',
                  borderRadius: 3,
                  background: 'rgba(34,197,94,0.12)',
                  color: '#15803D',
                  fontWeight: 700,
                  border: '1px solid rgba(34,197,94,0.3)',
                }}
              >
                NEW
              </span>
            )}
            {isChanged && (
              <span
                style={{
                  fontSize: 8,
                  padding: '1px 5px',
                  borderRadius: 3,
                  background: 'rgba(234,179,8,0.12)',
                  color: '#A16207',
                  fontWeight: 700,
                  border: '1px solid rgba(234,179,8,0.3)',
                }}
              >
                CHG
              </span>
            )}
          </div>
        )}

        {findingCount > 0 && highestSev && (
          <div
            style={{
              position: 'absolute',
              top: -6,
              right: -6,
              minWidth: 20,
              height: 20,
              padding: '0 6px',
              borderRadius: 10,
              background: severityColors[highestSev],
              color: '#ffffff',
              fontSize: 11,
              fontWeight: 800,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: `0 1px 4px ${severityColors[highestSev]}66, 0 0 0 2px #FFFFFF`,
            }}
          >
            {findingCount}
          </div>
        )}
      </div>

      <Handle
        type="source"
        position={Position.Bottom}
        className="!bg-slate-400 !border-slate-500 !w-2 !h-2"
      />

      {isShadow && (
        <div style={{ textAlign: 'center', marginTop: 2, fontSize: 9, color: '#D97706' }}>
          shadow
        </div>
      )}
    </div>
  );
}

export const ResourceNodeMemo = memo(ResourceNodeComponent);
