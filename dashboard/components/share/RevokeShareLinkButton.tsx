'use client'

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import { toast } from 'sonner'

type Props = {
  scanId: string
  shareId: string
  onRevoked: () => void
}

/**
 * RevokeShareLinkButton — destructive confirm flow for revoking a share link
 * (RMD-03 toasts firing + RMD-04 destructive AlertDialog).
 *
 * Renders a red text-link [Revoke] (per UI-SPEC §Share modal — never a filled
 * red button — destructive but recoverable via re-create) that opens a shadcn
 * `<AlertDialog/>` with the spec'd destructive copy. Confirming fires
 * `DELETE /api/scan-share?scan_id&share_id`, then `toast.success('Share link
 * revoked')`, then calls `onRevoked()` so the parent refetches the list.
 *
 * On failure: `toast.error('Could not revoke share link.')` and `onRevoked` is
 * NOT invoked — the row stays in place so the user can retry. Toast strings
 * are static literals (T-07.1-15: no backend error message concatenation).
 *
 * The Confirm button uses shadcn `variant="destructive"` instead of raw
 * `bg-red-600` to preserve the focus-visible ring (Pitfall 4).
 */
export function RevokeShareLinkButton({ scanId, shareId, onRevoked }: Props) {
  async function handleRevoke() {
    const url = `/api/scan-share?scan_id=${encodeURIComponent(
      scanId,
    )}&share_id=${encodeURIComponent(shareId)}`
    try {
      const res = await fetch(url, { method: 'DELETE' })
      if (!res.ok) {
        toast.error('Could not revoke share link.')
        return
      }
      toast.success('Share link revoked')
      onRevoked()
    } catch {
      toast.error('Could not revoke share link.')
    }
  }

  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <button
          type="button"
          aria-label="Revoke share link"
          className="text-sm text-red-600 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400 focus-visible:ring-offset-2 rounded-sm"
        >
          Revoke
        </button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Revoke this share link?</AlertDialogTitle>
          <AlertDialogDescription>
            Anyone with this link will get a 410 Gone response immediately.
            This cannot be undone — they&apos;ll need a new link to view the
            scan.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction variant="destructive" onClick={handleRevoke}>
            Revoke
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
