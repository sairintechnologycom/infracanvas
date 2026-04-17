import type { SVGProps } from 'react';
export function AzureVirtualMachine(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 18 18" xmlns="http://www.w3.org/2000/svg" {...props}>
      <defs>
        <linearGradient id="azurevm-a" x1="9" y1="14.44" x2="9" y2="3.05" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#0078d4" />
          <stop offset="0.82" stopColor="#5ea0ef" />
        </linearGradient>
      </defs>
      <rect x="1" y="3.05" width="16" height="11.39" rx="1" fill="url(#azurevm-a)" />
      <rect x="2.5" y="4.55" width="13" height="7.5" fill="#fff" />
      <rect x="6.5" y="14.5" width="5" height="0.75" fill="#5ea0ef" />
    </svg>
  );
}
