'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { OrganizationSwitcher, UserButton } from '@clerk/nextjs'
import { List, GitCompare, Settings } from 'lucide-react'

const NAV_ITEMS = [
  { href: '/scans', label: 'Scans', icon: List },
  { href: '/compare', label: 'Compare', icon: GitCompare },
  { href: '/settings', label: 'Settings', icon: Settings },
]

export function Sidebar() {
  const pathname = usePathname()
  return (
    <aside className="w-[220px] flex-shrink-0 h-screen bg-slate-50 border-r border-slate-200 flex flex-col">
      {/* Top: wordmark + org switcher */}
      <div className="px-4 pt-4 pb-2 space-y-4">
        <span className="text-base font-semibold text-slate-900">InfraCanvas</span>
        <OrganizationSwitcher
          appearance={{
            elements: {
              rootBox: 'w-full',
              organizationSwitcherTrigger: 'w-full text-sm',
            },
          }}
        />
      </div>

      {/* Middle: nav items */}
      <nav className="flex-1 px-2 py-2 space-y-0.5">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(href + '/')
          return (
            <Link
              key={href}
              href={href}
              className={[
                'flex items-center gap-2 px-3 py-2 rounded-md text-sm transition-colors',
                active
                  ? 'bg-white border-l-2 border-amber-400 text-slate-900 font-medium'
                  : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900 border-l-2 border-transparent',
              ].join(' ')}
            >
              <Icon size={16} />
              {label}
            </Link>
          )
        })}
      </nav>

      {/* Bottom: user menu */}
      <div className="px-4 pb-4">
        <UserButton
          appearance={{
            elements: { userButtonBox: 'text-sm' },
          }}
        />
      </div>
    </aside>
  )
}
