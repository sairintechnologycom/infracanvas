import { useRef } from 'react';
import { useViewerStoreOrSingleton } from '../store';

type TabId = 'canvas' | 'flowmap' | 'costlens';

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
  {
    id: 'costlens',
    label: 'CostLens',
    tooltip: 'Shared infrastructure cost allocation — press 3',
  },
];

export function TabBar() {
  const activeTab = useViewerStoreOrSingleton((s) => s.activeTab);
  const setActiveTab = useViewerStoreOrSingleton((s) => s.setActiveTab);
  const refs = useRef<Record<TabId, HTMLButtonElement | null>>({
    canvas: null,
    flowmap: null,
    costlens: null,
  });

  const focusTab = (id: TabId) => {
    refs.current[id]?.focus();
  };

  const handleKey = (e: React.KeyboardEvent<HTMLButtonElement>, index: number) => {
    const navigable = TABS;
    const navIdx = navigable.findIndex((t) => t.id === TABS[index].id);
    if (navIdx === -1) return;
    const last = navigable.length - 1;
    if (e.key === 'ArrowRight') {
      e.preventDefault();
      const next = navIdx === last ? 0 : navIdx + 1;
      setActiveTab(navigable[next].id);
      focusTab(navigable[next].id);
    } else if (e.key === 'ArrowLeft') {
      e.preventDefault();
      const prev = navIdx === 0 ? last : navIdx - 1;
      setActiveTab(navigable[prev].id);
      focusTab(navigable[prev].id);
    } else if (e.key === 'Home') {
      e.preventDefault();
      setActiveTab(navigable[0].id);
      focusTab(navigable[0].id);
    } else if (e.key === 'End') {
      e.preventDefault();
      setActiveTab(navigable[last].id);
      focusTab(navigable[last].id);
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
        return (
          <button
            key={tab.id}
            ref={(el) => {
              refs.current[tab.id] = el;
            }}
            role="tab"
            aria-selected={isActive}
            aria-controls={`panel-${tab.id}`}
            id={`tab-${tab.id}`}
            tabIndex={isActive ? 0 : -1}
            title={tab.tooltip}
            onClick={() => {
              setActiveTab(tab.id);
            }}
            onKeyDown={(e) => handleKey(e, index)}
            style={{
              minWidth: 120,
              padding: '0 16px',
              border: 'none',
              background: isActive ? 'rgba(59,130,246,0.08)' : 'transparent',
              color: isActive ? '#F1F5F9' : '#64748B',
              borderBottom: isActive ? '2px solid #3B82F6' : '2px solid transparent',
              fontSize: 12,
              fontWeight: isActive ? 700 : 500,
              cursor: 'pointer',
              transition: 'color 0.12s, background 0.12s',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 8,
              outlineOffset: 2,
            }}
            onMouseEnter={(e) => {
              if (!isActive) {
                e.currentTarget.style.color = '#94A3B8';
                e.currentTarget.style.background = 'rgba(45,55,72,0.3)';
              }
            }}
            onMouseLeave={(e) => {
              if (!isActive) {
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
    </div>
  );
}
