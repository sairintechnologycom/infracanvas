import { memo } from 'react';
import type { NodeProps } from '@xyflow/react';
import { ZONE_COLORS, type ZoneType } from '../lib/colors';
import type { Provider } from '../lib/providerTheme';

type GroupNodeProps = NodeProps & {
  data: {
    label: string;
    zoneType: ZoneType;
    chip?: string;
    cidr?: string;
    provider?: Provider;
  };
};

// Provider-branded palette for the top-level cloud container.
// Mirrors the official AWS / Azure reference-architecture styling.
const CLOUD_PROVIDER_PALETTE: Record<Provider, { border: string; text: string }> = {
  aws:     { border: 'rgba(255,153,0,0.85)',  text: '#D97706' },
  azurerm: { border: 'rgba(0,120,212,0.85)',  text: '#0078D4' },
  generic: { border: 'rgba(100,116,139,0.7)', text: '#475569' },
};

function GroupNodeComponent({ data }: GroupNodeProps) {
  const baseZone = ZONE_COLORS[data.zoneType] ?? ZONE_COLORS.regional;
  const isCloud = data.zoneType === 'cloud';
  const cloudPalette = isCloud ? CLOUD_PROVIDER_PALETTE[data.provider ?? 'generic'] : null;

  const borderColor = cloudPalette ? cloudPalette.border : baseZone.border;
  const labelColor = cloudPalette ? cloudPalette.text : baseZone.pillText;

  const isCategory = data.zoneType === 'category';
  const isAz = data.zoneType === 'az';

  // Label tab (AWS/Azure ref-arch style): small rounded pill that straddles the top-left
  // of the container, white fill with a thin colored border, colored uppercase text.
  const tabFontSize = isCategory ? 9 : isCloud ? 11 : 10;
  const tabPadding = isCategory ? '2px 8px' : '3px 10px';

  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        background: 'transparent',
        border: `${baseZone.borderWidth} ${baseZone.borderStyle} ${borderColor}`,
        borderRadius: isCategory ? 6 : isCloud ? 14 : 10,
        position: 'relative',
        boxSizing: 'border-box',
      }}
    >
      {/* Label tab — anchored straddling the top-left border like AWS ref diagrams */}
      <div
        style={{
          position: 'absolute',
          top: -10,
          left: 14,
          display: 'flex',
          alignItems: 'center',
          gap: 5,
        }}
      >
        <span
          style={{
            fontSize: tabFontSize,
            fontWeight: 600,
            fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
            color: labelColor,
            background: '#FFFFFF',
            border: `1px solid ${borderColor}`,
            padding: tabPadding,
            borderRadius: 4,
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
            display: 'flex',
            alignItems: 'center',
            gap: 5,
            lineHeight: 1,
            whiteSpace: 'nowrap',
          }}
        >
          {data.label}
        </span>

        {data.chip && !isAz && !isCategory && (
          <span
            style={{
              fontSize: 9,
              fontWeight: 500,
              fontFamily: 'ui-monospace, monospace',
              color: labelColor,
              background: '#FFFFFF',
              border: `1px solid ${borderColor}`,
              padding: '2px 6px',
              borderRadius: 3,
              letterSpacing: '0.04em',
              lineHeight: 1,
              opacity: 0.9,
            }}
          >
            {data.chip}
          </span>
        )}
      </div>

      {data.cidr && !isCategory && (
        <span
          style={{
            position: 'absolute',
            bottom: 6,
            right: 12,
            fontSize: 10,
            fontFamily: 'ui-monospace, monospace',
            color: '#64748B',
          }}
        >
          {data.cidr}
        </span>
      )}
    </div>
  );
}

export const GroupNodeMemo = memo(GroupNodeComponent);
