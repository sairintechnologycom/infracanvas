import { useState } from 'react';
import { X, Network, FileText, Shield, Code, List } from 'lucide-react';
import { FindingCard } from '../FindingCard';
import { useStore } from '../../store';
import type { Finding, ResourceNode } from '../../types';

type Tab = 'overview' | 'findings' | 'attributes' | 'routes';

const ROUTES_ELIGIBLE_TYPES = new Set([
  'aws_ec2_transit_gateway_route_table',
  'aws_route_table',
  'azurerm_virtual_hub',
]);

export function PathDetailPanel() {
  const node = useStore((s) => s.selectedNode);
  const setSelectedNode = useStore((s) => s.setSelectedNode);
  const [activeTab, setActiveTab] = useState<Tab>('overview');

  // Empty state — nothing selected
  if (!node) {
    return (
      <div
        className="w-80 shrink-0 flex flex-col overflow-hidden z-10"
        style={{ background: '#161b27', borderLeft: '1px solid #252d3d' }}
      >
        <div
          style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 12,
            padding: 24,
            textAlign: 'center',
          }}
        >
          <Network size={24} color="#4a5568" />
          <div style={{ fontSize: 13, fontWeight: 600, color: '#e2e8f0' }}>Select a node</div>
          <p
            style={{
              fontSize: 11,
              fontWeight: 500,
              color: '#94a3b8',
              lineHeight: 1.45,
              margin: 0,
              maxWidth: 260,
            }}
          >
            Click any TGW, VPC, vWAN hub, vNet, or ExpressRoute circuit to see routes, peers, and
            attached findings.
          </p>
        </div>
      </div>
    );
  }

  const hasRoutes = ROUTES_ELIGIBLE_TYPES.has(node.type);
  const tabs: Array<{ id: Tab; label: string; icon: typeof FileText }> = [
    { id: 'overview', label: 'Overview', icon: FileText },
    { id: 'findings', label: `Findings (${node.findings.length})`, icon: Shield },
    { id: 'attributes', label: 'Attributes', icon: Code },
    ...(hasRoutes ? [{ id: 'routes' as const, label: 'Routes', icon: List }] : []),
  ];

  const color = '#3B82F6'; // reuse forward-blue accent

  return (
    <div
      className="w-80 shrink-0 flex flex-col overflow-hidden z-10"
      style={{ background: '#161b27', borderLeft: '1px solid #252d3d' }}
    >
      {/* Header */}
      <div className="p-4" style={{ borderBottom: '1px solid #252d3d' }}>
        <div className="flex items-start justify-between mb-2">
          <span
            className="text-[10px] font-medium px-1.5 py-0.5 rounded"
            style={{ background: `${color}20`, color }}
          >
            {node.type}
          </span>
          <button
            onClick={() => setSelectedNode(null)}
            className="cursor-pointer"
            style={{ color: '#94A3B8' }}
            aria-label="Close details"
          >
            <X size={16} />
          </button>
        </div>
        <div className="font-semibold text-sm" style={{ color: '#e2e8f0' }}>
          {node.name}
        </div>
        <div className="text-[11px] font-mono mt-0.5" style={{ color: '#4a5568' }}>
          {node.id}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex" style={{ borderBottom: '1px solid #252d3d' }}>
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className="flex items-center gap-1 px-3 py-2 text-[11px] font-medium cursor-pointer transition-colors flex-1 justify-center"
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
      <div style={{ flex: 1, overflowY: 'auto', padding: 16 }}>
        {activeTab === 'overview' && <OverviewTab node={node} />}
        {activeTab === 'findings' && <FindingsTab findings={node.findings} />}
        {activeTab === 'attributes' && <AttributesTab attributes={node.attributes} />}
        {activeTab === 'routes' && hasRoutes && (
          <RoutesTab routes={(node.attributes.routes as unknown[] | undefined) ?? []} />
        )}
      </div>
    </div>
  );
}

function OverviewTab({ node }: { node: ResourceNode }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: 11, color: '#94A3B8' }}>
      <Row label="Provider" value={node.provider} />
      <Row label="Region" value={node.region || '—'} />
      <Row label="Findings" value={String(node.findings.length)} />
      <Row label="Drift" value={node.drift} />
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
      <span style={{ color: '#4a5568' }}>{label}</span>
      <span style={{ color: '#e2e8f0', fontFamily: 'var(--font-mono)' }}>{value}</span>
    </div>
  );
}

function FindingsTab({ findings }: { findings: Finding[] }) {
  if (findings.length === 0) {
    return <p style={{ fontSize: 11, color: '#4a5568' }}>No findings on this node.</p>;
  }
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {findings.map((f, i) => (
        <FindingCard key={`${f.rule_id}-${i}`} finding={f} />
      ))}
    </div>
  );
}

function AttributesTab({ attributes }: { attributes: Record<string, unknown> }) {
  return (
    <pre
      style={{
        fontSize: 10,
        fontFamily: 'var(--font-mono)',
        color: '#94A3B8',
        background: '#0F172A',
        padding: 8,
        borderRadius: 4,
        whiteSpace: 'pre-wrap',
        overflowX: 'auto',
      }}
    >
      {JSON.stringify(attributes, null, 2)}
    </pre>
  );
}

interface RouteEntry {
  DestinationCidrBlock?: string;
  destination_cidr_block?: string;
  Type?: string;
  State?: string;
  state?: string;
  next_hop?: string;
}

function RoutesTab({ routes }: { routes: unknown[] }) {
  if (routes.length === 0) {
    return <p style={{ fontSize: 11, color: '#4a5568' }}>No routes collected for this node.</p>;
  }
  return (
    <table style={{ width: '100%', fontSize: 11, borderCollapse: 'collapse' }}>
      <thead>
        <tr style={{ color: '#4a5568', textAlign: 'left' }}>
          <th
            style={{
              padding: '4px 6px',
              fontWeight: 600,
              textTransform: 'uppercase',
              fontSize: 10,
            }}
          >
            Destination
          </th>
          <th
            style={{
              padding: '4px 6px',
              fontWeight: 600,
              textTransform: 'uppercase',
              fontSize: 10,
            }}
          >
            Source
          </th>
          <th
            style={{
              padding: '4px 6px',
              fontWeight: 600,
              textTransform: 'uppercase',
              fontSize: 10,
            }}
          >
            State
          </th>
        </tr>
      </thead>
      <tbody>
        {routes.map((r, i) => {
          const route = r as RouteEntry;
          const dest = route.DestinationCidrBlock ?? route.destination_cidr_block ?? '—';
          const type = route.Type ?? '—';
          const state = route.State ?? route.state ?? '—';
          return (
            <tr key={i} style={{ borderTop: '1px solid #252d3d' }}>
              <td
                style={{
                  padding: '4px 6px',
                  color: '#e2e8f0',
                  fontFamily: 'var(--font-mono)',
                }}
              >
                {dest}
              </td>
              <td style={{ padding: '4px 6px', color: '#94A3B8' }}>{type}</td>
              <td
                style={{
                  padding: '4px 6px',
                  color: state === 'active' || state === 'available' ? '#22C55E' : '#F59E0B',
                }}
              >
                {state}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

export default PathDetailPanel;
