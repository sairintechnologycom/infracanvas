import type { SVGProps } from 'react';
export function AzureFirewall(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 18 18" xmlns="http://www.w3.org/2000/svg" {...props}>
      <defs>
        <linearGradient id="azurefw-a" x1="9" y1="16" x2="9" y2="2" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#0078d4" />
          <stop offset="0.82" stopColor="#5ea0ef" />
        </linearGradient>
      </defs>
      <rect x="1" y="2" width="16" height="14" rx="1.5" fill="url(#azurefw-a)" />
      <rect x="3" y="4.5" width="12" height="2" rx="0.4" fill="#fff" />
      <rect x="3" y="8" width="12" height="2" rx="0.4" fill="#fff" />
      <rect x="3" y="11.5" width="12" height="2" rx="0.4" fill="#fff" />
    </svg>
  );
}
