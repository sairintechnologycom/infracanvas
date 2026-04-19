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
  const activeTab = useStore((s) => s.activeTab);

  useEffect(() => {
    const injected = window.__INFRACANVAS_DATA__;
    const data: ResourceGraph = injected ?? sampleData;
    setGraph(data);
    const gateMode = window.__INFRACANVAS_GATE__ ?? true;
    setGateMode(gateMode);
  }, [setGraph, setGateMode]);

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
