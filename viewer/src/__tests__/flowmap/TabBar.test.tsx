import { describe, test, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

import { TabBar } from '../../components/TabBar';
import { useStore } from '../../store';

describe('TabBar (ARIA + keyboard)', () => {
  beforeEach(() => {
    useStore.setState({ activeTab: 'canvas' });
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
