'use client'
import { Share2 } from 'lucide-react'

interface Props {
  scanId: string
}

/**
 * Share button stub — opens ShareModal (Plan 07-09).
 * scanId is passed through so the modal can POST to /v1/scans/{scanId}/share-links.
 */
export function ShareButton({ scanId }: Props) {
  // TODO (Plan 07-09): replace onClick with openShareModal(scanId)
  const handleClick = () => {
    // eslint-disable-next-line no-console
    console.info('[ShareButton] Share modal not yet wired — Plan 07-09', scanId)
  }

  return (
    <button
      onClick={handleClick}
      className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-slate-300 rounded-md text-slate-600 hover:bg-slate-100 whitespace-nowrap"
      aria-label="Share this scan"
      data-testid="share-button"
    >
      <Share2 size={14} />
      Share
    </button>
  )
}
