import type { SVGProps } from 'react';
export function AzureAppService(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 18 18" xmlns="http://www.w3.org/2000/svg" {...props}>
      <defs>
        <linearGradient id="azureapp-a" x1="9" y1="16" x2="9" y2="2" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#0078d4" />
          <stop offset="0.82" stopColor="#5ea0ef" />
        </linearGradient>
      </defs>
      <rect x="1" y="2" width="16" height="14" rx="1.5" fill="url(#azureapp-a)" />
      <circle cx="9" cy="9" r="5" fill="none" stroke="#fff" strokeWidth="1" />
      <ellipse cx="9" cy="9" rx="2" ry="5" fill="none" stroke="#fff" strokeWidth="0.8" />
      <line x1="4" y1="9" x2="14" y2="9" stroke="#fff" strokeWidth="0.8" />
      <line x1="5" y1="6.5" x2="13" y2="6.5" stroke="#fff" strokeWidth="0.6" />
      <line x1="5" y1="11.5" x2="13" y2="11.5" stroke="#fff" strokeWidth="0.6" />
    </svg>
  );
}
