import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import type { ResourceNode as ResourceNodeData } from '../types';
import { AwsIcon } from './icons/AwsIcon';
import { severityColors, driftColors, getHighestSeverity, getResourceColor } from '../lib/colors';
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

  const borderColor = selected
    ? '#60a5fa'
    : isShadow
    ? '#f59e0b'
    : highestSev
    ? severityColors[highestSev]
    : isNew
    ? driftColors.added
    : isChanged
    ? driftColors.changed
    : '#e2e8f0';

  // e.g. AWS_INSTANCE
  const typeLabel = data.type.replace(/^aws_/, '').toUpperCase().replaceAll('_', '_');

  return (
    <div
      style={{ width: 180 }}
      className="relative cursor-pointer"
      onClick={() => setSelectedNode(data)}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="!bg-slate-300 !border-slate-200 !w-2 !h-2"
      />

      <div
        style={{
          background: '#ffffff',
          border: `1.5px ${isShadow ? 'dashed' : 'solid'} ${borderColor}`,
          borderLeft: `3px solid ${getResourceColor(data.type)}`,
          borderRadius: 8,
          padding: '9px 11px 8px',
          opacity: isDeleted ? 0.45 : 1,
          boxShadow: selected
            ? `0 0 12px ${borderColor}50`
            : '0 1px 3px rgba(0,0,0,0.10)',
        }}
      >
        {/* Header: type label + icon */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: 5,
          }}
        >
          <span
            style={{
              fontSize: 9,
              fontFamily: 'ui-monospace, monospace',
              color: '#64748b',
              letterSpacing: '0.04em',
              fontWeight: 600,
            }}
          >
            {typeLabel}
          </span>
          <AwsIcon resourceType={data.type} size={22} />
        </div>

        {/* Resource name */}
        <div
          style={{
            fontSize: 13,
            fontWeight: 700,
            fontFamily: 'ui-monospace, monospace',
            color: '#0f172a',
            lineHeight: 1.2,
            marginBottom: 8,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
          title={data.id}
        >
          {data.name}
        </div>

        {/* Footer: cost + drift badge + finding badge */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
            {data.cost.monthly_usd > 0 && (
              <span style={{ fontSize: 10, color: '#64748b' }}>
                ${data.cost.monthly_usd.toFixed(0)}/mo
              </span>
            )}
            {isNew && (
              <span
                style={{
                  fontSize: 8,
                  padding: '1px 5px',
                  borderRadius: 3,
                  background: 'rgba(22,163,74,0.10)',
                  color: '#16a34a',
                  fontWeight: 700,
                  border: '0.5px solid rgba(22,163,74,0.25)',
                }}
              >
                +NEW
              </span>
            )}
            {isChanged && (
              <span
                style={{
                  fontSize: 8,
                  padding: '1px 5px',
                  borderRadius: 3,
                  background: 'rgba(217,119,6,0.10)',
                  color: '#d97706',
                  fontWeight: 700,
                  border: '0.5px solid rgba(217,119,6,0.25)',
                }}
              >
                ~CHG
              </span>
            )}
          </div>

          {/* Finding badge or clean check */}
          {findingCount > 0 && highestSev ? (
            <div
              style={{
                width: 22,
                height: 22,
                borderRadius: '50%',
                background: severityColors[highestSev],
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 10,
                fontWeight: 800,
                color: 'white',
                flexShrink: 0,
                boxShadow: `0 0 6px ${severityColors[highestSev]}60`,
              }}
            >
              {findingCount}
            </div>
          ) : (
            <div
              style={{
                width: 22,
                height: 22,
                borderRadius: 5,
                background: 'rgba(22,163,74,0.08)',
                border: '1px solid rgba(22,163,74,0.30)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 11,
                color: '#16a34a',
                flexShrink: 0,
              }}
            >
              ✓
            </div>
          )}
        </div>
      </div>

      <Handle
        type="source"
        position={Position.Bottom}
        className="!bg-slate-300 !border-slate-200 !w-2 !h-2"
      />

      {isShadow && (
        <div style={{ textAlign: 'center', marginTop: 2, fontSize: 9, color: '#d97706' }}>
          shadow
        </div>
      )}
    </div>
  );
}

export const ResourceNodeMemo = memo(ResourceNodeComponent);
