import type { SVGProps } from 'react';
export function AzureFunctionApp(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 18 18" xmlns="http://www.w3.org/2000/svg" {...props}>
      <defs>
        <linearGradient id="azurefn-a" x1="9" y1="16" x2="9" y2="2" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#0078d4" />
          <stop offset="0.82" stopColor="#5ea0ef" />
        </linearGradient>
      </defs>
      <rect x="1" y="2" width="16" height="14" rx="1.5" fill="url(#azurefn-a)" />
      <path d="M7 4.5 L5 9h3.5L6 13.5h1L12 8H8.5L11 4.5z" fill="#fff" />
    </svg>
  );
}
