import type { SVGProps } from 'react';
export function AzureLoadBalancer(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 18 18" xmlns="http://www.w3.org/2000/svg" {...props}>
      <defs>
        <linearGradient id="azurelb-a" x1="9" y1="16" x2="9" y2="2" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#0078d4" />
          <stop offset="0.82" stopColor="#5ea0ef" />
        </linearGradient>
      </defs>
      <rect x="1" y="2" width="16" height="14" rx="1.5" fill="url(#azurelb-a)" />
      <circle cx="5" cy="9" r="1.5" fill="#fff" />
      <circle cx="13" cy="6" r="1.5" fill="#fff" />
      <circle cx="13" cy="12" r="1.5" fill="#fff" />
      <line x1="6.5" y1="9" x2="11.5" y2="6" stroke="#fff" strokeWidth="1" />
      <line x1="6.5" y1="9" x2="11.5" y2="12" stroke="#fff" strokeWidth="1" />
    </svg>
  );
}
