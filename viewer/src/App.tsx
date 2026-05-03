import { Suspense, lazy, useEffect } from 'react';
import { ReactFlowProvider } from '@xyflow/react';
import { useViewerStoreOrSingleton } from './store';
import { SummaryBar } from './components/SummaryBar';
import { TabBar } from './components/TabBar';
import { FilterPanel } from './components/FilterPanel';
import { DiagramCanvas } from './components/DiagramCanvas';
import { DetailPanel } from './components/DetailPanel';
import { FlowMapEmptyState } from './components/flowmap/FlowMapEmptyState';

const FlowMapCanvas = lazy(() =>
  import('./components/flowmap/FlowMapCanvas').then((m) => ({ default: m.FlowMapCanvas })),
);
const FlowMapFilterPanel = lazy(() =>
  import('./components/flowmap/FlowMapFilterPanel').then((m) => ({
    default: m.FlowMapFilterPanel,
  })),
);
const PathDetailPanel = lazy(() =>
  import('./components/flowmap/PathDetailPanel').then((m) => ({ default: m.PathDetailPanel })),
);

export default function App() {
  const activeTab = useViewerStoreOrSingleton((s) => s.activeTab);
  const setActiveTab = useViewerStoreOrSingleton((s) => s.setActiveTab);
  const hasFlowMap = useViewerStoreOrSingleton((s) => s.hasFlowMap);

  // Hash init on mount + hashchange listener.
  // Unknown hashes silently fall through to 'canvas'.
  useEffect(() => {
    const readHash = () => {
      const hash = window.location.hash.replace(/^#/, '');
      if (hash === 'flowmap') {
        setActiveTab('flowmap');
      } else {
        setActiveTab('canvas');
      }
    };
    readHash();
    window.addEventListener('hashchange', readHash);
    return () => window.removeEventListener('hashchange', readHash);
  }, [setActiveTab]);

  // Sync activeTab → URL hash via replaceState (not pushState — tab switches
  // must not pollute history).
  useEffect(() => {
    const targetHash = `#${activeTab}`;
    if (window.location.hash !== targetHash) {
      history.replaceState(null, '', targetHash);
    }
  }, [activeTab]);

  // Global keyboard shortcuts — Cmd/Ctrl+\, 1, 2.
  // Suppressed when focus is inside form fields.
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      const tag = target?.tagName;
      if (
        tag === 'INPUT' ||
        tag === 'TEXTAREA' ||
        tag === 'SELECT' ||
        target?.isContentEditable === true
      ) {
        return;
      }

      // Cmd/Ctrl + \ toggles Canvas <-> FlowMap
      if ((e.metaKey || e.ctrlKey) && e.key === '\\') {
        e.preventDefault();
        setActiveTab(activeTab === 'canvas' ? 'flowmap' : 'canvas');
        return;
      }

      // '1' jumps to Canvas
      if (e.key === '1' && !e.metaKey && !e.ctrlKey && !e.altKey) {
        setActiveTab('canvas');
        return;
      }

      // '2' jumps to FlowMap — always navigable; shows empty state if no data
      if (e.key === '2' && !e.metaKey && !e.ctrlKey && !e.altKey) {
        setActiveTab('flowmap');
        return;
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [activeTab, setActiveTab]);

  const isFlowMap = activeTab === 'flowmap';

  return (
    <ReactFlowProvider>
      <div className="flex flex-col h-full w-full" style={{ background: '#f8fafc' }}>
        <SummaryBar />
        <TabBar />
        <div
          className="flex flex-1 min-h-0"
          role="tabpanel"
          id={`panel-${activeTab}`}
          aria-labelledby={`tab-${activeTab}`}
        >
          {isFlowMap ? (
            hasFlowMap ? (
              <Suspense fallback={<div className="flex-1" />}>
                <FlowMapFilterPanel />
                <div className="flex-1 min-w-0">
                  <FlowMapCanvas />
                </div>
                <PathDetailPanel />
              </Suspense>
            ) : (
              <FlowMapEmptyState />
            )
          ) : (
            <>
              <FilterPanel />
              <div className="flex-1 min-w-0">
                <DiagramCanvas />
              </div>
              <DetailPanel />
            </>
          )}
        </div>
      </div>
    </ReactFlowProvider>
  );
}
