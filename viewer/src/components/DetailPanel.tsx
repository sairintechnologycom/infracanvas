import { useState } from 'react';
import { X, FileText, Shield, Code } from 'lucide-react';
import type { ResourceNode as ResourceNodeType } from '../types';
import { useStore } from '../store';
import { FindingCard } from './FindingCard';
import { ResourceIcon } from './icons/ResourceIcon';
import { getResourceColor, driftColors, severityColors } from '../lib/colors';

type Tab = 'overview' | 'findings' | 'attributes';

export function DetailPanel() {
  const selectedNode = useStore(s => s.selectedNode);
  const setSelectedNode = useStore(s => s.setSelectedNode);
  const [activeTab, setActiveTab] = useState<Tab>('overview');

  if (!selectedNode) return null;

  const node = selectedNode;
  const typeLabel = node.type.replace(/^aws_/, '').replaceAll('_', ' ');
  const color = getResourceColor(node.type);

  const tabs: { id: Tab; label: string; icon: typeof FileText }[] = [
    { id: 'overview', label: 'Overview', icon: FileText },
    { id: 'findings', label: `Findings (${node.findings.length})`, icon: Shield },
    { id: 'attributes', label: 'Attributes', icon: Code },
  ];

  return (
    <div
      className="w-80 shrink-0 flex flex-col overflow-hidden z-10"
      style={{
        background: '#111827',
        borderLeft: '1px solid #1e293b',
      }}
    >
      {/* Header */}
      <div className="p-4" style={{ borderBottom: '1px solid #1e293b' }}>
        <div className="flex items-start justify-between mb-2">
          <div className="flex items-center gap-2">
            <ResourceIcon resourceType={node.type} size={28} />
            <div>
              <span
                className="text-[10px] font-medium px-1.5 py-0.5 rounded"
                style={{ background: `${color}20`, color }}
              >
                {typeLabel}
              </span>
            </div>
          </div>
          <button
            onClick={() => setSelectedNode(null)}
            className="cursor-pointer"
            style={{ color: '#64748b' }}
          >
            <X size={16} />
          </button>
        </div>
        <div className="font-semibold text-sm" style={{ color: '#e2e8f0' }}>{node.name}</div>
        <div className="text-[11px] font-mono mt-0.5" style={{ color: '#64748b' }}>{node.id}</div>
      </div>

      {/* Tabs */}
      <div className="flex" style={{ borderBottom: '1px solid #1e293b' }}>
        {tabs.map(tab => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className="flex items-center gap-1 px-3 py-2 text-[11px] font-medium cursor-pointer transition-colors flex-1 justify-center"
              style={{
                color: isActive ? '#e2e8f0' : '#64748b',
                borderBottom: isActive ? `2px solid ${color}` : '2px solid transparent',
                background: isActive ? `${color}08` : 'transparent',
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
            <span className="text-[10px] uppercase tracking-wider" style={{ color: '#64748b' }}>{row.label}</span>
            <span className="text-[11px] font-mono" style={{ color: '#94a3b8' }}>{row.value}</span>
          </div>
        ))}
      </div>

      {/* Drift status */}
      <div className="flex items-center justify-between">
        <span className="text-[10px] uppercase tracking-wider" style={{ color: '#64748b' }}>Drift</span>
        <span
          className="text-[10px] font-medium px-2 py-0.5 rounded capitalize"
          style={{ background: `${driftColor}20`, color: driftColor }}
        >
          {node.drift}
        </span>
      </div>

      {/* Cost */}
      <div className="flex items-center justify-between">
        <span className="text-[10px] uppercase tracking-wider" style={{ color: '#64748b' }}>Cost</span>
        <div className="text-right">
          <div className="text-sm font-semibold" style={{ color: '#e2e8f0' }}>
            ${node.cost.monthly_usd.toFixed(2)}/mo
          </div>
          {node.cost.basis && (
            <div className="text-[10px]" style={{ color: '#64748b' }}>{node.cost.basis}</div>
          )}
        </div>
      </div>

      {/* Dependencies */}
      {node.dependencies.length > 0 && (
        <div>
          <div className="text-[10px] uppercase tracking-wider mb-1.5" style={{ color: '#64748b' }}>
            Dependencies ({node.dependencies.length})
          </div>
          <div className="flex flex-col gap-1">
            {node.dependencies.map(dep => (
              <div
                key={dep}
                className="text-[10px] font-mono px-2 py-1 rounded"
                style={{ background: '#0a0e17', color: '#94a3b8' }}
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
          <div className="text-[10px] uppercase tracking-wider mb-1.5" style={{ color: '#64748b' }}>
            Findings Summary
          </div>
          <div className="flex gap-2">
            {(['critical', 'high', 'medium', 'info'] as const).map(sev => {
              const count = node.findings.filter(f => f.severity === sev).length;
              if (count === 0) return null;
              return (
                <span
                  key={sev}
                  className="text-[10px] font-medium px-1.5 py-0.5 rounded"
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
  if (node.findings.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-8">
        <Shield size={24} color="#22c55e" />
        <div className="text-xs mt-2" style={{ color: '#22c55e' }}>No findings</div>
        <div className="text-[10px] mt-1" style={{ color: '#64748b' }}>This resource passed all checks</div>
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
      className="text-[10px] p-3 rounded overflow-auto"
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
