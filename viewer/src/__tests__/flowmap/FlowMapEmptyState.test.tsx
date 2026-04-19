import { describe, test, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { FlowMapEmptyState } from '../../components/flowmap/FlowMapEmptyState';

describe('FlowMapEmptyState', () => {
  test('renders heading and CLI command', () => {
    render(<FlowMapEmptyState />);
    expect(screen.getByText('No network topology collected yet')).toBeInTheDocument();
    expect(screen.getByText('infracanvas scan ./terraform --flowmap')).toBeInTheDocument();
  });

  test('renders beta pill', () => {
    render(<FlowMapEmptyState />);
    expect(screen.getByText('Beta · free during preview')).toBeInTheDocument();
  });

  test('Copy button calls clipboard API', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText } });
    render(<FlowMapEmptyState />);
    fireEvent.click(screen.getByText('Copy'));
    await waitFor(() => {
      expect(writeText).toHaveBeenCalledWith('infracanvas scan ./terraform --flowmap');
    });
  });

  test('has role=status for screen reader', () => {
    render(<FlowMapEmptyState />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });
});
