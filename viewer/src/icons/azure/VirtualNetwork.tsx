import type { SVGProps } from 'react';
export function AzureVirtualNetwork(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 18 18" xmlns="http://www.w3.org/2000/svg" {...props}>
      <defs>
        <linearGradient id="azurevnet-a" x1="9" y1="16" x2="9" y2="2" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#0078d4" />
          <stop offset="0.82" stopColor="#5ea0ef" />
        </linearGradient>
      </defs>
      <rect x="1" y="2" width="16" height="14" rx="1.5" fill="url(#azurevnet-a)" />
      <rect x="2.5" y="4" width="5.5" height="4" rx="0.5" fill="none" stroke="#fff" strokeWidth="1" />
      <rect x="10" y="4" width="5.5" height="4" rx="0.5" fill="none" stroke="#fff" strokeWidth="1" />
      <line x1="8" y1="6" x2="10" y2="6" stroke="#fff" strokeWidth="1" />
      <rect x="6" y="11" width="6" height="3" rx="0.5" fill="none" stroke="#fff" strokeWidth="1" />
      <line x1="9" y1="8" x2="9" y2="11" stroke="#fff" strokeWidth="1" />
    </svg>
  );
}
