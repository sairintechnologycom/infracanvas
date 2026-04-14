import { Shield, Filter, Box } from 'lucide-react';
import { useStore } from '../store';
import { severityColors } from '../lib/colors';
import type { Severity } from '../types';

const severityOrder: Severity[] = ['critical', 'high', 'medium', 'info'];

export function SummaryBar() {
  const graph = useStore(s => s.graph);
  const toggleFilterPanel = useStore(s => s.toggleFilterPanel);
  const filterPanelOpen = useStore(s => s.filterPanelOpen);
  const toggleSeverityFilter = useStore(s => s.toggleSeverityFilter);
  const activeSeverities = useStore(s => s.filters.severities);

  if (!graph) return null;

  const { summary, metadata } = graph;
  const scoreColor = summary.score >= 80 ? '#22c55e' : summary.score >= 60 ? '#f59e0b' : '#ef4444';
  const scanDate = new Date(metadata.scanned_at).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit',
  });

  return (
    <div
      className="flex items-center gap-4 px-4 py-2 shrink-0 z-20"
      style={{ background: '#111827', borderBottom: '1px solid #1e293b' }}
    >
      {/* Project name */}
      <div className="flex items-center gap-2">
        <Box size={16} color="#3b82f6" />
        <span className="text-sm font-semibold" style={{ color: '#e2e8f0' }}>
          {metadata.project}
        </span>
        <span className="text-[10px]" style={{ color: '#64748b' }}>
          {scanDate}
        </span>
      </div>

      {/* Separator */}
      <div className="w-px h-5" style={{ background: '#1e293b' }} />

      {/* Score badge */}
      <div className="flex items-center gap-1.5">
        <Shield size={14} color={scoreColor} />
        <span className="text-sm font-bold" style={{ color: scoreColor }}>
          {summary.score}
        </span>
        <span className="text-[10px]" style={{ color: '#64748b' }}>/100</span>
      </div>

      {/* Separator */}
      <div className="w-px h-5" style={{ background: '#1e293b' }} />

      {/* Finding pills */}
      <div className="flex items-center gap-1.5">
        {severityOrder.map(sev => {
          const count = summary.findings[sev] ?? 0;
          const isActive = activeSeverities.includes(sev);
          return (
            <button
              key={sev}
              onClick={() => toggleSeverityFilter(sev)}
              className="flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium cursor-pointer transition-all"
              style={{
                background: isActive ? `${severityColors[sev]}30` : `${severityColors[sev]}10`,
                color: severityColors[sev],
                border: `1px solid ${isActive ? severityColors[sev] : 'transparent'}`,
              }}
            >
              {sev.charAt(0).toUpperCase() + sev.slice(1)} {count}
            </button>
          );
        })}
      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Resource count */}
      <span className="text-[11px]" style={{ color: '#64748b' }}>
        {summary.total_resources} resources
      </span>

      {/* Cost */}
      {summary.estimated_monthly_cost > 0 && (
        <span className="text-[11px] font-medium" style={{ color: '#22c55e' }}>
          ${summary.estimated_monthly_cost.toFixed(2)}/mo
        </span>
      )}

      {/* Filter toggle */}
      <button
        onClick={toggleFilterPanel}
        className="flex items-center gap-1 px-2 py-1 rounded text-[11px] cursor-pointer transition-all"
        style={{
          background: filterPanelOpen ? '#1e293b' : 'transparent',
          color: '#94a3b8',
          border: '1px solid #1e293b',
        }}
      >
        <Filter size={12} />
        Filters
      </button>
    </div>
  );
}
