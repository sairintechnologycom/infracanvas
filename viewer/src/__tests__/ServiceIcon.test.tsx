import { describe, test, expect } from 'vitest';
import { render } from '@testing-library/react';
import { ServiceIcon } from '../components/icons/ServiceIcon';

describe('ServiceIcon', () => {
  test('renders AWS svg for aws provider + known type', () => {
    const { container } = render(<ServiceIcon provider="aws" type="aws_s3_bucket" />);
    expect(container.querySelector('svg')).toBeInTheDocument();
  });

  test('renders Azure svg for azurerm provider + known type', () => {
    const { container } = render(<ServiceIcon provider="azurerm" type="azurerm_storage_account" />);
    expect(container.querySelector('svg')).toBeInTheDocument();
  });

  test('falls back to geometric for unknown aws type', () => {
    const { container } = render(<ServiceIcon provider="aws" type="aws_totally_fake_type" />);
    // Geometric fallback always returns an svg
    expect(container.querySelector('svg')).toBeInTheDocument();
  });

  test('falls back to geometric for generic provider', () => {
    const { container } = render(<ServiceIcon provider="generic" type="unknown_type" />);
    expect(container.querySelector('svg')).toBeInTheDocument();
  });

  test('respects size prop', () => {
    const { container } = render(<ServiceIcon provider="aws" type="aws_s3_bucket" size={64} />);
    const svg = container.querySelector('svg')!;
    // width/height may be attributes or styles depending on icon source
    const w = svg.getAttribute('width') ?? svg.style.width;
    expect(w).toMatch(/64/);
  });
});
