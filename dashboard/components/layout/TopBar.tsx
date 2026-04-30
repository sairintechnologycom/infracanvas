'use client'
import { usePathname } from 'next/navigation'
import { Menu } from 'lucide-react'
import { TopBarActionsSlot } from './TopBarActions'

interface TopBarProps {
  onMenuToggle?: () => void
}

export function TopBar({ onMenuToggle }: TopBarProps) {
  const pathname = usePathname()
  // Simple breadcrumb: capitalize each path segment
  const segments = (pathname ?? '').split('/').filter(Boolean)
  return (
    <header
      data-testid="topbar"
      className="h-12 flex-shrink-0 bg-slate-50 border-b border-slate-200 flex items-center px-6 gap-2 flex-wrap md:flex-nowrap"
    >
      <button
        type="button"
        className="md:hidden mr-3 p-1.5 rounded hover:bg-slate-100"
        onClick={onMenuToggle}
        aria-label="Open navigation menu"
        data-testid="hamburger-button"
      >
        <Menu className="h-5 w-5 text-slate-600" />
      </button>
      <nav className="flex items-center gap-1 text-sm flex-1">
        {segments.map((seg, i) => {
          const isLast = i === segments.length - 1
          return (
            <span key={i} className="flex items-center gap-1">
              {i > 0 && <span className="text-slate-300">/</span>}
              <span className={isLast ? 'text-slate-900' : 'text-slate-500'}>
                {seg.charAt(0).toUpperCase() + seg.slice(1)}
              </span>
            </span>
          )
        })}
      </nav>
      {/* Page-level actions injected by child pages via TopBarActions slot pattern (RMD-05) */}
      <div className="ml-auto flex items-center gap-2" data-testid="topbar-actions">
        <TopBarActionsSlot />
      </div>
    </header>
  )
}
