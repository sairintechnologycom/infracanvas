import { X } from 'lucide-react';
import { useViewerStoreOrSingleton } from '../../store';
import type { Severity, ResourceNode } from '../../types';

const SEVERITIES: Severity[] = ['critical', 'high', 'medium', 'info'];

const NETWORK_TYPE_OPTIONS: Array<{ value: string; label: string }> = [
  { value: 'aws_ec2_transit_gateway', label: 'TGW' },
  { value: 'aws_route_table', label: 'VPC Route Table' },
  { value: 'aws_network_acl', label: 'NACL' },
  { value: 'aws_dx_connection', label: 'Direct Connect' },
  { value: 'aws_dx_virtual_interface', label: 'DX Virtual Interface' },
  { value: 'aws_vpn_connection', label: 'VPN' },
  { value: 'azurerm_virtual_hub', label: 'vWAN Hub' },
  { value: 'azurerm_virtual_network', label: 'vNet' },
  { value: 'azurerm_virtual_network_peering', label: 'vNet Peering' },
  { value: 'azurerm_network_security_group', label: 'NSG' },
  { value: 'azurerm_express_route_circuit', label: 'ExpressRoute' },
];

const NETWORK_TYPE_SET = new Set(NETWORK_TYPE_OPTIONS.map((o) => o.value));

export function FlowMapFilterPanel() {
  const filterPanelOpen = useViewerStoreOrSingleton((s) => s.filterPanelOpen);
  const toggleFilterPanel = useViewerStoreOrSingleton((s) => s.toggleFilterPanel);
  const graph = useViewerStoreOrSingleton((s) => s.graph);
  const filters = useViewerStoreOrSingleton((s) => s.flowMapFilters);
  const toggleSev = useViewerStoreOrSingleton((s) => s.toggleFlowMapSeverity);
  const setCloud = useViewerStoreOrSingleton((s) => s.setFlowMapCloud);
  const toggleNT = useViewerStoreOrSingleton((s) => s.toggleFlowMapNodeType);
  const toggleFL = useViewerStoreOrSingleton((s) => s.toggleFlowMapFlowLogs);
  const clear = useViewerStoreOrSingleton((s) => s.clearFlowMapFilters);

  if (!filterPanelOpen || !graph) return null;

  const networkNodes: ResourceNode[] = graph.nodes.filter((n) => NETWORK_TYPE_SET.has(n.type));

  const hasActive =
    filters.severities.length > 0 ||
    filters.cloud !== 'both' ||
    filters.nodeTypes.length > 0 ||
    filters.hasFlowLogs;

  return (
    <div
      className="w-56 shrink-0 overflow-y-auto z-10"
      style={{ background: '#161b27', borderRight: '1px solid #252d3d' }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between p-3"
        style={{ borderBottom: '1px solid #252d3d' }}
      >
        <span className="text-xs font-semibold" style={{ color: '#e2e8f0' }}>
          Filters
        </span>
        <div className="flex items-center gap-2">
          {hasActive && (
            <button
              onClick={clear}
              className="text-[10px] uppercase tracking-wider font-semibold cursor-pointer"
              style={{ color: '#94A3B8' }}
            >
              Clear
            </button>
          )}
          <button
            onClick={toggleFilterPanel}
            className="cursor-pointer"
            style={{ color: '#94A3B8' }}
            aria-label="Close filters"
          >
            <X size={14} />
          </button>
        </div>
      </div>

      {/* Severity */}
      <div className="p-3" style={{ borderBottom: '1px solid #252d3d' }}>
        <div
          className="text-[10px] uppercase tracking-wider mb-2 font-semibold"
          style={{ color: '#4a5568' }}
        >
          Severity
        </div>
        <div className="flex flex-col gap-1">
          {SEVERITIES.map((sev) => {
            const isActive = filters.severities.includes(sev);
            const count = networkNodes.reduce(
              (acc, n) => acc + n.findings.filter((f) => f.severity === sev).length,
              0,
            );
            return (
              <label
                key={sev}
                className="flex items-center gap-2 cursor-pointer text-[11px] py-0.5"
                style={{ color: isActive ? '#e2e8f0' : '#94A3B8' }}
              >
                <input
                  type="checkbox"
                  checked={isActive}
                  onChange={() => toggleSev(sev)}
                  className="w-3 h-3"
                />
                <span className="flex-1 capitalize">{sev}</span>
                <span className="text-[10px]" style={{ color: '#374151' }}>
                  {count}
                </span>
              </label>
            );
          })}
        </div>
      </div>

      {/* Cloud */}
      <div className="p-3" style={{ borderBottom: '1px solid #252d3d' }}>
        <div
          className="text-[10px] uppercase tracking-wider mb-2 font-semibold"
          style={{ color: '#4a5568' }}
        >
          Cloud
        </div>
        <div className="flex gap-2">
          {(['aws', 'azure', 'both'] as const).map((c) => {
            const isActive = filters.cloud === c;
            const cloudRing = c === 'aws' ? '#FF9900' : c === 'azure' ? '#0078D4' : '#94A3B8';
            const label = c === 'both' ? 'Both' : c.toUpperCase();
            return (
              <button
                key={c}
                onClick={() => setCloud(c)}
                className="px-2 py-0.5 text-[11px] font-medium cursor-pointer"
                style={{
                  height: 22,
                  borderRadius: 11,
                  border: `1px solid ${isActive ? cloudRing : '#252d3d'}`,
                  background: isActive ? `${cloudRing}20` : 'transparent',
                  color: isActive ? '#e2e8f0' : '#94A3B8',
                  textTransform: 'uppercase',
                }}
              >
                {label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Node Type */}
      <div className="p-3" style={{ borderBottom: '1px solid #252d3d' }}>
        <div
          className="text-[10px] uppercase tracking-wider mb-2 font-semibold"
          style={{ color: '#4a5568' }}
        >
          Node Type
        </div>
        <div className="flex flex-col gap-1 max-h-48 overflow-y-auto">
          {NETWORK_TYPE_OPTIONS.map((opt) => {
            const count = networkNodes.filter((n) => n.type === opt.value).length;
            if (count === 0) return null;
            const isActive = filters.nodeTypes.includes(opt.value);
            return (
              <label
                key={opt.value}
                className="flex items-center gap-2 cursor-pointer text-[11px] py-0.5"
                style={{ color: isActive ? '#e2e8f0' : '#94A3B8' }}
              >
                <input
                  type="checkbox"
                  checked={isActive}
                  onChange={() => toggleNT(opt.value)}
                  className="w-3 h-3"
                />
                <span className="flex-1 font-mono text-[10px]">{opt.label}</span>
                <span className="text-[10px]" style={{ color: '#374151' }}>
                  {count}
                </span>
              </label>
            );
          })}
        </div>
      </div>

      {/* Has Flow Logs */}
      <div className="p-3">
        <div
          className="text-[10px] uppercase tracking-wider mb-2 font-semibold"
          style={{ color: '#4a5568' }}
        >
          Flow Logs
        </div>
        <label
          className="flex items-center justify-between cursor-pointer text-[11px] py-0.5"
          style={{ color: '#94A3B8' }}
        >
          <span>Has Flow Logs</span>
          <span
            role="switch"
            aria-checked={filters.hasFlowLogs}
            onClick={toggleFL}
            onKeyDown={(e) => {
              if (e.key === ' ' || e.key === 'Enter') {
                e.preventDefault();
                toggleFL();
              }
            }}
            tabIndex={0}
            style={{
              width: 28,
              height: 14,
              borderRadius: 7,
              background: filters.hasFlowLogs ? '#22C55E' : '#475569',
              position: 'relative',
              cursor: 'pointer',
              transition: 'background 0.2s',
              display: 'inline-block',
            }}
          >
            <span
              style={{
                position: 'absolute',
                top: 2,
                left: filters.hasFlowLogs ? 16 : 2,
                width: 10,
                height: 10,
                borderRadius: 5,
                background: '#FFFFFF',
                transition: 'left 0.2s',
              }}
            />
          </span>
        </label>
      </div>
    </div>
  );
}

export default FlowMapFilterPanel;
