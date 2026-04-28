'use client'
import { usePathname } from 'next/navigation'

export function TopBar() {
  const pathname = usePathname()
  // Simple breadcrumb: capitalize each path segment
  const segments = pathname.split('/').filter(Boolean)
  return (
    <header className="h-12 flex-shrink-0 bg-slate-50 border-b border-slate-200 flex items-center px-6 gap-2">
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
      {/* Page-level actions injected by child pages via a slot pattern in later plans */}
    </header>
  )
}
