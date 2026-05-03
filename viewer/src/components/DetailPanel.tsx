import { useState } from 'react';
import { X, FileText, Shield, Code, GitCompare, Lock } from 'lucide-react';
import type { ResourceNode as ResourceNodeType, AttributeChange } from '../types';
import { useViewerStoreOrSingleton } from '../store';
import { FindingCard } from './FindingCard';
import { ResourceIcon } from './icons/ResourceIcon';
import { getResourceColor, driftColors, severityColors } from '../lib/colors';

type Tab = 'overview' | 'findings' | 'attributes' | 'changes';

export function DetailPanel() {
  const selectedNode = useViewerStoreOrSingleton(s => s.selectedNode);
  const setSelectedNode = useViewerStoreOrSingleton(s => s.setSelectedNode);
  const [activeTab, setActiveTab] = useState<Tab>('overview');

  if (!selectedNode) return null;

  const node = selectedNode;
  const typeLabel = node.type.replace(/^aws_/, '').replaceAll('_', ' ');
  const color = getResourceColor(node.type);

  const driftChanges = node.drift_changes ?? [];
  const tabs: { id: Tab; label: string; icon: typeof FileText }[] = [
    { id: 'overview', label: 'Overview', icon: FileText },
    { id: 'findings', label: `Findings (${node.findings.length})`, icon: Shield },
    { id: 'attributes', label: 'Attributes', icon: Code },
    ...(driftChanges.length > 0
      ? [{ id: 'changes' as const, label: `Changes (${driftChanges.length})`, icon: GitCompare }]
      : []),
  ];

  return (
    <div
      className="w-80 shrink-0 flex flex-col overflow-hidden z-10"
      style={{
        background: '#161b27',
        borderLeft: '1px solid #252d3d',
      }}
    >
      {/* Header */}
      <div className="p-4" style={{ borderBottom: '1px solid #252d3d' }}>
        <div className="flex items-start justify-between mb-2">
          <div className="flex items-center gap-2">
            <ResourceIcon resourceType={node.type} size={28} />
            <div>
              <span
                className="text-xs font-medium px-1.5 py-0.5 rounded"
                style={{ background: `${color}20`, color }}
              >
                {typeLabel}
              </span>
            </div>
          </div>
          <button
            onClick={() => setSelectedNode(null)}
            className="cursor-pointer"
            style={{ color: '#4a5568' }}
          >
            <X size={16} />
          </button>
        </div>
        <div className="font-semibold text-sm" style={{ color: '#e2e8f0' }}>{node.name}</div>
        <div className="text-xs font-mono mt-0.5" style={{ color: '#4a5568' }}>{node.id}</div>
      </div>

      {/* Tabs */}
      <div className="flex" style={{ borderBottom: '1px solid #252d3d' }}>
        {tabs.map(tab => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className="flex items-center gap-1 px-3 py-2 text-xs font-medium cursor-pointer transition-colors flex-1 justify-center"
              style={{
                color: isActive ? '#e2e8f0' : '#4a5568',
                borderBottom: isActive ? `2px solid ${color}` : '2px solid transparent',
                background: isActive ? `${color}10` : 'transparent',
              }}
            >
              <Icon size={12} />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {activeTab === 'overview' && <OverviewTab node={node} />}
        {activeTab === 'findings' && <FindingsTab node={node} />}
        {activeTab === 'attributes' && <AttributesTab node={node} />}
        {activeTab === 'changes' && <ChangesTab changes={driftChanges} />}
      </div>
    </div>
  );
}

function OverviewTab({ node }: { node: ResourceNodeType }) {
  const driftColor = driftColors[node.drift];
  const rows = [
    { label: 'Provider', value: node.provider },
    { label: 'Region', value: node.region || 'N/A' },
    { label: 'Module', value: node.module || 'root' },
    { label: 'Group', value: node.group || 'ungrouped' },
  ];

  return (
    <div className="flex flex-col gap-3">
      {/* Info rows */}
      <div className="flex flex-col gap-1.5">
        {rows.map(row => (
          <div key={row.label} className="flex items-center justify-between">
            <span className="text-xs uppercase tracking-wider" style={{ color: '#4a5568' }}>{row.label}</span>
            <span className="text-xs font-mono" style={{ color: '#94a3b8' }}>{row.value}</span>
          </div>
        ))}
      </div>

      {/* Drift status */}
      <div className="flex items-center justify-between">
        <span className="text-xs uppercase tracking-wider" style={{ color: '#4a5568' }}>Drift</span>
        <span
          className="text-xs font-medium px-2 py-0.5 rounded capitalize"
          style={{ background: `${driftColor}20`, color: driftColor }}
        >
          {node.drift}
        </span>
      </div>

      {/* Cost */}
      <div className="flex items-center justify-between">
        <span className="text-xs uppercase tracking-wider" style={{ color: '#4a5568' }}>Cost</span>
        <div className="text-right">
          <div className="text-sm font-semibold" style={{ color: '#e2e8f0' }}>
            ${node.cost.monthly_usd.toFixed(2)}/mo
          </div>
          {node.cost.basis && (
            <div className="text-xs" style={{ color: '#4a5568' }}>{node.cost.basis}</div>
          )}
        </div>
      </div>

      {/* Dependencies */}
      {node.dependencies.length > 0 && (
        <div>
          <div className="text-xs uppercase tracking-wider mb-1.5" style={{ color: '#4a5568' }}>
            Dependencies ({node.dependencies.length})
          </div>
          <div className="flex flex-col gap-1">
            {node.dependencies.map(dep => (
              <div
                key={dep}
                className="text-xs font-mono px-2 py-1 rounded"
                style={{ background: '#1c2333', color: '#94a3b8', border: '1px solid #252d3d' }}
              >
                {dep}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Findings summary */}
      {node.findings.length > 0 && (
        <div>
          <div className="text-xs uppercase tracking-wider mb-1.5" style={{ color: '#4a5568' }}>
            Findings Summary
          </div>
          <div className="flex gap-2">
            {(['critical', 'high', 'medium', 'info'] as const).map(sev => {
              const count = node.findings.filter(f => f.severity === sev).length;
              if (count === 0) return null;
              return (
                <span
                  key={sev}
                  className="text-xs font-medium px-1.5 py-0.5 rounded"
                  style={{ background: `${severityColors[sev]}20`, color: severityColors[sev] }}
                >
                  {count} {sev}
                </span>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

function FindingsTab({ node }: { node: Pick<ResourceNodeType, 'findings'> }) {
  const gateMode = useViewerStoreOrSingleton(s => s.gateMode);

  if (node.findings.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-8">
        <Shield size={24} color="#22c55e" />
        <div className="text-xs mt-2" style={{ color: '#22c55e' }}>No findings</div>
        <div className="text-xs mt-1" style={{ color: '#4a5568' }}>This resource passed all checks</div>
      </div>
    );
  }

  if (gateMode) {
    return (
      <div className="flex flex-col items-center gap-2 py-4 px-3">
        <Lock size={16} style={{ color: '#4a5568' }} />
        <div className="text-xs font-semibold" style={{ color: '#e2e8f0' }}>
          {node.findings.length} finding{node.findings.length !== 1 ? 's' : ''}
        </div>
        <div className="flex flex-wrap gap-1">
          {(['critical', 'high', 'medium', 'info'] as const).map(sev => {
            const count = node.findings.filter(f => f.severity === sev).length;
            if (count === 0) return null;
            return (
              <span key={sev} className="text-xs font-medium px-1.5 py-0.5 rounded"
                style={{ background: `${severityColors[sev]}20`, color: severityColors[sev] }}>
                {count} {sev}
              </span>
            );
          })}
        </div>
        <div className="w-full flex flex-col gap-1 mt-2">
          {[1, 2, 3].map(i => (
            <div key={i} className="rounded px-3 py-2"
              style={{ background: '#1c2333', border: '1px solid #252d3d', filter: 'blur(4px)', pointerEvents: 'none', height: 24 }} />
          ))}
        </div>
        <div className="text-xs mt-1" style={{ color: '#4a5568' }}>
          Upgrade to see what's wrong and how to fix it
        </div>
        <a href="https://infracanvas.dev/founding" target="_blank" rel="noopener noreferrer"
          className="text-xs font-semibold px-4 py-2 rounded-md mt-1 inline-block"
          style={{ background: '#3b82f620', border: '1px solid #3b82f6', color: '#60a5fa' }}>
          Unlock details — founding member $49/mo
        </a>
        <div className="text-xs" style={{ color: '#4a5568' }}>
          Locked forever for founding members
        </div>
      </div>
    );
  }

  return (
    <div>
      {node.findings.map((finding, i) => (
        <FindingCard key={`${finding.rule_id}-${i}`} finding={finding} />
      ))}
    </div>
  );
}

function AttributesTab({ node }: { node: { attributes: Record<string, unknown> } }) {
  return (
    <pre
      className="text-xs p-3 rounded overflow-auto"
      style={{
        background: '#0a0e17',
        color: '#94a3b8',
        fontFamily: 'var(--font-mono)',
        maxHeight: '100%',
      }}
    >
      {JSON.stringify(node.attributes, null, 2)}
    </pre>
  );
}

function ChangesTab({ changes }: { changes: AttributeChange[] }) {
  if (changes.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-8">
        <GitCompare size={24} color="#22c55e" />
        <div className="text-xs mt-2" style={{ color: '#22c55e' }}>No changes</div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      {changes.map((change) => (
        <div
          key={change.attribute}
          className="p-2 rounded text-xs"
          style={{ background: '#1c2333', border: '1px solid #252d3d' }}
        >
          <div className="font-semibold mb-1" style={{ color: '#e2e8f0', fontFamily: 'var(--font-mono)' }}>
            {change.attribute}
          </div>
          <div className="flex flex-col gap-0.5">
            {change.before != null && (
              <div style={{ color: '#ef4444' }}>
                <span style={{ textDecoration: 'line-through' }}>
                  {change.sensitive ? (
                    <span style={{ color: '#4a5568', fontStyle: 'italic' }}>[sensitive]</span>
                  ) : (
                    String(change.before)
                  )}
                </span>
              </div>
            )}
            {change.after != null && (
              <div style={{ color: '#22c55e' }}>
                {change.sensitive ? (
                  <span style={{ color: '#4a5568', fontStyle: 'italic' }}>[sensitive]</span>
                ) : (
                  String(change.after)
                )}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
