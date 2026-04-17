import type { SVGProps } from 'react';
export function AzureKeyVault(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 18 18" xmlns="http://www.w3.org/2000/svg" {...props}>
      <defs>
        <linearGradient id="azurekv-a" x1="9" y1="16" x2="9" y2="2" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#0078d4" />
          <stop offset="0.82" stopColor="#5ea0ef" />
        </linearGradient>
      </defs>
      <rect x="1" y="2" width="16" height="14" rx="1.5" fill="url(#azurekv-a)" />
      <circle cx="7.5" cy="8.5" r="2.5" fill="none" stroke="#fff" strokeWidth="1.2" />
      <circle cx="7.5" cy="8.5" r="0.9" fill="#fff" />
      <path d="M9.8 10.2l1.2 1.2m0 0l1 1m-1-1l1-1" stroke="#fff" strokeWidth="1.1" strokeLinecap="round" />
    </svg>
  );
}
