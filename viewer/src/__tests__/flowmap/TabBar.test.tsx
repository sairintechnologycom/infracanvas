import { describe, test, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

import { TabBar } from '../../components/TabBar';
import { useStore } from '../../store';

describe('TabBar (ARIA + keyboard)', () => {
  beforeEach(() => {
    useStore.setState({ activeTab: 'canvas', hasFlowMap: true });
  });

  test('renders role=tablist with three tabs (Canvas, FlowMap, CostLens)', () => {
    render(<TabBar />);
    expect(screen.getByRole('tablist')).toBeInTheDocument();
    expect(screen.getAllByRole('tab')).toHaveLength(3);
  });

  test('Canvas tab is initially selected', () => {
    render(<TabBar />);
    const canvasTab = screen.getByRole('tab', { name: /canvas/i });
    expect(canvasTab.getAttribute('aria-selected')).toBe('true');
  });

  test('FlowMap tab carries BETA label', () => {
    render(<TabBar />);
    expect(screen.getByText('BETA')).toBeInTheDocument();
  });

  test('CostLens tab does not carry SOON label (tab is active in Phase 9)', () => {
    render(<TabBar />);
    expect(screen.queryByText('SOON')).toBeNull();
  });

  test('clicking FlowMap activates it', () => {
    render(<TabBar />);
    const flowmapTab = screen.getByRole('tab', { name: /flowmap/i });
    fireEvent.click(flowmapTab);
    expect(useStore.getState().activeTab).toBe('flowmap');
    expect(flowmapTab.getAttribute('aria-selected')).toBe('true');
  });

  test('clicking CostLens activates it', () => {
    render(<TabBar />);
    const costlensTab = screen.getByRole('tab', { name: /costlens/i });
    fireEvent.click(costlensTab);
    expect(useStore.getState().activeTab).toBe('costlens');
    expect(costlensTab.getAttribute('aria-selected')).toBe('true');
  });

  test('ArrowRight from Canvas cycles to FlowMap', () => {
    render(<TabBar />);
    const canvasTab = screen.getByRole('tab', { name: /canvas/i });
    canvasTab.focus();
    fireEvent.keyDown(canvasTab, { key: 'ArrowRight' });
    expect(useStore.getState().activeTab).toBe('flowmap');
  });

  test('CostLens tab activates with ArrowRight from FlowMap', () => {
    useStore.setState({ activeTab: 'flowmap' });
    render(<TabBar />);
    const flowmapTab = screen.getByRole('tab', { name: /flowmap/i });
    flowmapTab.focus();
    fireEvent.keyDown(flowmapTab, { key: 'ArrowRight' });
    expect(useStore.getState().activeTab).toBe('costlens');
  });

  test('ArrowLeft from Canvas wraps to CostLens (last navigable tab)', () => {
    render(<TabBar />);
    const canvasTab = screen.getByRole('tab', { name: /canvas/i });
    canvasTab.focus();
    fireEvent.keyDown(canvasTab, { key: 'ArrowLeft' });
    expect(useStore.getState().activeTab).toBe('costlens');
  });

  test('End jumps to last navigable tab (CostLens)', () => {
    render(<TabBar />);
    const canvasTab = screen.getByRole('tab', { name: /canvas/i });
    canvasTab.focus();
    fireEvent.keyDown(canvasTab, { key: 'End' });
    expect(useStore.getState().activeTab).toBe('costlens');
  });

  test('Home jumps to first tab', () => {
    useStore.setState({ activeTab: 'flowmap' });
    render(<TabBar />);
    const flowmapTab = screen.getByRole('tab', { name: /flowmap/i });
    flowmapTab.focus();
    fireEvent.keyDown(flowmapTab, { key: 'Home' });
    expect(useStore.getState().activeTab).toBe('canvas');
  });

  test('active tab has tabIndex 0; inactive navigable tab has -1', () => {
    render(<TabBar />);
    const canvasTab = screen.getByRole('tab', { name: /canvas/i });
    const flowmapTab = screen.getByRole('tab', { name: /flowmap/i });
    expect(canvasTab.getAttribute('tabindex')).toBe('0');
    expect(flowmapTab.getAttribute('tabindex')).toBe('-1');
  });

  test('each tab has aria-controls pointing to its panel id', () => {
    render(<TabBar />);
    const canvasTab = screen.getByRole('tab', { name: /canvas/i });
    const flowmapTab = screen.getByRole('tab', { name: /flowmap/i });
    expect(canvasTab.getAttribute('aria-controls')).toBe('panel-canvas');
    expect(flowmapTab.getAttribute('aria-controls')).toBe('panel-flowmap');
  });
});

describe('TabBar — FlowMap always-on (hasFlowMap=false shows empty state, not disabled tab)', () => {
  beforeEach(() => {
    useStore.setState({ activeTab: 'canvas', hasFlowMap: false });
  });

  test('FlowMap tab is NOT aria-disabled when hasFlowMap=false', () => {
    render(<TabBar />);
    const flowmapTab = screen.getByRole('tab', { name: /flowmap/i });
    expect(flowmapTab.getAttribute('aria-disabled')).toBeNull();
  });

  test('clicking FlowMap when hasFlowMap=false navigates to flowmap tab', () => {
    render(<TabBar />);
    const flowmapTab = screen.getByRole('tab', { name: /flowmap/i });
    fireEvent.click(flowmapTab);
    expect(useStore.getState().activeTab).toBe('flowmap');
  });

  test('FlowMap tab has normal cursor when hasFlowMap=false', () => {
    render(<TabBar />);
    const flowmapTab = screen.getByRole('tab', { name: /flowmap/i });
    // cursor style is 'pointer', not 'not-allowed'
    expect(flowmapTab.style.cursor).toBe('pointer');
  });
});

describe('TabBar — CostLens tab is fully interactive (Phase 9 activation)', () => {
  beforeEach(() => {
    useStore.setState({ activeTab: 'canvas', hasFlowMap: true });
  });

  test('CostLens tab is NOT aria-disabled', () => {
    render(<TabBar />);
    const costlensTab = screen.getByRole('tab', { name: /costlens/i });
    expect(costlensTab.getAttribute('aria-disabled')).toBeNull();
  });

  test('clicking CostLens changes activeTab to costlens', () => {
    render(<TabBar />);
    const costlensTab = screen.getByRole('tab', { name: /costlens/i });
    fireEvent.click(costlensTab);
    expect(useStore.getState().activeTab).toBe('costlens');
  });

  test('CostLens tab has pointer cursor', () => {
    render(<TabBar />);
    const costlensTab = screen.getByRole('tab', { name: /costlens/i });
    expect(costlensTab.style.cursor).toBe('pointer');
  });

  test('CostLens tab tooltip mentions press 3', () => {
    render(<TabBar />);
    const costlensTab = screen.getByRole('tab', { name: /costlens/i });
    expect(costlensTab.getAttribute('title')).toContain('press 3');
  });
});
