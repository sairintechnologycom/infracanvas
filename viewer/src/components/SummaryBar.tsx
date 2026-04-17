import { Shield, Filter, Box } from 'lucide-react';
import { useStore } from '../store';
import { severityColors } from '../lib/colors';
import type { Severity } from '../types';
import { SearchBar } from './SearchBar';

const severityOrder: Severity[] = ['critical', 'high', 'medium', 'info'];

export function SummaryBar() {
  const graph = useStore(s => s.graph);
  const toggleFilterPanel = useStore(s => s.toggleFilterPanel);
  const filterPanelOpen = useStore(s => s.filterPanelOpen);
  const toggleSeverityFilter = useStore(s => s.toggleSeverityFilter);
  const activeSeverities = useStore(s => s.filters.severities);

  if (!graph) return null;

  const { summary, metadata } = graph;
  const scoreColor =
    summary.score >= 70 ? '#22c55e' :
    summary.score >= 60 ? '#eab308' :
    '#ef4444';
  const scoreBg =
    summary.score >= 70 ? 'rgba(34,197,94,0.1)' :
    summary.score >= 60 ? 'rgba(234,179,8,0.1)' :
    'rgba(239,68,68,0.1)';
  const scoreBorder =
    summary.score >= 70 ? 'rgba(34,197,94,0.3)' :
    summary.score >= 60 ? 'rgba(234,179,8,0.3)' :
    'rgba(239,68,68,0.3)';

  const scanDate = new Date(metadata.scanned_at).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit',
  });

  return (
    <div
      className="flex items-center gap-5 px-5 shrink-0 z-20"
      style={{
        background: 'linear-gradient(180deg, #0f1419 0%, #1a202c 100%)',
        borderBottom: '1.5px solid #252d3d',
        height: 48,
        boxShadow: '0 2px 8px rgba(0,0,0,0.2)',
      }}
    >
      {/* Project name */}
      <div className="flex items-center gap-2.5">
        <Box size={16} color="#60a5fa" />
        <span className="text-sm font-bold" style={{ color: '#f1f5f9' }}>
          {metadata.project}
        </span>
        <span className="text-xs" style={{ color: '#64748b', fontWeight: 500 }}>
          {scanDate}
        </span>
      </div>

      {/* Separator */}
      <div className="w-px h-5" style={{ background: '#252d3d' }} />

      {/* Score badge */}
      <div
        className="flex items-center gap-2 px-3 py-1.5 rounded-lg transition-all"
        style={{
          background: scoreBg,
          border: `1.5px solid ${scoreBorder}`,
          boxShadow: `0 2px 8px ${scoreBg}`,
        }}
      >
        <Shield size={14} color={scoreColor} />
        <span className="text-sm font-bold" style={{ color: scoreColor }}>
          {summary.score}
        </span>
        <span className="text-xs" style={{ color: scoreColor, opacity: 0.8, fontWeight: 600 }}>/100</span>
      </div>

      {/* Separator */}
      <div className="w-px h-5" style={{ background: '#252d3d' }} />

      {/* Finding chips — dot + count */}
      <div className="flex items-center gap-3.5">
        {severityOrder.map(sev => {
          const count = summary.findings[sev] ?? 0;
          const isActive = activeSeverities.includes(sev);
          return (
            <button
              key={sev}
              onClick={() => toggleSeverityFilter(sev)}
              className="flex items-center gap-1.5 text-xs font-semibold cursor-pointer transition-all hover:opacity-100"
              style={{
                color: severityColors[sev],
                opacity: isActive ? 1 : 0.45,
                background: 'none',
                border: 'none',
                padding: 0,
              }}
            >
              <span
                style={{
                  width: 7,
                  height: 7,
                  borderRadius: '50%',
                  background: severityColors[sev],
                  display: 'inline-block',
                  flexShrink: 0,
                  boxShadow: `0 0 6px ${severityColors[sev]}40`,
                }}
              />
              {count}
            </button>
          );
        })}
      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Drift counts */}
      {(summary.drift.added > 0 || summary.drift.changed > 0 || summary.drift.deleted > 0) && (
        <>
          <div className="w-px h-5" style={{ background: '#252d3d' }} />
          <div className="flex items-center gap-1.5 text-[10px] font-medium">
            {summary.drift.added > 0 && (
              <span style={{ color: '#22c55e' }}>+{summary.drift.added}</span>
            )}
            {summary.drift.changed > 0 && (
              <span style={{ color: '#eab308' }}>~{summary.drift.changed}</span>
            )}
            {summary.drift.deleted > 0 && (
              <span style={{ color: '#ef4444' }}>-{summary.drift.deleted}</span>
            )}
          </div>
        </>
      )}

      {/* Resource count */}
      <span className="text-[11px]" style={{ color: '#4a5568' }}>
        {summary.total_resources} resources
      </span>

      {/* Cost */}
      {summary.estimated_monthly_cost > 0 && (
        <span className="text-[11px] font-medium" style={{ color: '#22c55e' }}>
          ${summary.estimated_monthly_cost.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}/mo
        </span>
      )}

      {/* Edge legend — actual stroke samples */}
      <div className="flex items-center gap-3 text-[9px]" style={{ color: '#4a5568' }}>
        <span className="flex items-center gap-1.5">
          <svg width="22" height="6">
            <line x1="0" y1="3" x2="16" y2="3" stroke="rgba(71,85,105,0.6)" strokeWidth="1.5" />
            <polygon points="16,1 22,3 16,5" fill="rgba(71,85,105,0.6)" />
          </svg>
          traffic
        </span>
        <span className="flex items-center gap-1.5">
          <svg width="22" height="6">
            <line x1="0" y1="3" x2="16" y2="3" stroke="rgba(59,130,246,0.45)" strokeWidth="1.5" strokeDasharray="5 3" />
            <polygon points="16,1 22,3 16,5" fill="rgba(59,130,246,0.45)" />
          </svg>
          access
        </span>
        <span className="flex items-center gap-1.5">
          <svg width="22" height="6">
            <line x1="0" y1="3" x2="22" y2="3" stroke="rgba(221,52,76,0.4)" strokeWidth="1" strokeDasharray="3 2" />
          </svg>
          security
        </span>
      </div>

      {/* Search */}
      <SearchBar />

      {/* Filter toggle */}
      <button
        onClick={toggleFilterPanel}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold cursor-pointer transition-all hover:border-slate-500"
        style={{
          background: filterPanelOpen ? 'rgba(45,55,72,0.6)' : 'transparent',
          color: filterPanelOpen ? '#f1f5f9' : '#64748b',
          border: `1.5px solid ${filterPanelOpen ? '#404d5c' : '#2d3748'}`,
        }}
      >
        <Filter size={14} />
        Filters
      </button>
    </div>
  );
}
