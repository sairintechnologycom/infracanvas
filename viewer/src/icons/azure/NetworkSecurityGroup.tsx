import type { SVGProps } from 'react';
export function AzureNetworkSecurityGroup(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 18 18" xmlns="http://www.w3.org/2000/svg" {...props}>
      <defs>
        <linearGradient id="azurenic-a" x1="9" y1="16" x2="9" y2="2" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#0078d4" />
          <stop offset="0.82" stopColor="#5ea0ef" />
        </linearGradient>
      </defs>
      <rect x="1" y="2" width="16" height="14" rx="1.5" fill="url(#azurenic-a)" />
      <path d="M9 3.5 L15 6v4c0 3-2.5 4.5-6 5.5-3.5-1-6-2.5-6-5.5V6z" fill="none" stroke="#fff" strokeWidth="1" strokeLinejoin="round" />
      <path d="M6.5 9l1.5 1.5 3.5-3" stroke="#fff" strokeWidth="1.2" fill="none" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
