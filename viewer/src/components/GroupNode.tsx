import { memo } from 'react';
import type { NodeProps } from '@xyflow/react';
import { ZONE_COLORS, type ZoneType } from '../lib/colors';

type GroupNodeProps = NodeProps & {
  data: {
    label: string;
    zoneType: ZoneType;
    chip?: string;
    cidr?: string;
  };
};

function GroupNodeComponent({ data }: GroupNodeProps) {
  const zone = ZONE_COLORS[data.zoneType] ?? ZONE_COLORS.regional;
  const isAz = data.zoneType === 'az';

  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        background: zone.background,
        border: `${zone.borderWidth} ${zone.borderStyle} ${zone.border}`,
        borderRadius: 12,
        position: 'relative',
      }}
    >
      {/* Zone label pill */}
      <div
        style={{
          position: 'absolute',
          top: -11,
          left: 16,
          display: 'flex',
          alignItems: 'center',
          gap: 5,
        }}
      >
        <span
          style={{
            fontSize: 11,
            fontWeight: 600,
            fontFamily: 'ui-monospace, monospace',
            color: zone.pillText,
            background: isAz ? 'transparent' : zone.pill,
            border: isAz ? 'none' : `1px solid ${zone.pillBorder}`,
            padding: isAz ? '0' : '2px 10px',
            borderRadius: 4,
            letterSpacing: '0.06em',
            textTransform: 'uppercase',
            display: 'flex',
            alignItems: 'center',
            gap: 5,
          }}
        >
          {data.zoneType === 'vpc' && <span style={{ fontSize: 10 }}>⬡</span>}
          {data.label}
        </span>

        {/* Chip (public/private/data tier) */}
        {data.chip && !isAz && (
          <span
            style={{
              fontSize: 9,
              fontWeight: 500,
              fontFamily: 'ui-monospace, monospace',
              color: zone.pillText,
              background: zone.pill,
              border: `1px solid ${zone.pillBorder}`,
              padding: '2px 6px',
              borderRadius: 3,
              letterSpacing: '0.04em',
              opacity: 0.8,
            }}
          >
            {data.chip}
          </span>
        )}
      </div>

      {/* CIDR block */}
      {data.cidr && (
        <span
          style={{
            position: 'absolute',
            bottom: 6,
            left: 12,
            fontSize: 10,
            fontFamily: 'ui-monospace, monospace',
            color: '#374151',
          }}
        >
          {data.cidr}
        </span>
      )}
    </div>
  );
}

export const GroupNodeMemo = memo(GroupNodeComponent);
