'use client'
import { useEffect, useState } from 'react'
import { Copy, Check, X } from 'lucide-react'
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

  // Esc-to-close — keeps shipping without a full Radix Dialog.
  useEffect(() => {
    if (!isOpen) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [isOpen, onClose])

  if (!isOpen) return null

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
    } catch {
      // Clipboard access denied — fallback: select the input value.
      // No toast component shipped yet; copy state silently fails.
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40"
      role="dialog"
      aria-modal="true"
      aria-labelledby="share-modal-title"
      onClick={onClose}
    >
      <div
        className="bg-white border border-slate-200 rounded-lg shadow-lg w-full max-w-md p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h2
            id="share-modal-title"
            className="text-base font-semibold text-slate-900"
          >
            Share this scan
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close share dialog"
            className="text-slate-400 hover:text-slate-700"
          >
            <X size={16} />
          </button>
        </div>

        {!generatedUrl && (
          <>
            <div className="space-y-3">
              <div>
                <label
                  htmlFor="share-expiry"
                  className="block text-sm text-slate-700 mb-1"
                >
                  Expires in
                </label>
                <select
                  id="share-expiry"
                  value={expiryChoice}
                  onChange={(e) =>
                    setExpiryChoice(e.target.value as ExpiryChoice)
                  }
                  className="w-full border border-slate-300 rounded-md px-2 py-1.5 text-sm"
                >
                  {EXPIRY_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
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

        <p className="text-xs font-semibold text-slate-700 mt-6">
          Active share links
        </p>
        {/*
          TODO: GET /v1/scans/{id}/share-links not yet implemented in backend —
          ShareList deferred to a follow-on plan.
        */}
        <p className="text-xs text-slate-500 mt-1">
          No share links yet for this scan.
        </p>
      </div>
    </div>
  )
}
