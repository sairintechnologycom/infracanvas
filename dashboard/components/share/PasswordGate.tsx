'use client'
import { useState } from 'react'
import {
  ShareViewer,
  type ShareViewerScanMetadata,
} from '@/components/share/ShareViewer'
import type { ShareVerifyResp } from '@/lib/types'

interface Props {
  token: string
}

// PasswordGate — gates a password-protected share link (D-09 / D-15).
//
// Receives ONLY `token`. The component renders ZERO pre-unlock metadata
// (no scan info of any kind). Backend confirms this contract by omitting
// those fields from GET /v1/share-links/{token} when has_password=true.
//
// Calls POST /v1/share-links/{token}/unlock on submit:
//   200 → mount ShareViewer with the returned presigned URL
//   401 → 'Incorrect password.'
//   410 → 'This share link is no longer active.'
//   429 → 'Too many attempts. Retry in N minutes.' (reads Retry-After header)
//   other → generic error
export function PasswordGate({ token }: Props) {
  const [password, setPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [retryIn, setRetryIn] = useState<number | null>(null)
  const [unlockedData, setUnlockedData] = useState<ShareVerifyResp | null>(null)

  if (unlockedData) {
    // Once unlocked, hand the verified payload to ShareViewer verbatim —
    // ShareViewer renders the metadata; this component only forwards it.
    return (
      <ShareViewer
        presignedUrl={unlockedData.presigned_get_url}
        metadata={unlockedData as ShareViewerScanMetadata}
        teamName={null}
      />
    )
  }

  async function handleSubmit() {
    if (!password || submitting || retryIn !== null) return
    setSubmitting(true)
    setError(null)
    try {
      const backendUrl =
        process.env.NEXT_PUBLIC_BACKEND_URL ?? ''
      const res = await fetch(
        `${backendUrl}/v1/share-links/${token}/unlock`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ password }),
        },
      )
      if (res.status === 200) {
        const data = (await res.json()) as ShareVerifyResp
        setUnlockedData(data)
      } else if (res.status === 401) {
        setError('Incorrect password.')
      } else if (res.status === 429) {
        const retryAfterSec = Number.parseInt(
          res.headers.get('Retry-After') ?? '60',
          10,
        )
        const minutes = Math.max(1, Math.ceil(retryAfterSec / 60))
        setError(
          `Too many attempts. Retry in ${minutes} minute${minutes !== 1 ? 's' : ''}.`,
        )
        setRetryIn(retryAfterSec)
      } else if (res.status === 410) {
        setError('This share link is no longer active.')
      } else {
        setError('Something went wrong. Please try again.')
      }
    } catch {
      setError('Something went wrong. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter') {
      e.preventDefault()
      void handleSubmit()
    }
  }

  return (
    <div
      data-testid="password-gate"
      className="min-h-screen bg-slate-50 flex flex-col items-center justify-center"
    >
      <div className="bg-white border border-slate-200 rounded-lg p-8 max-w-md w-full mt-32">
        <h1 className="text-base font-semibold text-slate-900">
          This scan is password-protected
        </h1>
        <div className="mt-4 space-y-3">
          <label
            className="block text-sm text-slate-700"
            htmlFor="share-password"
          >
            Password
          </label>
          <input
            id="share-password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            onKeyDown={onKeyDown}
            disabled={submitting || retryIn !== null}
            className="w-full border border-slate-300 rounded-md px-2 py-1.5 text-sm disabled:bg-slate-100 disabled:text-slate-500"
          />
          {error && (
            <p className="text-xs text-red-600" role="alert">
              {error}
            </p>
          )}
        </div>
        <button
          type="button"
          className="mt-4 w-full bg-amber-400 text-slate-900 hover:bg-amber-300 disabled:opacity-60 rounded-md py-2 text-sm font-medium"
          onClick={() => void handleSubmit()}
          disabled={submitting || !password || retryIn !== null}
        >
          {submitting ? 'Verifying…' : 'Unlock'}
        </button>
      </div>
      <p className="mt-6 text-xs text-slate-500">
        Made with{' '}
        <a
          href="https://infracanvas.dev"
          target="_blank"
          rel="noopener"
          className="hover:text-slate-900 hover:underline underline-offset-2"
        >
          InfraCanvas
        </a>
      </p>
    </div>
  )
}
