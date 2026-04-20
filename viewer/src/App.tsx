import { Suspense, lazy, useEffect } from 'react';
import { ReactFlowProvider } from '@xyflow/react';
import { useStore } from './store';
import { SummaryBar } from './components/SummaryBar';
import { TabBar } from './components/TabBar';
import { FilterPanel } from './components/FilterPanel';
import { DiagramCanvas } from './components/DiagramCanvas';
import { DetailPanel } from './components/DetailPanel';
import { sampleData } from './sample-data';
import type { ResourceGraph } from './types';

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
  const setGraph = useStore((s) => s.setGraph);
  const setGateMode = useStore((s) => s.setGateMode);
  const setHasFlowMap = useStore((s) => s.setHasFlowMap);
  const activeTab = useStore((s) => s.activeTab);
  const setActiveTab = useStore((s) => s.setActiveTab);
  const hasFlowMap = useStore((s) => s.hasFlowMap);

  useEffect(() => {
    const injected = window.__INFRACANVAS_DATA__;
    const data: ResourceGraph = injected ?? sampleData;
    setGraph(data);
    const gateMode = window.__INFRACANVAS_GATE__ ?? true;
    setGateMode(gateMode);
    // Phase 4 WRG-03: detect presence of flowmap payload for tab disabled state
    setHasFlowMap(Boolean(injected?.flowmap));
  }, [setGraph, setGateMode, setHasFlowMap]);

  // Phase 4 WRG-03 (D-11): hash init on mount + hashchange listener.
  // Unknown hashes silently fall through to 'canvas' (no error toast).
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

  // Phase 4 WRG-03 (D-11): sync activeTab -> URL hash via replaceState.
  // Use replaceState (not pushState) — tab switches must not pollute history.
  useEffect(() => {
    const targetHash = `#${activeTab}`;
    if (window.location.hash !== targetHash) {
      history.replaceState(null, '', targetHash);
    }
  }, [activeTab]);

  // Phase 4 WRG-03 (D-12): global keyboard shortcuts — Cmd/Ctrl+\, 1, 2.
  // Suppressed when focus is inside form fields (input/textarea/select/CE).
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
        const next = activeTab === 'canvas' ? 'flowmap' : 'canvas';
        if (next === 'flowmap' && !hasFlowMap) return; // no-op when disabled
        setActiveTab(next);
        return;
      }

      // '1' jumps to Canvas
      if (e.key === '1' && !e.metaKey && !e.ctrlKey && !e.altKey) {
        setActiveTab('canvas');
        return;
      }

      // '2' jumps to FlowMap (no-op if disabled)
      if (e.key === '2' && !e.metaKey && !e.ctrlKey && !e.altKey) {
        if (!hasFlowMap) return;
        setActiveTab('flowmap');
        return;
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [activeTab, hasFlowMap, setActiveTab]);

  const isFlowMap = activeTab === 'flowmap';

  return (
    <ReactFlowProvider>
      <div className="flex flex-col h-screen w-screen" style={{ background: '#f8fafc' }}>
        <SummaryBar />
        <TabBar />
        <div
          className="flex flex-1 min-h-0"
          role="tabpanel"
          id={`panel-${activeTab}`}
          aria-labelledby={`tab-${activeTab}`}
        >
          {isFlowMap ? (
            <Suspense fallback={<div className="flex-1" />}>
              <FlowMapFilterPanel />
              <div className="flex-1 min-w-0">
                <FlowMapCanvas />
              </div>
              <PathDetailPanel />
            </Suspense>
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
