import { Shield, Filter, Box } from 'lucide-react';
import { useViewerStoreOrSingleton } from '../store';
import { severityColors } from '../lib/colors';
import type { Severity } from '../types';
import { SearchBar } from './SearchBar';

const severityOrder: Severity[] = ['critical', 'high', 'medium', 'info'];

export function SummaryBar() {
  const graph = useViewerStoreOrSingleton(s => s.graph);
  const toggleFilterPanel = useViewerStoreOrSingleton(s => s.toggleFilterPanel);
  const filterPanelOpen = useViewerStoreOrSingleton(s => s.filterPanelOpen);
  const toggleSeverityFilter = useViewerStoreOrSingleton(s => s.toggleSeverityFilter);
  const activeSeverities = useViewerStoreOrSingleton(s => s.filters.severities);

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
      className="flex items-center gap-4 px-5 shrink-0 z-20"
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
        <span className="text-sm font-bold" style={{ color: scoreColor, letterSpacing: '-0.02em' }}>
          {summary.score}
        </span>
        <span className="text-xs font-semibold" style={{ color: scoreColor, opacity: 0.6 }}>
          /100
        </span>
      </div>

      <div className="w-px h-5" style={{ background: '#252d3d' }} />

      {/* Severity chips — tightened cluster */}
      <div className="flex items-center gap-2.5">
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

      <div className="flex-1" />

      {/* Metadata cluster — single group */}
      <div className="flex items-center gap-3">
        <span className="text-xs" style={{ color: '#4a5568' }}>
          {summary.total_resources} resources
        </span>
        {summary.estimated_monthly_cost > 0 && (
          <span className="text-xs font-medium" style={{ color: '#22c55e' }}>
            ${summary.estimated_monthly_cost.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}/mo
          </span>
        )}
        {(summary.drift.added > 0 || summary.drift.changed > 0 || summary.drift.deleted > 0) && (
          <div className="flex items-center gap-1.5 text-xs font-medium">
            {summary.drift.added > 0 && <span style={{ color: '#22c55e' }}>+{summary.drift.added}</span>}
            {summary.drift.changed > 0 && <span style={{ color: '#eab308' }}>~{summary.drift.changed}</span>}
            {summary.drift.deleted > 0 && <span style={{ color: '#ef4444' }}>-{summary.drift.deleted}</span>}
          </div>
        )}
      </div>

      {/* Edge legend — hover or focus-within reveals */}
      <div className="relative group focus-within:z-30">
        <button
          type="button"
          className="peer flex items-center justify-center rounded-full text-xs font-bold cursor-help transition-colors hover:border-slate-500 focus-visible:border-slate-500 focus-visible:outline-none"
          style={{
            width: 20,
            height: 20,
            background: 'transparent',
            border: '1.5px solid #2d3748',
            color: '#64748b',
          }}
          aria-label="Edge legend"
          aria-describedby="edge-legend-tooltip"
        >
          ?
        </button>
        <div
          id="edge-legend-tooltip"
          role="tooltip"
          className="absolute right-0 top-full mt-2 hidden group-hover:flex peer-focus-visible:flex flex-col gap-1.5 px-3 py-2 rounded-lg z-30 text-xs"
          style={{
            background: '#0f1419',
            border: '1.5px solid #252d3d',
            boxShadow: '0 8px 24px rgba(0,0,0,0.6)',
            color: '#94a3b8',
            minWidth: 140,
          }}
        >
          <span className="flex items-center gap-2">
            <svg width="22" height="6">
              <line x1="0" y1="3" x2="16" y2="3" stroke="#475569" strokeWidth="1.5" />
              <polygon points="16,1 22,3 16,5" fill="#475569" />
            </svg>
            traffic
          </span>
          <span className="flex items-center gap-2">
            <svg width="22" height="6">
              <line x1="0" y1="3" x2="16" y2="3" stroke="#3B82F6" strokeWidth="1.25" strokeDasharray="5 3" />
              <polygon points="16,1 22,3 16,5" fill="#3B82F6" />
            </svg>
            access
          </span>
          <span className="flex items-center gap-2">
            <svg width="22" height="6">
              <line x1="0" y1="3" x2="22" y2="3" stroke="#DC2626" strokeWidth="1" strokeDasharray="3 2" />
            </svg>
            security
          </span>
        </div>
      </div>

      <SearchBar />

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
