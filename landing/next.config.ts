import type { NextConfig } from 'next'

// Note: `output: 'export'` enables fully static export (generates `out/` directory).
// When deploying to Vercel, you can remove this line — Vercel handles SSG natively
// without static export mode, enabling features like ISR and image optimisation.
const nextConfig: NextConfig = {
  output: 'export',
}

export default nextConfig
