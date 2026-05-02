import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import type { ResourceNode as ResourceNodeData } from '../types';
import { severityColors, driftColors, getHighestSeverity } from '../lib/colors';
import { detectProvider } from '../lib/providerTheme';
import { ServiceIcon } from './icons/ServiceIcon';
import { useViewerStoreOrSingleton } from '../store';

type ResourceNodeProps = NodeProps & {
  data: ResourceNodeData;
};

// Must match layout.ts NODE_W / NODE_H so the layout math is truthful.
const NODE_W = 120;
const NODE_H = 90;
const ICON_SIZE = 40;

function ResourceNodeComponent({ data, selected }: ResourceNodeProps) {
  const setSelectedNode = useViewerStoreOrSingleton(s => s.setSelectedNode);
  const highestSev = getHighestSeverity(data.findings);
  const findingCount = data.findings.length;
  const isShadow = data.drift === 'shadow';
  const isNew = data.drift === 'added';
  const isChanged = data.drift === 'changed';
  const isDeleted = data.drift === 'deleted';

  // 5.1 D-01 / D-02: unresolved parser states — reuse shadow-orange visual vocabulary.
  const isUnresolvedModule =
    typeof data.type === 'string' && data.type.startsWith('_infracanvas_unresolved');
  const hasUnresolvedCount = Boolean(
    (data.attributes as Record<string, unknown> | undefined)?.['_unresolved_count'],
  );

  const provider = data.provider === 'azurerm' ? 'azurerm' : detectProvider(data.type);

  const typeLabel = data.type
    .replace(/^aws_/, '')
    .replace(/^azurerm_/, '')
    .replaceAll('_', ' ')
    .replace(/\b\w/g, c => c.toUpperCase());

  const driftTint = isShadow || isUnresolvedModule
    ? '#D97706'
    : isNew
    ? driftColors.added
    : isChanged
    ? driftColors.changed
    : null;

  return (
    <div
      style={{
        width: NODE_W,
        height: NODE_H,
        opacity: isDeleted ? 0.45 : 1,
        cursor: 'pointer',
        position: 'relative',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'flex-start',
        gap: 2,
      }}
      onClick={() => setSelectedNode(data)}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="!bg-slate-400 !border-slate-500 !w-2 !h-2"
      />

      {/* Icon — the visual anchor. Selected/drift states use a subtle ring, no card. */}
      <div
        style={{
          width: ICON_SIZE + 8,
          height: ICON_SIZE + 8,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          borderRadius: 8,
          boxShadow: selected
            ? '0 0 0 2px #3B82F6, 0 0 0 5px rgba(59,130,246,0.18)'
            : driftTint
            ? `0 0 0 2px ${driftTint}`
            : 'none',
          background: 'transparent',
          transition: 'box-shadow 0.12s ease',
        }}
      >
        <ServiceIcon provider={provider} type={data.type} size={ICON_SIZE} />
      </div>

      {/* Caption — bold name, muted type below, centered. Matches AWS ref-arch style. */}
      <div
        style={{
          fontSize: 11,
          fontWeight: 700,
          color: '#0F172A',
          lineHeight: 1.15,
          textAlign: 'center',
          width: '100%',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
          marginTop: 2,
        }}
        title={data.id}
      >
        {data.name}
      </div>
      <div
        style={{
          fontSize: 9,
          fontWeight: 500,
          color: '#64748B',
          lineHeight: 1.1,
          textAlign: 'center',
          width: '100%',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
        }}
      >
        {typeLabel}
      </div>

      {/* Severity badge — floating top-right of the icon */}
      {findingCount > 0 && highestSev && (
        <div
          style={{
            position: 'absolute',
            top: -4,
            right: 22,
            minWidth: 18,
            height: 18,
            padding: '0 5px',
            borderRadius: 9,
            background: severityColors[highestSev],
            color: '#ffffff',
            fontSize: 10,
            fontWeight: 800,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: `0 1px 3px ${severityColors[highestSev]}66, 0 0 0 2px #FFFFFF`,
          }}
        >
          {findingCount}
        </div>
      )}

      {/* 5.1 D-01: unresolved-module warning marker */}
      {isUnresolvedModule && (
        <div
          style={{
            position: 'absolute',
            top: -4,
            left: 22,
            minWidth: 18,
            height: 18,
            padding: '0 5px',
            borderRadius: 9,
            background: '#D97706',
            color: '#ffffff',
            fontSize: 10,
            fontWeight: 800,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 1px 3px rgba(217,119,6,0.4), 0 0 0 2px #FFFFFF',
          }}
          title="Unresolved module — check stderr for parse errors"
          data-testid="resource-node-unresolved-marker"
        >
          ⚠
        </div>
      )}

      {/* 5.1 D-02: ×? badge for non-literal count/for_each */}
      {hasUnresolvedCount && (
        <div
          style={{
            position: 'absolute',
            bottom: 18,
            right: -4,
            minWidth: 18,
            height: 18,
            padding: '0 5px',
            borderRadius: 9,
            background: '#64748B',
            color: '#ffffff',
            fontSize: 10,
            fontWeight: 700,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 1px 3px rgba(100,116,139,0.4), 0 0 0 2px #FFFFFF',
          }}
          title="Non-literal count/for_each — expanded instance count unknown"
          data-testid="resource-node-unresolved-count-badge"
        >
          ×?
        </div>
      )}

      <Handle
        type="source"
        position={Position.Bottom}
        className="!bg-slate-400 !border-slate-500 !w-2 !h-2"
      />
    </div>
  );
}

export const ResourceNodeMemo = memo(ResourceNodeComponent);
