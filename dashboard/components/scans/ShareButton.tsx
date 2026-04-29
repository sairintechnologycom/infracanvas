'use client'
import { useState } from 'react'
import { Share2 } from 'lucide-react'
import { ShareModal } from '@/components/share/ShareModal'

interface Props {
  scanId: string
}

/**
 * Share button — opens ShareModal which posts to
 * POST /v1/scans/{scanId}/share-links via the /api/scan-share route handler.
 */
export function ShareButton({ scanId }: Props) {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <>
      <button
        onClick={() => setIsOpen(true)}
        className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-slate-300 rounded-md text-slate-600 hover:bg-slate-100 whitespace-nowrap"
        aria-label="Share this scan"
        data-testid="share-button"
      >
        <Share2 size={14} />
        Share
      </button>
      <ShareModal
        scanId={scanId}
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
      />
    </>
  )
}
