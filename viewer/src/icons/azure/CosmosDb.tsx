import type { SVGProps } from 'react';
export function AzureCosmosDb(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 18 18" xmlns="http://www.w3.org/2000/svg" {...props}>
      <defs>
        <linearGradient id="azurecosmos-a" x1="9" y1="16" x2="9" y2="2" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#0078d4" />
          <stop offset="0.82" stopColor="#5ea0ef" />
        </linearGradient>
      </defs>
      <rect x="1" y="2" width="16" height="14" rx="1.5" fill="url(#azurecosmos-a)" />
      <circle cx="9" cy="9" r="2" fill="#fff" />
      <ellipse cx="9" cy="9" rx="6" ry="2.2" fill="none" stroke="#fff" strokeWidth="0.9" />
      <ellipse cx="9" cy="9" rx="2.2" ry="6" fill="none" stroke="#fff" strokeWidth="0.9" />
    </svg>
  );
}
