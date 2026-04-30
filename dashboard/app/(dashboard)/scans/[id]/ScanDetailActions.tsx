'use client'
import { useEffect } from 'react'
import { useTopBarActions } from '@/components/layout/TopBarActions'
import { CompareButton } from '@/components/scans/CompareButton'
import { ShareButton } from '@/components/scans/ShareButton'

interface Props {
  scanId: string
  branch?: string | null
}

/**
 * Client wrapper that injects [Compare] [Share] into the top-bar action slot
 * (RMD-05). The /scans/[id] RSC cannot call useTopBarActions directly — this
 * thin client component bridges it.
 *
 * Mounts once per scan-detail render: on mount, calls set([Compare][Share]);
 * on unmount, calls clear() so other routes start with an empty slot.
 */
export function ScanDetailActions({ scanId, branch }: Props) {
  const { set, clear } = useTopBarActions()
  useEffect(() => {
    set(
      <div className="flex items-center gap-2">
        <CompareButton scanId={scanId} branch={branch ?? null} />
        <ShareButton scanId={scanId} />
      </div>,
    )
    return () => {
      clear()
    }
  }, [set, clear, scanId, branch])
  return null
}
