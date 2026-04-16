import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import type { ResourceNode as ResourceNodeData } from '../types';
import { severityColors, driftColors, getHighestSeverity } from '../lib/colors';
import { getServiceConfig } from '../icons/awsServiceConfig';
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

  const svc = getServiceConfig(data.type);

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
    : '#252d3d';

  const typeLabel = data.type
    .replace(/^aws_/, '')
    .toUpperCase()
    .replaceAll('_', ' ');

  return (
    <div
      style={{ width: 168 }}
      className="relative cursor-pointer"
      onClick={() => setSelectedNode(data)}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="!bg-slate-600 !border-slate-700 !w-2 !h-2"
      />

      <div
        style={{
          background: '#1c2333',
          border: `1px ${isShadow ? 'dashed' : 'solid'} ${borderColor}`,
          borderRadius: 8,
          padding: '12px 14px',
          opacity: isDeleted ? 0.4 : 1,
          boxShadow: selected
            ? `0 0 0 1px ${borderColor}, 0 4px 24px rgba(0,0,0,0.5)`
            : '0 2px 8px rgba(0,0,0,0.3)',
          transition: 'border-color 0.15s, box-shadow 0.15s, transform 0.15s',
        }}
        onMouseEnter={e => {
          (e.currentTarget as HTMLDivElement).style.borderColor = 'rgba(255,255,255,0.2)';
          (e.currentTarget as HTMLDivElement).style.transform = 'translateY(-1px)';
          (e.currentTarget as HTMLDivElement).style.boxShadow = '0 4px 24px rgba(0,0,0,0.4)';
        }}
        onMouseLeave={e => {
          (e.currentTarget as HTMLDivElement).style.borderColor = borderColor;
          (e.currentTarget as HTMLDivElement).style.transform = 'translateY(0)';
          (e.currentTarget as HTMLDivElement).style.boxShadow = selected
            ? `0 0 0 1px ${borderColor}, 0 4px 24px rgba(0,0,0,0.5)`
            : '0 2px 8px rgba(0,0,0,0.3)';
        }}
      >
        {/* Header: icon box + meta */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
          {/* Icon box */}
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: 6,
              background: `${svc.color}1F`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            }}
          >
            <div
              style={{
                width: 20,
                height: 20,
                borderRadius: 4,
                background: svc.color,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: svc.label.length > 3 ? 6 : 8,
                fontWeight: 800,
                fontFamily: 'ui-monospace, monospace',
                color: '#ffffff',
                letterSpacing: '-0.5px',
              }}
            >
              {svc.label}
            </div>
          </div>

          {/* Meta */}
          <div style={{ minWidth: 0, flex: 1 }}>
            <div
              style={{
                fontSize: 10,
                fontWeight: 600,
                fontFamily: 'ui-monospace, monospace',
                color: '#4a5568',
                letterSpacing: '0.5px',
                textTransform: 'uppercase',
                marginBottom: 2,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {typeLabel}
            </div>
            <div
              style={{
                fontSize: 13,
                fontWeight: 600,
                color: '#e2e8f0',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                lineHeight: 1.2,
              }}
              title={data.id}
            >
              {data.name}
            </div>
          </div>
        </div>

        {/* Footer: cost + drift + finding badge */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
            {data.cost.monthly_usd > 0 && (
              <span
                style={{
                  fontSize: 11,
                  fontFamily: 'ui-monospace, monospace',
                  color: '#4a5568',
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
                  color: '#22c55e',
                  fontWeight: 700,
                  border: '0.5px solid rgba(34,197,94,0.3)',
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
                  background: 'rgba(234,179,8,0.12)',
                  color: '#eab308',
                  fontWeight: 700,
                  border: '0.5px solid rgba(234,179,8,0.3)',
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
                background: `${severityColors[highestSev]}22`,
                border: `1px solid ${severityColors[highestSev]}55`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 10,
                fontWeight: 800,
                color: severityColors[highestSev],
                flexShrink: 0,
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
                background: 'rgba(34,197,94,0.08)',
                border: '1px solid rgba(34,197,94,0.25)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 11,
                color: '#22c55e',
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
        className="!bg-slate-600 !border-slate-700 !w-2 !h-2"
      />

      {isShadow && (
        <div style={{ textAlign: 'center', marginTop: 2, fontSize: 9, color: '#f59e0b' }}>
          shadow
        </div>
      )}
    </div>
  );
}

export const ResourceNodeMemo = memo(ResourceNodeComponent);
