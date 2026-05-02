import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import '@fontsource/inter/400.css';
import '@fontsource/inter/500.css';
import '@fontsource/inter/600.css';
import '@fontsource/inter/700.css';
import '@fontsource/jetbrains-mono/400.css';
import '@fontsource/jetbrains-mono/500.css';
import '@fontsource/jetbrains-mono/600.css';
import App from './App';
import { useStore } from './store';
import { sampleData } from './sample-data';
import './index.css';

// Bootstrap before first render so components read real data immediately.
// In the standalone HTML viewer, window.__INFRACANVAS_DATA__ is injected by
// the CLI exporter. In all other contexts (tests, Storybook) it is unset,
// so sampleData is used as the fallback.
const injected = window.__INFRACANVAS_DATA__;
useStore.getState().setGraph(injected ?? sampleData);
useStore.getState().setGateMode(window.__INFRACANVAS_GATE__ ?? true);
useStore.getState().setHasFlowMap(Boolean(injected?.flowmap));

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
