import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import type { ResourceNode as ResourceNodeData } from '../types';
import { severityColors, driftColors, getHighestSeverity } from '../lib/colors';
import { getServiceConfig } from '../icons/awsServiceConfig';
import { getAzureServiceConfig } from '../icons/azureServiceConfig';
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

  const svc = data.provider === 'azurerm'
    ? getAzureServiceConfig(data.type)
    : getServiceConfig(data.type);

  const typeLabel = data.type
    .replace(/^aws_/, '')
    .replace(/^azurerm_/, '')
    .toUpperCase()
    .replaceAll('_', ' ');

  const hasSeverityAccent = !selected && !isShadow && highestSev !== null;
  const baseBorderColor = selected
    ? '#60a5fa'
    : isShadow
    ? '#f59e0b'
    : isNew
    ? driftColors.added
    : isChanged
    ? driftColors.changed
    : '#252d3d';

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
          background: 'linear-gradient(135deg, #0f1419 0%, #1a202c 100%)',
          border: `1.5px ${isShadow ? 'dashed' : 'solid'} ${baseBorderColor}`,
          borderTop: hasSeverityAccent
            ? `2.5px solid ${severityColors[highestSev!]}`
            : `1.5px ${isShadow ? 'dashed' : 'solid'} ${baseBorderColor}`,
          borderRadius: 10,
          padding: '14px 16px',
          opacity: isDeleted ? 0.5 : 1,
          boxShadow: selected
            ? `0 0 0 2px ${baseBorderColor}66, 0 8px 32px rgba(0,0,0,0.6), inset 0 1px 2px rgba(255,255,255,0.05)`
            : '0 4px 16px rgba(0,0,0,0.4), inset 0 1px 2px rgba(255,255,255,0.03)',
          transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
          position: 'relative',
        }}
        onMouseEnter={e => {
          (e.currentTarget as HTMLDivElement).style.transform = 'translateY(-1px)';
          (e.currentTarget as HTMLDivElement).style.boxShadow = hasSeverityAccent
            ? `0 0 0 1px ${severityColors[highestSev!]}55, 0 12px 40px rgba(0,0,0,0.5), inset 0 1px 2px rgba(255,255,255,0.05)`
            : `0 0 0 1px ${baseBorderColor}55, 0 12px 40px rgba(0,0,0,0.5), inset 0 1px 2px rgba(255,255,255,0.05)`;
        }}
        onMouseLeave={e => {
          (e.currentTarget as HTMLDivElement).style.transform = 'translateY(0)';
          (e.currentTarget as HTMLDivElement).style.boxShadow = selected
            ? `0 0 0 2px ${baseBorderColor}66, 0 8px 32px rgba(0,0,0,0.6), inset 0 1px 2px rgba(255,255,255,0.05)`
            : '0 4px 16px rgba(0,0,0,0.4), inset 0 1px 2px rgba(255,255,255,0.03)';
        }}
      >
        {/* Header: icon tile + meta */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 11, marginBottom: 10 }}>
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: 8,
              background: svc.color,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: svc.label.length > 3 ? 9 : 11,
              fontWeight: 900,
              fontFamily: 'ui-monospace, monospace',
              color: '#ffffff',
              letterSpacing: '-0.5px',
              flexShrink: 0,
              boxShadow: `0 2px 8px ${svc.color}40, inset 0 1px 1px rgba(255,255,255,0.15)`,
            }}
          >
            {svc.label}
          </div>

          <div style={{ minWidth: 0, flex: 1 }}>
            <div
              style={{
                fontSize: 9.5,
                fontWeight: 700,
                fontFamily: 'ui-monospace, monospace',
                color: '#64748b',
                letterSpacing: '0.6px',
                textTransform: 'uppercase',
                marginBottom: 3,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {typeLabel}
            </div>
            <div
              style={{
                fontSize: 13.5,
                fontWeight: 700,
                color: '#f1f5f9',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                lineHeight: 1.3,
                letterSpacing: '-0.2px',
              }}
              title={data.id}
            >
              {data.name}
            </div>
          </div>
        </div>

        {/* Footer: cost + drift + finding badge */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            {data.cost.monthly_usd > 0 && (
              <span
                style={{
                  fontSize: 11,
                  fontFamily: 'ui-monospace, monospace',
                  color: '#94a3b8',
                  fontWeight: 600,
                }}
              >
                ${data.cost.monthly_usd.toFixed(0)}/mo
              </span>
            )}
            {isNew && (
              <span
                style={{
                  fontSize: 7.5,
                  padding: '2px 6px',
                  borderRadius: 4,
                  background: 'rgba(34,197,94,0.15)',
                  color: '#4ade80',
                  fontWeight: 800,
                  border: '1px solid rgba(34,197,94,0.4)',
                  letterSpacing: '0.3px',
                }}
              >
                +NEW
              </span>
            )}
            {isChanged && (
              <span
                style={{
                  fontSize: 7.5,
                  padding: '2px 6px',
                  borderRadius: 4,
                  background: 'rgba(250,204,21,0.15)',
                  color: '#facc15',
                  fontWeight: 800,
                  border: '1px solid rgba(250,204,21,0.4)',
                  letterSpacing: '0.3px',
                }}
              >
                ~CHG
              </span>
            )}
          </div>

          {findingCount > 0 && highestSev ? (
            <div
              style={{
                width: 24,
                height: 24,
                borderRadius: '50%',
                background: `${severityColors[highestSev]}25`,
                border: `1.5px solid ${severityColors[highestSev]}66`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 10,
                fontWeight: 900,
                color: severityColors[highestSev],
                flexShrink: 0,
                boxShadow: `0 0 8px ${severityColors[highestSev]}30`,
              }}
            >
              {findingCount}
            </div>
          ) : (
            <div
              style={{
                width: 20,
                height: 20,
                borderRadius: 6,
                background: 'rgba(34,197,94,0.08)',
                border: '1px solid rgba(34,197,94,0.22)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 10,
                fontWeight: 700,
                color: 'rgba(74,222,128,0.75)',
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
