import type { SVGProps } from 'react';
export function AzureResourceGroup(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 18 18" xmlns="http://www.w3.org/2000/svg" {...props}>
      <defs>
        <linearGradient id="azurerg-a" x1="9" y1="16" x2="9" y2="2" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#0078d4" />
          <stop offset="0.82" stopColor="#5ea0ef" />
        </linearGradient>
      </defs>
      <rect x="1" y="2" width="16" height="14" rx="1.5" fill="url(#azurerg-a)" />
      <path d="M2.5 7h13v7.5a1 1 0 01-1 1h-11a1 1 0 01-1-1V7z" fill="#fff" opacity="0.2" />
      <path d="M2.5 7h5l1-1.5h7v1.5H2.5z" fill="#fff" />
      <rect x="2.5" y="7" width="13" height="7.5" rx="0.5" fill="none" stroke="#fff" strokeWidth="0.8" />
    </svg>
  );
}
