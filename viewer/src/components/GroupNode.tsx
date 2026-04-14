import { memo } from 'react';
import type { NodeProps } from '@xyflow/react';

type GroupNodeProps = NodeProps & {
  data: { label: string; color: string };
};

function GroupNodeComponent({ data }: GroupNodeProps) {
  return (
    <div
      className="rounded-xl p-3 pt-7 h-full w-full"
      style={{
        background: `${data.color}08`,
        border: `1px dashed ${data.color}40`,
        minWidth: 300,
        minHeight: 150,
      }}
    >
      <div
        className="absolute top-2 left-3 text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded"
        style={{
          color: data.color,
          background: `${data.color}15`,
        }}
      >
        {data.label}
      </div>
    </div>
  );
}

export const GroupNodeMemo = memo(GroupNodeComponent);
