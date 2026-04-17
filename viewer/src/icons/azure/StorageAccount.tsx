import type { SVGProps } from 'react';
export function AzureStorageAccount(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 18 18" xmlns="http://www.w3.org/2000/svg" {...props}>
      <defs>
        <linearGradient id="azurestorage-a" x1="9" y1="16.42" x2="9" y2="1.58" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#0078d4" />
          <stop offset="0.82" stopColor="#5ea0ef" />
        </linearGradient>
      </defs>
      <rect x="0.75" y="1.58" width="16.5" height="14.84" rx="1.5" fill="url(#azurestorage-a)" />
      <path d="M4.13 5.92h9.74v1.66H4.13zm0 2.74h9.74v1.66H4.13zm0 2.74h6.49v1.66H4.13z" fill="#fff" />
    </svg>
  );
}
