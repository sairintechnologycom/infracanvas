'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'

interface Tab {
  href: string
  label: string
}

const TABS: Tab[] = [
  { href: '/settings/members', label: 'Members' },
  { href: '/settings/billing', label: 'Billing' },
  { href: '/settings/integrations', label: 'Integrations' },
]

export default function SettingsLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const pathname = usePathname()
  return (
    <div className="max-w-7xl mx-auto px-8 py-8">
      <h1 className="text-base font-semibold text-slate-900 mb-6">Settings</h1>
      <nav className="flex border-b border-slate-200 mb-8" aria-label="Settings sections">
        {TABS.map(tab => {
          const isActive = pathname.startsWith(tab.href)
          const baseClass =
            'inline-flex items-center px-4 py-3 text-sm transition-colors -mb-px'
          const stateClass = isActive
            ? 'border-b-2 border-amber-400 text-slate-900 font-medium'
            : 'text-slate-500 hover:text-slate-700 border-b-2 border-transparent'
          return (
            <Link
              key={tab.href}
              href={tab.href}
              className={`${baseClass} ${stateClass}`}
            >
              {tab.label}
            </Link>
          )
        })}
      </nav>
      <div>{children}</div>
    </div>
  )
}
