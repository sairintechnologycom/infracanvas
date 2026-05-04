'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { RepoCombobox } from '@/components/integrations/RepoCombobox'
import { BranchPicker } from '@/components/integrations/BranchPicker'
import type { RepoResp } from '@/lib/types'

export interface ScanTriggerFormProps {
  installationId: number
}

/**
 * Compose RepoCombobox + BranchPicker + path input + Scan button.
 *
 * On submit POSTs to /api/scans/from-github (Plan 07 proxy → Plan 05
 * backend), then router.push to /scans/{scan_id} where Plan 10's polling
 * page picks up the pending state.
 *
 * Status mapping (T-07.5-09-03):
 *   - 503 → friendly "rate-limited" copy (preserves the Retry-After:60
 *     hint surfaced by the proxy in Plan 07).
 *   - everything else → generic "Failed to start scan" so we never leak
 *     backend internals.
 */
export function ScanTriggerForm({ installationId }: ScanTriggerFormProps) {
  const router = useRouter()
  const [repo, setRepo] = useState<RepoResp | null>(null)
  const [branch, setBranch] = useState<string>('')
  const [path, setPath] = useState<string>('.')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const canSubmit = !!repo && !!branch && !submitting

  const friendlyError = (code: string | null): string | null => {
    if (!code) return null
    if (code === 'http_503') {
      return 'GitHub is rate-limiting us right now. Please retry in a minute.'
    }
    return 'Failed to start scan. Please retry.'
  }

  const handleSubmit = async () => {
    if (!canSubmit || !repo) return
    setSubmitting(true)
    setError(null)
    try {
      const res = await fetch('/api/scans/from-github', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          installation_id: installationId,
          repo: repo.full_name,
          branch,
          path: path || '.',
        }),
      })
      if (!res.ok) {
        throw new Error(`http_${res.status}`)
      }
      const data = (await res.json()) as { scan_id: string }
      router.push(`/scans/${data.scan_id}`)
    } catch (err) {
      const code = err instanceof Error ? err.message : null
      setError(code)
      setSubmitting(false)
    }
  }

  return (
    <div className="space-y-3 p-4 border border-slate-200 rounded-md">
      <div className="space-y-1">
        <Label htmlFor="repo-trigger">Repository</Label>
        <RepoCombobox
          installationId={installationId}
          value={repo}
          onSelect={(r) => {
            setRepo(r)
            setBranch('')
          }}
        />
      </div>
      <div className="space-y-1">
        <Label htmlFor="branch-trigger">Branch</Label>
        <BranchPicker
          installationId={installationId}
          selectedRepo={repo}
          value={branch}
          onChange={setBranch}
        />
      </div>
      <div className="space-y-1">
        <Label htmlFor="path-input">Path (subdirectory)</Label>
        <Input
          id="path-input"
          value={path}
          onChange={(e) => setPath(e.target.value)}
          placeholder="."
          aria-label="Subdirectory path"
        />
      </div>
      {error && (
        <div role="alert" className="text-sm text-red-600">
          {friendlyError(error)}
        </div>
      )}
      <Button onClick={handleSubmit} disabled={!canSubmit}>
        {submitting ? 'Starting…' : 'Scan'}
      </Button>
    </div>
  )
}
