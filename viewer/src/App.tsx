import { useEffect } from 'react';
import { ReactFlowProvider } from '@xyflow/react';
import { useStore } from './store';
import { SummaryBar } from './components/SummaryBar';
import { FilterPanel } from './components/FilterPanel';
import { DiagramCanvas } from './components/DiagramCanvas';
import { DetailPanel } from './components/DetailPanel';
import { sampleData } from './sample-data';
import type { ResourceGraph } from './types';

export default function App() {
  const setGraph = useStore(s => s.setGraph);

  useEffect(() => {
    const injected = window.__INFRACANVAS_DATA__;
    const data: ResourceGraph = injected ?? sampleData;
    setGraph(data);
  }, [setGraph]);

  return (
    <ReactFlowProvider>
      <div className="flex flex-col h-screen w-screen" style={{ background: '#0a0e17' }}>
        <SummaryBar />
        <div className="flex flex-1 min-h-0">
          <FilterPanel />
          <div className="flex-1 min-w-0">
            <DiagramCanvas />
          </div>
          <DetailPanel />
        </div>
      </div>
    </ReactFlowProvider>
  );
}
