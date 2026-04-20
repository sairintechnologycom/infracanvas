import { useRef } from 'react';
import { useStore } from '../store';

type TabId = 'canvas' | 'flowmap';

interface TabDef {
  id: TabId;
  label: string;
  beta?: boolean;
  tooltip: string;
}

// WRG-03 / UI-SPEC §Copywriting: shortcut hint uses Mac glyph or Ctrl prefix
// depending on platform. navigator may be undefined in SSR/test — guard it.
const _isMac =
  typeof navigator !== 'undefined' &&
  navigator.platform.toLowerCase().includes('mac');
const _shortcut = _isMac ? '⌘\\' : 'Ctrl+\\';

const TABS: TabDef[] = [
  {
    id: 'canvas',
    label: 'Canvas',
    tooltip: `Infrastructure diagram — press 1 or ${_shortcut}`,
  },
  {
    id: 'flowmap',
    label: 'FlowMap',
    beta: true,
    tooltip: `Hybrid network topology — beta, free during preview. Press 2 or ${_shortcut}`,
  },
];

const FLOWMAP_DISABLED_COPY =
  'No FlowMap data in this scan. Re-run with infracanvas scan --with-flowmap to enable.';

export function TabBar() {
  const activeTab = useStore((s) => s.activeTab);
  const setActiveTab = useStore((s) => s.setActiveTab);
  const hasFlowMap = useStore((s) => s.hasFlowMap);
  const refs = useRef<Record<TabId, HTMLButtonElement | null>>({
    canvas: null,
    flowmap: null,
  });

  const focusTab = (id: TabId) => {
    refs.current[id]?.focus();
  };

  const handleKey = (e: React.KeyboardEvent<HTMLButtonElement>, index: number) => {
    const last = TABS.length - 1;
    if (e.key === 'ArrowRight') {
      e.preventDefault();
      const next = index === last ? 0 : index + 1;
      setActiveTab(TABS[next].id);
      focusTab(TABS[next].id);
    } else if (e.key === 'ArrowLeft') {
      e.preventDefault();
      const prev = index === 0 ? last : index - 1;
      setActiveTab(TABS[prev].id);
      focusTab(TABS[prev].id);
    } else if (e.key === 'Home') {
      e.preventDefault();
      setActiveTab(TABS[0].id);
      focusTab(TABS[0].id);
    } else if (e.key === 'End') {
      e.preventDefault();
      setActiveTab(TABS[last].id);
      focusTab(TABS[last].id);
    }
  };

  return (
    <div
      role="tablist"
      aria-label="Viewer mode"
      style={{
        height: 36,
        background: '#0f1419',
        borderBottom: '1px solid #252d3d',
        display: 'flex',
        alignItems: 'stretch',
        paddingLeft: 20,
        gap: 0,
        flexShrink: 0,
      }}
    >
      {TABS.map((tab, index) => {
        const isActive = activeTab === tab.id;
        const isDisabled = tab.id === 'flowmap' && !hasFlowMap;
        return (
          <button
            key={tab.id}
            ref={(el) => {
              refs.current[tab.id] = el;
            }}
            role="tab"
            aria-selected={isActive}
            aria-disabled={isDisabled || undefined}
            aria-describedby={isDisabled ? 'flowmap-disabled-tooltip' : undefined}
            aria-controls={`panel-${tab.id}`}
            id={`tab-${tab.id}`}
            tabIndex={isDisabled ? -1 : isActive ? 0 : -1}
            title={isDisabled ? FLOWMAP_DISABLED_COPY : tab.tooltip}
            onClick={() => {
              if (isDisabled) return;
              setActiveTab(tab.id);
            }}
            onKeyDown={(e) => handleKey(e, index)}
            style={{
              minWidth: 120,
              padding: '0 16px',
              border: 'none',
              background: isActive ? 'rgba(59,130,246,0.08)' : 'transparent',
              color: isDisabled ? '#475569' : isActive ? '#F1F5F9' : '#64748B',
              borderBottom: isActive ? '2px solid #3B82F6' : '2px solid transparent',
              fontSize: 12,
              fontWeight: isActive ? 700 : 500,
              cursor: isDisabled ? 'not-allowed' : 'pointer',
              transition: 'color 0.12s, background 0.12s',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 8,
              outlineOffset: 2,
            }}
            onMouseEnter={(e) => {
              if (!isActive && !isDisabled) {
                e.currentTarget.style.color = '#94A3B8';
                e.currentTarget.style.background = 'rgba(45,55,72,0.3)';
              }
            }}
            onMouseLeave={(e) => {
              if (!isActive && !isDisabled) {
                e.currentTarget.style.color = '#64748B';
                e.currentTarget.style.background = 'transparent';
              }
            }}
          >
            {tab.label}
            {tab.beta && (
              <span
                aria-label="beta"
                style={{
                  fontSize: 10,
                  fontWeight: 600,
                  padding: '1px 6px',
                  borderRadius: 4,
                  background: 'rgba(217,119,6,0.12)',
                  color: '#D97706',
                  lineHeight: 1.4,
                }}
              >
                BETA
              </span>
            )}
          </button>
        );
      })}
      {/* WRG-03 §Accessibility: off-screen tooltip node referenced by the
          FlowMap button when disabled (see the describedby attribute above). */}
      <span
        role="tooltip"
        id="flowmap-disabled-tooltip"
        style={{
          position: 'absolute',
          width: 1,
          height: 1,
          padding: 0,
          margin: -1,
          overflow: 'hidden',
          clip: 'rect(0, 0, 0, 0)',
          whiteSpace: 'nowrap',
          border: 0,
        }}
      >
        No FlowMap data in this scan. Re-run with infracanvas scan --with-flowmap to enable.
      </span>
    </div>
  );
}
