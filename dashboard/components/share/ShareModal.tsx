'use client'
import { useEffect, useState } from 'react'
import { Copy, Check } from 'lucide-react'
import { toast } from 'sonner'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from '@/components/ui/select'
import { ShareLinksList } from './ShareLinksList'
import type { ShareCreateResp } from '@/lib/types'

interface Props {
  scanId: string
  isOpen: boolean
  onClose: () => void
}

type ExpiryChoice = '1' | '7' | '30' | 'never'

const EXPIRY_OPTIONS: Array<{ value: ExpiryChoice; label: string }> = [
  { value: '1', label: '1 day' },
  { value: '7', label: '7 days' },
  { value: '30', label: '30 days' },
  { value: 'never', label: 'Never (not recommended)' },
]

function expiryToIsoOrNull(choice: ExpiryChoice): string | null {
  if (choice === 'never') return null
  const days = Number.parseInt(choice, 10)
  const dt = new Date(Date.now() + days * 24 * 60 * 60 * 1000)
  return dt.toISOString()
}

/**
 * ShareModal — generates a share link for a scan.
 *
 * Posts to /api/scan-share?scan_id=… (which proxies to backend
 * POST /v1/scans/{id}/share-links). The raw token is shown ONCE — D-08
 * mandates we never persist it. The visible URL uses
 * NEXT_PUBLIC_DASHBOARD_URL when set, falling back to the backend's
 * canonical share_url.
 *
 * Migrated to shadcn `<Dialog/>` in plan 07.1-02 (RMD-01) — focus trap,
 * Escape-to-close, and overlay are all provided by the primitive.
 * Copy success / failure now surface as `toast.success` / `toast.error`
 * via sonner (RMD-03) — no more silent catch.
 */
export function ShareModal({ scanId, isOpen, onClose }: Props) {
  const [expiryChoice, setExpiryChoice] = useState<ExpiryChoice>('7')
  const [password, setPassword] = useState('')
  const [generating, setGenerating] = useState(false)
  const [generatedUrl, setGeneratedUrl] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Reset state whenever the modal closes so reopening starts fresh.
  useEffect(() => {
    if (!isOpen) {
      setExpiryChoice('7')
      setPassword('')
      setGenerating(false)
      setGeneratedUrl(null)
      setCopied(false)
      setError(null)
    }
  }, [isOpen])

  async function handleGenerate() {
    setGenerating(true)
    setError(null)
    try {
      const body: { password?: string; expires_at: string | null } = {
        expires_at: expiryToIsoOrNull(expiryChoice),
      }
      if (password) body.password = password

      const res = await fetch(`/api/scan-share?scan_id=${scanId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!res.ok) {
        setError('Could not generate share link. Please try again.')
        toast.error("Couldn't generate share link. Try again.", {
          duration: Infinity,
        })
        return
      }
      const data = (await res.json()) as ShareCreateResp
      const baseUrl = process.env.NEXT_PUBLIC_DASHBOARD_URL ?? ''
      const url = baseUrl
        ? `${baseUrl}/share/${data.token}`
        : data.share_url
      setGeneratedUrl(url)
    } catch {
      setError('Could not generate share link. Please try again.')
      toast.error("Couldn't generate share link. Try again.", {
        duration: Infinity,
      })
    } finally {
      setGenerating(false)
    }
  }

  async function handleCopy() {
    if (!generatedUrl) return
    try {
      await navigator.clipboard.writeText(generatedUrl)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
      toast.success('Link copied to clipboard')
    } catch {
      // Clipboard access denied — surface to the user instead of swallowing.
      toast.error("Couldn't copy. Copy manually instead.")
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="text-base font-semibold text-slate-900">
            Share this scan
          </DialogTitle>
        </DialogHeader>

        {!generatedUrl && (
          <>
            <div className="space-y-3">
              <div>
                <label
                  htmlFor="share-expiry"
                  className="block text-sm text-slate-700 mb-1"
                >
                  Link expires in
                </label>
                <Select
                  value={expiryChoice}
                  onValueChange={(v) => setExpiryChoice(v as ExpiryChoice)}
                >
                  <SelectTrigger id="share-expiry" className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {EXPIRY_OPTIONS.map((opt) => (
                      <SelectItem key={opt.value} value={opt.value}>
                        {opt.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {expiryChoice === 'never' && (
                  <p className="text-xs text-amber-600 mt-1">
                    ⚠ Anyone with this link can view this scan forever, even
                    after team members leave.
                  </p>
                )}
              </div>

              <div>
                <label
                  htmlFor="share-password"
                  className="block text-sm text-slate-700 mb-1"
                >
                  Password (optional)
                </label>
                <input
                  id="share-password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Leave blank for no password"
                  className="w-full border border-slate-300 rounded-md px-2 py-1.5 text-sm"
                />
              </div>
            </div>

            {error && (
              <p className="text-xs text-red-600 mt-3" role="alert">
                {error}
              </p>
            )}

            <button
              type="button"
              onClick={handleGenerate}
              disabled={generating}
              className="mt-4 w-full bg-amber-400 text-slate-900 hover:bg-amber-300 disabled:opacity-60 rounded-md py-2 text-sm font-medium"
            >
              {generating ? 'Generating…' : 'Generate share link'}
            </button>
          </>
        )}

        {generatedUrl && (
          <div className="space-y-3">
            <p className="text-xs text-slate-500">
              Copy this link now — it will not be shown again.
            </p>
            <div className="flex items-center gap-2">
              <input
                readOnly
                value={generatedUrl}
                className="flex-1 border border-slate-300 rounded-md px-2 py-1.5 text-xs font-mono bg-slate-50"
                onFocus={(e) => e.currentTarget.select()}
              />
              <button
                type="button"
                aria-label="Copy share link to clipboard"
                onClick={handleCopy}
                className="border border-slate-300 rounded-md px-3 py-1.5 text-xs hover:bg-slate-50 flex items-center gap-1"
              >
                {copied ? (
                  <>
                    <Check size={12} />
                    Copied
                  </>
                ) : (
                  <>
                    <Copy size={12} />
                    Copy
                  </>
                )}
              </button>
            </div>
          </div>
        )}

        <div className="mt-6">
          <p className="text-xs font-semibold text-slate-700">
            Active share links
          </p>
          <div className="mt-2">
            <ShareLinksList
              scanId={scanId}
              refreshKey={generatedUrl ? 1 : 0}
            />
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
