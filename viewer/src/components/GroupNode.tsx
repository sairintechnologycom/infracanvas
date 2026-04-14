import { memo } from 'react';
import type { NodeProps } from '@xyflow/react';
import type { ResourceNode } from '../types';

type GroupNodeProps = NodeProps & {
  data: {
    label: string;
    color: string;
    dashed?: boolean;
    subnetNode?: ResourceNode;
  };
};

function GroupNodeComponent({ data }: GroupNodeProps) {
  const subnetNode = data.subnetNode;
  const isSubnet = !!subnetNode;

  // Issue 4: Determine public/private for subnet context
  const isPublic = isSubnet && (
    subnetNode.attributes?.map_public_ip_on_launch === true ||
    subnetNode.group?.includes('public') ||
    subnetNode.name?.includes('public')
  );

  const cidr = isSubnet
    ? (subnetNode.attributes?.cidr_block as string | undefined)
    : undefined;

  return (
    <div
      className="rounded-xl p-3 pt-7 h-full w-full"
      style={{
        background: `${data.color}08`,
        border: `1px ${data.dashed ? 'dashed' : 'dashed'} ${data.color}40`,
        minWidth: 300,
        minHeight: 150,
      }}
    >
      {/* Group label */}
      <div
        className="absolute top-2 left-3 text-[10px] font-semibold tracking-wider px-2 py-0.5 rounded"
        style={{
          color: data.color,
          background: `${data.color}15`,
        }}
      >
        {data.label}
      </div>

      {/* Issue 4: Subnet context chip */}
      {isSubnet && (
        <div className="absolute top-2 right-3 flex items-center gap-2">
          {/* Public/private indicator */}
          <span
            className="text-[9px] font-medium px-1.5 py-0.5 rounded"
            style={{
              color: isPublic ? '#06b6d4' : '#64748b',
              background: isPublic ? '#06b6d410' : '#64748b10',
            }}
          >
            {isPublic ? '\uD83C\uDF10 public IP on launch' : '\uD83D\uDD12 no public IP'}
          </span>

          {/* CIDR block */}
          {cidr && (
            <span
              className="text-[10px] font-mono px-1 py-0.5 rounded"
              style={{ color: '#94a3b8', background: '#1e293b' }}
            >
              {cidr}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

export const GroupNodeMemo = memo(GroupNodeComponent);
