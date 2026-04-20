import { describe, test, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

import { TabBar } from '../../components/TabBar';
import { useStore } from '../../store';

describe('TabBar (ARIA + keyboard)', () => {
  beforeEach(() => {
    // Phase 4 WRG-03: default hasFlowMap=true here so existing behaviour tests
    // exercise the enabled-FlowMap-tab path. A dedicated `describe` below
    // covers the disabled branch.
    useStore.setState({ activeTab: 'canvas', hasFlowMap: true });
  });

  test('renders role=tablist with two tabs', () => {
    render(<TabBar />);
    expect(screen.getByRole('tablist')).toBeInTheDocument();
    expect(screen.getAllByRole('tab')).toHaveLength(2);
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

  test('clicking FlowMap activates it', () => {
    render(<TabBar />);
    const flowmapTab = screen.getByRole('tab', { name: /flowmap/i });
    fireEvent.click(flowmapTab);
    expect(useStore.getState().activeTab).toBe('flowmap');
    expect(flowmapTab.getAttribute('aria-selected')).toBe('true');
  });

  test('ArrowRight cycles to next tab', () => {
    render(<TabBar />);
    const canvasTab = screen.getByRole('tab', { name: /canvas/i });
    canvasTab.focus();
    fireEvent.keyDown(canvasTab, { key: 'ArrowRight' });
    expect(useStore.getState().activeTab).toBe('flowmap');
  });

  test('ArrowLeft from first tab wraps to last', () => {
    render(<TabBar />);
    const canvasTab = screen.getByRole('tab', { name: /canvas/i });
    canvasTab.focus();
    fireEvent.keyDown(canvasTab, { key: 'ArrowLeft' });
    expect(useStore.getState().activeTab).toBe('flowmap');
  });

  test('End jumps to last tab', () => {
    render(<TabBar />);
    const canvasTab = screen.getByRole('tab', { name: /canvas/i });
    canvasTab.focus();
    fireEvent.keyDown(canvasTab, { key: 'End' });
    expect(useStore.getState().activeTab).toBe('flowmap');
  });

  test('Home jumps to first tab', () => {
    useStore.setState({ activeTab: 'flowmap' });
    render(<TabBar />);
    const flowmapTab = screen.getByRole('tab', { name: /flowmap/i });
    flowmapTab.focus();
    fireEvent.keyDown(flowmapTab, { key: 'Home' });
    expect(useStore.getState().activeTab).toBe('canvas');
  });

  test('active tab has tabIndex 0; inactive has -1', () => {
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

describe('TabBar (WRG-03: FlowMap tab disabled when hasFlowMap=false)', () => {
  beforeEach(() => {
    useStore.setState({ activeTab: 'canvas', hasFlowMap: false });
  });

  test('TBR-D-01: FlowMap tab renders aria-disabled=true when hasFlowMap=false', () => {
    render(<TabBar />);
    const flowmapTab = screen.getByRole('tab', { name: /flowmap/i });
    expect(flowmapTab.getAttribute('aria-disabled')).toBe('true');
  });

  test('TBR-D-02: clicking disabled FlowMap does not change activeTab', () => {
    render(<TabBar />);
    const flowmapTab = screen.getByRole('tab', { name: /flowmap/i });
    fireEvent.click(flowmapTab);
    expect(useStore.getState().activeTab).toBe('canvas');
  });

  test('TBR-D-03: disabled FlowMap tab exposes the UI-SPEC remediation copy via title', () => {
    render(<TabBar />);
    const flowmapTab = screen.getByRole('tab', { name: /flowmap/i });
    expect(flowmapTab.getAttribute('title')).toBe(
      'No FlowMap data in this scan. Re-run with infracanvas scan --with-flowmap to enable.',
    );
  });

  test('TBR-D-04: disabled FlowMap tab wires aria-describedby to the off-screen tooltip', () => {
    render(<TabBar />);
    const flowmapTab = screen.getByRole('tab', { name: /flowmap/i });
    expect(flowmapTab.getAttribute('aria-describedby')).toBe('flowmap-disabled-tooltip');
  });

  test('TBR-D-05: off-screen tooltip node is present with the exact UI-SPEC copy', () => {
    render(<TabBar />);
    const tooltip = document.getElementById('flowmap-disabled-tooltip');
    expect(tooltip).not.toBeNull();
    expect(tooltip?.getAttribute('role')).toBe('tooltip');
    expect(tooltip?.textContent).toContain(
      'No FlowMap data in this scan. Re-run with infracanvas scan --with-flowmap to enable.',
    );
  });

  test('TBR-D-06: disabled FlowMap tab uses tabIndex=-1', () => {
    render(<TabBar />);
    const flowmapTab = screen.getByRole('tab', { name: /flowmap/i });
    expect(flowmapTab.getAttribute('tabindex')).toBe('-1');
  });

  test('TBR-D-07: enabling hasFlowMap removes the disabled state', () => {
    useStore.setState({ hasFlowMap: true });
    render(<TabBar />);
    const flowmapTab = screen.getByRole('tab', { name: /flowmap/i });
    expect(flowmapTab.getAttribute('aria-disabled')).toBeNull();
    fireEvent.click(flowmapTab);
    expect(useStore.getState().activeTab).toBe('flowmap');
  });
});
