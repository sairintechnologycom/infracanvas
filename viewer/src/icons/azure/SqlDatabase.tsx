import type { SVGProps } from 'react';
export function AzureSqlDatabase(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 18 18" xmlns="http://www.w3.org/2000/svg" {...props}>
      <defs>
        <linearGradient id="azuresql-a" x1="9" y1="16" x2="9" y2="2" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#0078d4" />
          <stop offset="0.82" stopColor="#5ea0ef" />
        </linearGradient>
      </defs>
      <rect x="1" y="2" width="16" height="14" rx="1.5" fill="url(#azuresql-a)" />
      <ellipse cx="9" cy="5.5" rx="4.5" ry="1.5" fill="none" stroke="#fff" strokeWidth="1" />
      <path d="M4.5 5.5v7c0 .83 2.02 1.5 4.5 1.5s4.5-.67 4.5-1.5v-7" fill="none" stroke="#fff" strokeWidth="1" />
      <line x1="4.5" y1="9" x2="13.5" y2="9" stroke="#fff" strokeWidth="0.75" strokeDasharray="1.5 1" />
    </svg>
  );
}
