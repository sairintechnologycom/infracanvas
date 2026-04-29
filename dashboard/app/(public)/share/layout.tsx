import type { Metadata } from 'next'

/**
 * Share-link layout — public, full-bleed, no sidebar/topbar.
 *
 * Adds <meta name="referrer" content="no-referrer"> to prevent the share token
 * (which lives in the URL path) from leaking to third-party assets loaded by
 * the page. T-07-09-02 mitigation.
 */
export const metadata: Metadata = {
  referrer: 'no-referrer',
  other: { referrer: 'no-referrer' },
  robots: { index: false, follow: false },
}

export default function ShareLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return <div className="min-h-screen bg-slate-50">{children}</div>
}
