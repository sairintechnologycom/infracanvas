import { AlertTriangle, Info, ShieldAlert, ShieldX } from 'lucide-react';
import type { Finding, Severity } from '../types';
import { severityColors } from '../lib/colors';

const severityIcons: Record<Severity, typeof AlertTriangle> = {
  critical: ShieldX,
  high: ShieldAlert,
  medium: AlertTriangle,
  info: Info,
};

interface FindingCardProps {
  finding: Finding;
  gateMode?: boolean;
}

export function FindingCard({ finding, gateMode = false }: FindingCardProps) {
  const color = severityColors[finding.severity];
  const Icon = severityIcons[finding.severity];

  return (
    <div
      className="rounded-lg p-3 mb-2"
      style={{
        background: `${color}08`,
        border: `1px solid ${color}30`,
      }}
    >
      {/* Header — always visible */}
      <div className="flex items-center gap-2 mb-1.5">
        <Icon size={14} color={color} />
        <span
          className="text-xs font-bold uppercase px-1.5 py-0.5 rounded"
          style={{ background: `${color}20`, color }}
        >
          {finding.severity}
        </span>
        {finding.source === 'policy' && (
          <span
            className="text-xs font-bold uppercase px-1.5 py-0.5 rounded"
            style={{
              background: 'rgba(167,139,250,0.15)',
              color: '#a78bfa',
              border: '0.5px solid rgba(167,139,250,0.3)',
            }}
          >
            POLICY
          </span>
        )}
        <span className="text-xs font-mono" style={{ color: '#94a3b8' }}>
          {finding.rule_id}
        </span>
      </div>

      {gateMode ? (
        /* Blurred placeholders — no finding text in DOM */
        <div className="flex flex-col gap-1" style={{ filter: 'blur(4px)', pointerEvents: 'none' }}>
          <div className="rounded" style={{ background: '#1e293b', height: 14, width: '80%' }} />
          <div className="rounded" style={{ background: '#1e293b', height: 12, width: '60%' }} />
          <div className="rounded" style={{ background: '#1e293b', height: 12, width: '70%' }} />
        </div>
      ) : (
        <>
          {/* Title + description */}
          <div className="text-xs font-medium mb-1" style={{ color: '#e2e8f0' }}>
            {finding.title}
          </div>
          <div className="text-xs mb-2" style={{ color: '#94a3b8' }}>
            {finding.description}
          </div>

          {/* Evidence */}
          {Object.keys(finding.evidence).length > 0 && (
            <pre
              className="text-xs p-2 rounded overflow-x-auto mb-2"
              style={{
                background: '#0a0e17',
                color: '#94a3b8',
                fontFamily: 'var(--font-mono)',
              }}
            >
              {JSON.stringify(finding.evidence, null, 2)}
            </pre>
          )}

          {/* Remediation */}
          {finding.remediation && (
            <div className="text-xs flex gap-1.5" style={{ color: '#22c55e' }}>
              <span className="shrink-0">Fix:</span>
              <span>{finding.remediation}</span>
            </div>
          )}

          {/* Compliance framework tags */}
          {finding.framework_ids && finding.framework_ids.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-1.5">
              {finding.framework_ids.map(id => (
                <span
                  key={id}
                  className="text-xs px-1 py-0.5 rounded"
                  style={{
                    background: '#1c2333',
                    color: '#4a5568',
                    border: '1px solid #252d3d',
                  }}
                >
                  {id}
                </span>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
