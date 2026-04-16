import { memo } from 'react';
import type { NodeProps } from '@xyflow/react';
import { ZONE_COLORS, type ZoneType } from '../lib/colors';
import {
  ArchitectureGroupVirtualprivatecloudVPC,
  ArchitectureGroupRegion,
} from 'aws-react-icons';

const ZONE_BORDER_STYLE: Record<ZoneType, 'solid' | 'dashed'> = {
  internet: 'solid',
  vpc: 'solid',
  az: 'dashed',
  public_subnet: 'solid',
  private_subnet: 'dashed',
  data_subnet: 'dashed',
  regional: 'dashed',
};

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
  const borderStyle = ZONE_BORDER_STYLE[data.zoneType] ?? 'dashed';

  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        background: zone.background,
        border: `1px ${borderStyle} ${zone.border}`,
        borderRadius: 12,
        position: 'relative',
      }}
    >
      {/* Zone label */}
      <div
        style={{
          position: 'absolute',
          top: 8,
          left: 12,
          fontSize: 11,
          fontWeight: 600,
          fontFamily: 'ui-monospace, monospace',
          color: zone.label,
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          textTransform: 'uppercase' as const,
          letterSpacing: '0.06em',
          opacity: data.zoneType === 'az' ? 0.80 : undefined,
        }}
      >
        {data.zoneType === 'vpc' && <ArchitectureGroupVirtualprivatecloudVPC size={16} />}
        {data.zoneType === 'regional' && <ArchitectureGroupRegion size={16} />}
        {data.label}
      </div>

      {/* Tier chip (public/private/data) */}
      {data.chip && (
        <span
          style={{
            position: 'absolute',
            top: 8,
            right: 12,
            fontSize: 9,
            fontWeight: 500,
            color: zone.label,
            background: `${zone.label}15`,
            padding: '2px 6px',
            borderRadius: 3,
          }}
        >
          {data.chip}
        </span>
      )}

      {/* CIDR block */}
      {data.cidr && (
        <span
          style={{
            position: 'absolute',
            bottom: 6,
            left: 12,
            fontSize: 10,
            fontFamily: 'ui-monospace, monospace',
            color: '#64748b',
          }}
        >
          {data.cidr}
        </span>
      )}
    </div>
  );
}

export const GroupNodeMemo = memo(GroupNodeComponent);
