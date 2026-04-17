import type { SVGProps } from 'react';
export function AzurePublicIp(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 18 18" xmlns="http://www.w3.org/2000/svg" {...props}>
      <defs>
        <linearGradient id="azurepip-a" x1="9" y1="16" x2="9" y2="2" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#0078d4" />
          <stop offset="0.82" stopColor="#5ea0ef" />
        </linearGradient>
      </defs>
      <rect x="1" y="2" width="16" height="14" rx="1.5" fill="url(#azurepip-a)" />
      <circle cx="8" cy="9" r="4.5" fill="none" stroke="#fff" strokeWidth="1" />
      <ellipse cx="8" cy="9" rx="1.8" ry="4.5" fill="none" stroke="#fff" strokeWidth="0.8" />
      <line x1="3.5" y1="9" x2="12.5" y2="9" stroke="#fff" strokeWidth="0.8" />
      <path d="M13 7l2 2-2 2" stroke="#fff" strokeWidth="1" fill="none" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
