'use client'

import { useEffect, useState } from 'react'

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type { BranchResp, RepoResp } from '@/lib/types'

export interface BranchPickerProps {
  installationId: number
  selectedRepo: RepoResp | null
  value: string
  onChange: (branch: string) => void
}

/**
 * Lazy-loading branch dropdown built on the shadcn Select primitive.
 *
 * - Fetches /api/github/branches only when a repo is selected (D-05 lazy
 *   load — branches are unbounded, sometimes >100 per repo).
 * - Defaults selection to repo.default_branch on first load when no value
 *   was passed by the parent (D-05 default-to-default-branch).
 * - Refetches when selectedRepo.full_name or installationId changes.
 * - Cancelled-flag cleanup (CC-14) so an in-flight fetch can't update
 *   state on an unmounted component or after the parent has switched repos.
 * - Surfaces 503 (Plan 07 proxy preserves Retry-After:60) inline so the
 *   user understands a rate-limit gap rather than thinking the dropdown
 *   is broken.
 * - Returns null when no repo selected — composition responsibility lives
 *   with the parent surface (Plan 09's ScanTriggerForm).
 */
export function BranchPicker({
  installationId,
  selectedRepo,
  value,
  onChange,
}: BranchPickerProps) {
  const [branches, setBranches] = useState<BranchResp[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!selectedRepo) {
      setBranches([])
      return
    }
    let cancelled = false
    setLoading(true)
    setError(null)
    const url = `/api/github/branches?installation_id=${installationId}&repo=${encodeURIComponent(
      selectedRepo.full_name,
    )}`
    fetch(url)
      .then(async (res) => {
        if (!res.ok) {
          if (res.status === 503) {
            throw new Error('Rate limited by GitHub — try again in 60s')
          }
          throw new Error(`Failed to load branches (${res.status})`)
        }
        return (await res.json()) as BranchResp[]
      })
      .then((data) => {
        if (cancelled) return
        setBranches(data)
        setLoading(false)
        // Default to repo.default_branch on first load if no value is set.
        if (!value && selectedRepo.default_branch) {
          onChange(selectedRepo.default_branch)
        }
      })
      .catch((err) => {
        if (cancelled) return
        setError(
          err instanceof Error ? err.message : 'Failed to load branches',
        )
        setLoading(false)
      })
    return () => {
      cancelled = true
    }
    // value/onChange intentionally omitted — only refetch on repo/installation
    // changes; default-branch fallback runs once per fetch resolution.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [installationId, selectedRepo?.full_name])

  if (!selectedRepo) return null

  return (
    <Select value={value} onValueChange={onChange} disabled={loading}>
      <SelectTrigger className="w-full">
        <SelectValue placeholder={loading ? 'Loading…' : 'Pick a branch'} />
      </SelectTrigger>
      <SelectContent>
        {error && (
          <div className="p-2 text-sm text-red-600" role="alert">
            {error}
          </div>
        )}
        {branches.map((b) => (
          <SelectItem key={b.name} value={b.name}>
            {b.name}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
