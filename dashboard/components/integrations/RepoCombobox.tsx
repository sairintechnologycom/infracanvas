'use client'

import { useEffect, useRef, useState } from 'react'
import { Lock } from 'lucide-react'

import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import {
  Command,
  CommandEmpty,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command'
import { Button } from '@/components/ui/button'
import type { RepoResp } from '@/lib/types'

export interface RepoComboboxProps {
  installationId: number
  value?: RepoResp | null
  onSelect: (repo: RepoResp) => void
}

const DEBOUNCE_MS = 250

/**
 * Searchable repo picker built on the shadcn Popover + Command recipe.
 *
 * - Server-side search: backend (Plan 07 proxy → Plan 04 backend handler)
 *   already filters by `q`, so `shouldFilter={false}` on Command is critical
 *   — otherwise cmdk would re-filter the already-filtered list and hide
 *   results that match the server's heuristics but not cmdk's substring.
 * - Debounced 250ms (CC-15 useRef+setTimeout pattern, D-05) so typeahead
 *   doesn't chew the GitHub rate-limit budget.
 * - Cancelled-flag cleanup (CC-14) so an in-flight fetch can't update
 *   state on an unmounted component.
 * - On 503 (GitHub rate-limited; preserved by the Plan 07 proxy with
 *   Retry-After: 60), the inline error renders the "Rate limited — try
 *   again in 60s" hint so the user understands the gap rather than
 *   thinking the picker is broken.
 */
export function RepoCombobox({
  installationId,
  value,
  onSelect,
}: RepoComboboxProps) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [repos, setRepos] = useState<RepoResp[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Debounced fetch on installationId or query change.
  useEffect(() => {
    let cancelled = false

    const fire = () => {
      if (cancelled) return
      setLoading(true)
      setError(null)
      const url = `/api/github/repos?installation_id=${installationId}${
        query ? `&q=${encodeURIComponent(query)}` : ''
      }`
      fetch(url)
        .then(async (res) => {
          if (!res.ok) {
            if (res.status === 503) {
              throw new Error('Rate limited by GitHub — try again in 60s')
            }
            throw new Error(`Failed to load repos (${res.status})`)
          }
          return (await res.json()) as RepoResp[]
        })
        .then((data) => {
          if (cancelled) return
          setRepos(data)
          setLoading(false)
        })
        .catch((err) => {
          if (cancelled) return
          setError(err instanceof Error ? err.message : 'Failed to load repos')
          setLoading(false)
        })
    }

    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(fire, DEBOUNCE_MS)

    return () => {
      cancelled = true
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [installationId, query])

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="outline" className="w-full justify-between">
          {value ? value.full_name : 'Pick a repo…'}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-full p-0">
        <Command shouldFilter={false}>
          <CommandInput
            placeholder="Search repos..."
            value={query}
            onValueChange={setQuery}
          />
          <CommandList>
            {loading && (
              <div className="p-2 text-sm text-slate-500">Loading…</div>
            )}
            {error && (
              <div className="p-2 text-sm text-red-600" role="alert">
                {error}
              </div>
            )}
            {!loading && !error && repos.length === 0 && (
              <CommandEmpty>No repos found.</CommandEmpty>
            )}
            {repos.map((repo) => (
              <CommandItem
                key={repo.full_name}
                value={repo.full_name}
                onSelect={() => {
                  onSelect(repo)
                  setOpen(false)
                }}
              >
                <span>{repo.full_name}</span>
                {repo.private && (
                  <Lock
                    aria-label="private"
                    className="ml-auto size-3 text-slate-500"
                  />
                )}
              </CommandItem>
            ))}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  )
}
