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
  const isCategory = data.zoneType === 'category';

  const pillPadding = isCategory ? '1px 8px' : '2px 10px';
  const pillFontSize = isCategory ? 9 : 11;
  const labelTop = isCategory ? 6 : 10;

  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        background: zone.background,
        border: `${zone.borderWidth} ${zone.borderStyle} ${zone.border}`,
        borderRadius: isCategory ? 8 : 12,
        position: 'relative',
      }}
    >
      {/* Zone label pill — anchored inside the container */}
      <div
        style={{
          position: 'absolute',
          top: labelTop,
          left: 14,
          display: 'flex',
          alignItems: 'center',
          gap: 5,
        }}
      >
        <span
          style={{
            fontSize: pillFontSize,
            fontWeight: 600,
            fontFamily: 'ui-monospace, monospace',
            color: zone.pillText,
            background: isAz ? 'transparent' : zone.pill,
            border: isAz ? 'none' : `1px solid ${zone.pillBorder}`,
            padding: isAz ? '0' : pillPadding,
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

        {data.chip && !isAz && !isCategory && (
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

      {data.cidr && !isCategory && (
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
