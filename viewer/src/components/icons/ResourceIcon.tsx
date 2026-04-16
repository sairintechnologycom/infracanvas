import { getResourceColor } from '../../lib/colors';

interface ResourceIconProps {
  resourceType: string;
  size?: number;
}

export function ResourceIcon({ resourceType, size = 28 }: ResourceIconProps) {
  const color = getResourceColor(resourceType);
  const s = size;
  const half = s / 2;

  // Pick shape based on resource family
  const family = resourceType.replace(/_[^_]+$/, '');
  let shape: React.ReactNode;

  switch (family) {
    case 'aws_vpc':
    case 'aws_subnet':
      // Cloud shape (rounded rect)
      shape = (
        <rect x={s * 0.15} y={s * 0.2} width={s * 0.7} height={s * 0.6}
          rx={s * 0.15} fill={color} opacity={0.9} />
      );
      break;
    case 'aws_security_group':
      // Shield
      shape = (
        <path d={`M${half} ${s * 0.1} L${s * 0.85} ${s * 0.3} L${s * 0.85} ${s * 0.6} Q${s * 0.85} ${s * 0.9} ${half} ${s * 0.95} Q${s * 0.15} ${s * 0.9} ${s * 0.15} ${s * 0.6} L${s * 0.15} ${s * 0.3} Z`}
          fill={color} opacity={0.9} />
      );
      break;
    case 'aws_instance':
    case 'aws_ec2':
      // Server (stacked rects)
      shape = (
        <>
          <rect x={s * 0.15} y={s * 0.15} width={s * 0.7} height={s * 0.3} rx={3} fill={color} opacity={0.9} />
          <rect x={s * 0.15} y={s * 0.55} width={s * 0.7} height={s * 0.3} rx={3} fill={color} opacity={0.7} />
        </>
      );
      break;
    case 'aws_s3':
      // Bucket
      shape = (
        <path d={`M${s * 0.2} ${s * 0.2} L${s * 0.8} ${s * 0.2} L${s * 0.75} ${s * 0.85} Q${half} ${s * 0.95} ${s * 0.25} ${s * 0.85} Z`}
          fill={color} opacity={0.9} />
      );
      break;
    case 'aws_rds':
    case 'aws_db':
      // Database cylinder
      shape = (
        <>
          <ellipse cx={half} cy={s * 0.28} rx={s * 0.32} ry={s * 0.13} fill={color} opacity={0.9} />
          <rect x={s * 0.18} y={s * 0.28} width={s * 0.64} height={s * 0.45} fill={color} opacity={0.8} />
          <ellipse cx={half} cy={s * 0.73} rx={s * 0.32} ry={s * 0.13} fill={color} opacity={0.9} />
        </>
      );
      break;
    case 'aws_lambda':
      // Lambda symbol (triangle)
      shape = (
        <path d={`M${half} ${s * 0.12} L${s * 0.88} ${s * 0.88} L${s * 0.12} ${s * 0.88} Z`}
          fill={color} opacity={0.9} />
      );
      break;
    case 'aws_alb':
    case 'aws_lb':
      // Load balancer (horizontal lines)
      shape = (
        <>
          <rect x={s * 0.15} y={s * 0.2} width={s * 0.7} height={s * 0.12} rx={2} fill={color} opacity={0.9} />
          <rect x={s * 0.15} y={s * 0.44} width={s * 0.7} height={s * 0.12} rx={2} fill={color} opacity={0.8} />
          <rect x={s * 0.15} y={s * 0.68} width={s * 0.7} height={s * 0.12} rx={2} fill={color} opacity={0.7} />
        </>
      );
      break;
    case 'aws_iam':
      // Person/key
      shape = (
        <>
          <circle cx={half} cy={s * 0.3} r={s * 0.16} fill={color} opacity={0.9} />
          <path d={`M${s * 0.2} ${s * 0.85} Q${s * 0.2} ${s * 0.5} ${half} ${s * 0.5} Q${s * 0.8} ${s * 0.5} ${s * 0.8} ${s * 0.85}`}
            fill={color} opacity={0.7} />
        </>
      );
      break;
    case 'aws_kms':
      // Key (circle + rect) — handles aws_kms_key
      shape = (
        <>
          <circle cx={s * 0.35} cy={s * 0.4} r={s * 0.2} fill={color} opacity={0.9} />
          <rect x={s * 0.45} y={s * 0.33} width={s * 0.4} height={s * 0.14} rx={2} fill={color} opacity={0.8} />
          <rect x={s * 0.7} y={s * 0.47} width={s * 0.12} height={s * 0.16} rx={1} fill={color} opacity={0.7} />
        </>
      );
      break;
    case 'aws_eks':
      // EKS cluster (hexagon with inner circle — Kubernetes wheel)
      shape = (
        <>
          <polygon
            points={`${half},${s * 0.1} ${s * 0.87},${s * 0.32} ${s * 0.87},${s * 0.68} ${half},${s * 0.9} ${s * 0.13},${s * 0.68} ${s * 0.13},${s * 0.32}`}
            fill={color} opacity={0.3} stroke={color} strokeWidth={1.5} />
          <circle cx={half} cy={half} r={s * 0.18} fill={color} opacity={0.9} />
        </>
      );
      break;
    case 'aws_nat':
      // NAT gateway (arrow up-down through a rect)
      shape = (
        <>
          <rect x={s * 0.2} y={s * 0.35} width={s * 0.6} height={s * 0.3} rx={4} fill={color} opacity={0.7} />
          <polygon points={`${half},${s * 0.1} ${s * 0.62},${s * 0.35} ${s * 0.38},${s * 0.35}`} fill={color} opacity={0.9} />
          <polygon points={`${half},${s * 0.9} ${s * 0.62},${s * 0.65} ${s * 0.38},${s * 0.65}`} fill={color} opacity={0.9} />
        </>
      );
      break;
    case 'aws_cloudwatch_log':
    case 'aws_cloudwatch':
      // CloudWatch log group (doc with lines)
      shape = (
        <>
          <rect x={s * 0.2} y={s * 0.1} width={s * 0.6} height={s * 0.8} rx={3} fill={color} opacity={0.2} stroke={color} strokeWidth={1.5} />
          <line x1={s * 0.32} y1={s * 0.35} x2={s * 0.68} y2={s * 0.35} stroke={color} strokeWidth={1.5} />
          <line x1={s * 0.32} y1={s * 0.5} x2={s * 0.68} y2={s * 0.5} stroke={color} strokeWidth={1.5} />
          <line x1={s * 0.32} y1={s * 0.65} x2={s * 0.55} y2={s * 0.65} stroke={color} strokeWidth={1.5} />
        </>
      );
      break;
    case 'aws_elasticache':
      // ElastiCache (stacked ellipses — in-memory db)
      shape = (
        <>
          <ellipse cx={half} cy={s * 0.3} rx={s * 0.32} ry={s * 0.12} fill={color} opacity={0.9} />
          <ellipse cx={half} cy={s * 0.55} rx={s * 0.32} ry={s * 0.12} fill={color} opacity={0.7} />
          <ellipse cx={half} cy={s * 0.78} rx={s * 0.32} ry={s * 0.12} fill={color} opacity={0.5} />
        </>
      );
      break;
    case 'aws_cloudfront':
      // Globe (circle with lines)
      shape = (
        <>
          <circle cx={half} cy={half} r={s * 0.35} fill="none" stroke={color} strokeWidth={2} opacity={0.9} />
          <ellipse cx={half} cy={half} rx={s * 0.18} ry={s * 0.35} fill="none" stroke={color} strokeWidth={1.5} opacity={0.7} />
          <line x1={s * 0.15} y1={half} x2={s * 0.85} y2={half} stroke={color} strokeWidth={1.5} opacity={0.7} />
        </>
      );
      break;
    case 'aws_dynamodb':
      // Table grid
      shape = (
        <>
          <rect x={s * 0.15} y={s * 0.15} width={s * 0.7} height={s * 0.7} rx={4} fill={color} opacity={0.2} stroke={color} strokeWidth={1.5} />
          <line x1={s * 0.15} y1={s * 0.42} x2={s * 0.85} y2={s * 0.42} stroke={color} strokeWidth={1.5} />
          <line x1={s * 0.42} y1={s * 0.15} x2={s * 0.42} y2={s * 0.85} stroke={color} strokeWidth={1.5} />
        </>
      );
      break;
    default:
      // Generic hex
      shape = (
        <polygon
          points={`${half},${s * 0.1} ${s * 0.87},${s * 0.32} ${s * 0.87},${s * 0.68} ${half},${s * 0.9} ${s * 0.13},${s * 0.68} ${s * 0.13},${s * 0.32}`}
          fill={color} opacity={0.9} />
      );
  }

  return (
    <svg width={s} height={s} viewBox={`0 0 ${s} ${s}`}>
      {shape}
    </svg>
  );
}
