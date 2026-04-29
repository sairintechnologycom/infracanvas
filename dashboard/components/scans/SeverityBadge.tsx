interface Props {
  severity: 'critical' | 'high' | 'medium' | 'info'
  count: number
}

// Tailwind arbitrary-value classes reference the CSS custom props declared by
// @infracanvas/viewer/styles.css (imported in dashboard/app/globals.css per Plan 07-05 / D-04).
// Fallback hex values guard against any build-time resolution gap.
const SEV_CLASSES: Record<Props['severity'], string> = {
  critical: 'text-[color:var(--color-sev-critical,#ef4444)]',
  high:     'text-[color:var(--color-sev-high,#f97316)]',
  medium:   'text-[color:var(--color-sev-medium,#eab308)]',
  info:     'text-[color:var(--color-sev-info,#3b82f6)]',
}

export function SeverityBadge({ severity, count }: Props) {
  const cls = count > 0 ? SEV_CLASSES[severity] : 'text-slate-400'
  return (
    <span
      className={`text-sm tabular-nums font-semibold ${cls}`}
      data-testid={`severity-badge-${severity}`}
    >
      {count}
    </span>
  )
}
