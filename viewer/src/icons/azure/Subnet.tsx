import type { SVGProps } from 'react';
export function AzureSubnet(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 18 18" xmlns="http://www.w3.org/2000/svg" {...props}>
      <defs>
        <linearGradient id="azurenet-a" x1="9" y1="16" x2="9" y2="2" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#0078d4" />
          <stop offset="0.82" stopColor="#5ea0ef" />
        </linearGradient>
      </defs>
      <rect x="1" y="2" width="16" height="14" rx="1.5" fill="url(#azurenet-a)" />
      <rect x="3" y="4" width="12" height="10" rx="1" fill="none" stroke="#fff" strokeWidth="1" strokeDasharray="2 1.5" />
      <rect x="5.5" y="6.5" width="7" height="5" rx="0.5" fill="#fff" opacity="0.25" />
    </svg>
  );
}
