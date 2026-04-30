'use client'
import { usePathname } from 'next/navigation'
import { Menu } from 'lucide-react'
import { TopBarActionsSlot } from './TopBarActions'

interface TopBarProps {
  onMenuToggle?: () => void
}

/** Static-segment label table — sentence case, never blind title-case. */
const LABELS: Record<string, string> = {
  scans: 'Scans',
  compare: 'Compare',
  settings: 'Settings',
  billing: 'Billing',
  members: 'Members',
  integrations: 'Integrations',
  share: 'Share',
}

/** RFC 4122 v1-v5 UUID. Dynamic crumb segments matching this are filtered out
 *  so we never render `Scans / 0a1b2c3d-...` (RMD-06; T-07.1-17 mitigation). */
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

function labelFor(seg: string): string | null {
  if (seg in LABELS) return LABELS[seg]
  if (UUID_RE.test(seg)) return null
  // Fallback for unknown static segments: sentence case (capitalize first letter only)
  return seg.charAt(0).toUpperCase() + seg.slice(1)
}

export function TopBar({ onMenuToggle }: TopBarProps) {
  const pathname = usePathname()
  const rawSegments = (pathname ?? '').split('/').filter(Boolean)
  const crumbs = rawSegments
    .map((seg) => labelFor(seg))
    .filter((s): s is string => s !== null)
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
      <nav className="flex items-center gap-1 text-sm flex-1" aria-label="Breadcrumb">
        {crumbs.map((label, i) => {
          const isLast = i === crumbs.length - 1
          return (
            <span key={i} className="flex items-center gap-1">
              {i > 0 && <span className="text-slate-300">/</span>}
              <span className={isLast ? 'text-slate-900' : 'text-slate-500'}>{label}</span>
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
