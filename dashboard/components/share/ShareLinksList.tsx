'use client'

import { useEffect, useState } from 'react'
import type { ShareLink } from '@/lib/types'
import { RevokeShareLinkButton } from './RevokeShareLinkButton'

type Props = {
  scanId: string
  /**
   * Bumping this from the parent triggers a refetch — used by ShareModal
   * after a new link is generated, and internally by this component after a
   * successful revoke.
   */
  refreshKey?: number
}

/**
 * ShareLinksList — Active share-links list inside ShareModal (RMD-04).
 *
 * Fetches GET /api/scan-share?scan_id={id} on mount and whenever `refreshKey`
 * changes, then renders one row per active link in the UI-SPEC format:
 *   `Expires {date} · Created by {user} · {with password / no password}`
 * with a [Revoke] text-link aligned right that opens an AlertDialog
 * destructive confirm (see RevokeShareLinkButton).
 *
 * On a successful revoke, the child fires `onRevoked()` which bumps the
 * internal `reloadTick`, triggering a refetch so the row disappears.
 */
export function ShareLinksList({ scanId, refreshKey = 0 }: Props) {
  const [links, setLinks] = useState<ShareLink[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [reloadTick, setReloadTick] = useState(0)

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      setError(null)
      try {
        const res = await fetch(
          `/api/scan-share?scan_id=${encodeURIComponent(scanId)}`,
          { cache: 'no-store' },
        )
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const body = (await res.json()) as { links: ShareLink[] }
        if (!cancelled) setLinks(body.links)
      } catch (e) {
        if (!cancelled) setError((e as Error).message)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [scanId, refreshKey, reloadTick])

  const triggerReload = () => setReloadTick((t) => t + 1)

  if (loading) {
    return (
      <div className="text-sm text-slate-500" aria-live="polite">
        Loading share links…
      </div>
    )
  }
  if (error) {
    return (
      <div className="text-sm text-red-600" role="alert">
        Couldn&apos;t load share links.
      </div>
    )
  }
  if (links.length === 0) {
    return <p className="text-sm text-slate-500">No active share links.</p>
  }

  return (
    <ul className="divide-y divide-slate-100">
      {links.map((link) => (
        <li
          key={link.id}
          className="py-2 flex items-center justify-between gap-4"
        >
          <span className="text-sm text-slate-700">
            Expires {formatExpiry(link.expires_at)}
            {' · '}Created by {link.created_by}
            {' · '}
            {link.has_password ? 'with password' : 'no password'}
          </span>
          <RevokeShareLinkButton
            scanId={scanId}
            shareId={link.id}
            onRevoked={triggerReload}
          />
        </li>
      ))}
    </ul>
  )
}

/**
 * UI-SPEC §Voice rules: dates in modals/strips render as "Apr 28" (short
 * month + day). `null` expires_at means "Never expires".
 */
function formatExpiry(iso: string | null): string {
  if (iso === null) return 'Never'
  const d = new Date(iso)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}
