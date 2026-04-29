import type { ShareLandingResp } from '@/lib/types'
import { PasswordGate } from '@/components/share/PasswordGate'
import {
  ShareViewer,
  type ShareViewerScanMetadata,
} from '@/components/share/ShareViewer'

/**
 * Public share landing — no Clerk auth required (middleware passes /share/* through).
 *
 * Routes to:
 *   - PasswordGate when has_password=true (D-09 / D-15: zero metadata pre-auth)
 *   - ShareViewer  when has_password=false (renders the read-only embedded viewer)
 *
 * Backend status mapping:
 *   - 410 + detail "expired" → "This share link has expired" card
 *   - 410 + detail "revoked" → "This share link is no longer active" card
 *   - 404 → "Share link not found" card
 *   - other non-2xx → generic error card
 */
interface PageProps {
  params: Promise<{ token: string }>
}

interface ErrorBody {
  detail?: string
}

interface DeadEndProps {
  title: string
  body: string
}

function DeadEndCard({ title, body }: DeadEndProps) {
  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center">
      <div className="bg-white border border-slate-200 rounded-lg p-8 max-w-md text-center">
        <h1 className="text-base font-semibold text-slate-900">{title}</h1>
        <p className="text-sm text-slate-500 mt-2">{body}</p>
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
    </div>
  )
}

export default async function ShareTokenPage({ params }: PageProps) {
  const { token } = await params // Next.js 15: params is async

  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL ?? process.env.BACKEND_URL
  if (!backendUrl) {
    return (
      <DeadEndCard
        title="Share link unavailable"
        body="The share service is not configured. Please contact support."
      />
    )
  }

  const res = await fetch(`${backendUrl}/v1/share-links/${token}`, {
    cache: 'no-store',
  })

  if (res.status === 410) {
    let detail: string | undefined
    try {
      const errBody = (await res.json()) as ErrorBody
      detail = errBody.detail
    } catch {
      detail = undefined
    }
    if (detail === 'expired') {
      return (
        <DeadEndCard
          title="This share link has expired"
          body="Ask the person who shared this link to create a new one."
        />
      )
    }
    return (
      <DeadEndCard
        title="This share link is no longer active"
        body="The link has been revoked."
      />
    )
  }

  if (res.status === 404) {
    return (
      <DeadEndCard
        title="Share link not found"
        body="The link may have been mistyped, or it never existed."
      />
    )
  }

  if (!res.ok) {
    return (
      <DeadEndCard
        title="Could not load share link"
        body="Something went wrong on our end. Please try again later."
      />
    )
  }

  const data = (await res.json()) as ShareLandingResp

  if (data.has_password === true) {
    // D-09 / D-15: pass NO scan metadata to PasswordGate
    return <PasswordGate token={token} />
  }

  // has_password === false → present the viewer immediately.
  if (!data.presigned_get_url) {
    return (
      <DeadEndCard
        title="Could not load share link"
        body="The shared scan data is unavailable."
      />
    )
  }

  const metadata: ShareViewerScanMetadata = {
    created_at: data.created_at,
    commit_sha: data.commit_sha,
    branch: data.branch,
    summary_json: (data.summary_json ?? null) as ShareViewerScanMetadata['summary_json'],
  }

  return (
    <ShareViewer
      presignedUrl={data.presigned_get_url}
      metadata={metadata}
      teamName={null}
    />
  )
}
