import { X } from 'lucide-react';
import { useStore } from '../store';
import { severityColors } from '../lib/colors';
import type { DriftStatus, Severity } from '../types';

const severities: Severity[] = ['critical', 'high', 'medium', 'info'];
const driftStatuses: DriftStatus[] = ['unchanged', 'added', 'changed', 'deleted'];

export function FilterPanel() {
  const graph = useStore(s => s.graph);
  const filterPanelOpen = useStore(s => s.filterPanelOpen);
  const toggleFilterPanel = useStore(s => s.toggleFilterPanel);
  const filters = useStore(s => s.filters);
  const toggleSeverityFilter = useStore(s => s.toggleSeverityFilter);
  const toggleResourceTypeFilter = useStore(s => s.toggleResourceTypeFilter);
  const toggleDriftFilter = useStore(s => s.toggleDriftFilter);
  const clearFilters = useStore(s => s.clearFilters);

  if (!filterPanelOpen || !graph) return null;

  // Get unique resource types
  const resourceTypes = [...new Set(graph.nodes.map(n => n.type))].sort();

  const hasActiveFilters =
    filters.severities.length > 0 ||
    filters.resourceTypes.length > 0 ||
    filters.driftStatuses.length > 0;

  return (
    <div
      className="w-56 shrink-0 overflow-y-auto z-10"
      style={{
        background: '#111827',
        borderRight: '1px solid #1e293b',
      }}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-3" style={{ borderBottom: '1px solid #1e293b' }}>
        <span className="text-xs font-semibold" style={{ color: '#e2e8f0' }}>Filters</span>
        <div className="flex items-center gap-2">
          {hasActiveFilters && (
            <button
              onClick={clearFilters}
              className="text-[10px] px-1.5 py-0.5 rounded cursor-pointer"
              style={{ background: '#1e293b', color: '#94a3b8' }}
            >
              Clear
            </button>
          )}
          <button onClick={toggleFilterPanel} className="cursor-pointer" style={{ color: '#64748b' }}>
            <X size={14} />
          </button>
        </div>
      </div>

      {/* Severity */}
      <div className="p-3" style={{ borderBottom: '1px solid #1e293b' }}>
        <div className="text-[10px] uppercase tracking-wider mb-2 font-semibold" style={{ color: '#64748b' }}>
          Severity
        </div>
        <div className="flex flex-col gap-1">
          {severities.map(sev => {
            const isActive = filters.severities.includes(sev);
            const count = graph.nodes.reduce((acc, n) =>
              acc + n.findings.filter(f => f.severity === sev).length, 0
            );
            return (
              <label
                key={sev}
                className="flex items-center gap-2 cursor-pointer text-[11px] py-0.5"
                style={{ color: isActive ? severityColors[sev] : '#94a3b8' }}
              >
                <input
                  type="checkbox"
                  checked={isActive}
                  onChange={() => toggleSeverityFilter(sev)}
                  className="accent-current"
                  style={{ accentColor: severityColors[sev] }}
                />
                <span className="flex-1 capitalize">{sev}</span>
                <span className="text-[10px]" style={{ color: '#64748b' }}>{count}</span>
              </label>
            );
          })}
        </div>
      </div>

      {/* Resource type */}
      <div className="p-3" style={{ borderBottom: '1px solid #1e293b' }}>
        <div className="text-[10px] uppercase tracking-wider mb-2 font-semibold" style={{ color: '#64748b' }}>
          Resource Type
        </div>
        <div className="flex flex-col gap-1 max-h-48 overflow-y-auto">
          {resourceTypes.map(rt => {
            const isActive = filters.resourceTypes.includes(rt);
            const count = graph.nodes.filter(n => n.type === rt).length;
            const label = rt.replace(/^aws_/, '');
            return (
              <label
                key={rt}
                className="flex items-center gap-2 cursor-pointer text-[11px] py-0.5"
                style={{ color: isActive ? '#e2e8f0' : '#94a3b8' }}
              >
                <input
                  type="checkbox"
                  checked={isActive}
                  onChange={() => toggleResourceTypeFilter(rt)}
                  className="accent-sky-500"
                />
                <span className="flex-1 truncate font-mono text-[10px]">{label}</span>
                <span className="text-[10px]" style={{ color: '#64748b' }}>{count}</span>
              </label>
            );
          })}
        </div>
      </div>

      {/* Drift status */}
      <div className="p-3">
        <div className="text-[10px] uppercase tracking-wider mb-2 font-semibold" style={{ color: '#64748b' }}>
          Drift Status
        </div>
        <div className="flex flex-col gap-1">
          {driftStatuses.map(ds => {
            const isActive = filters.driftStatuses.includes(ds);
            const count = graph.nodes.filter(n => n.drift === ds).length;
            return (
              <label
                key={ds}
                className="flex items-center gap-2 cursor-pointer text-[11px] py-0.5"
                style={{ color: isActive ? '#e2e8f0' : '#94a3b8' }}
              >
                <input
                  type="checkbox"
                  checked={isActive}
                  onChange={() => toggleDriftFilter(ds)}
                  className="accent-sky-500"
                />
                <span className="flex-1 capitalize">{ds}</span>
                <span className="text-[10px]" style={{ color: '#64748b' }}>{count}</span>
              </label>
            );
          })}
        </div>
      </div>
    </div>
  );
}
