'use client'
import { useEffect, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import { MessageSquare, Github } from 'lucide-react'

import { InstallButton } from '@/components/integrations/InstallButton'
import { ScanTriggerForm } from '@/components/integrations/ScanTriggerForm'
import type { InstallationResp } from '@/lib/types'

/**
 * /settings/integrations — live state machine (D-04, replaces Phase 7 D-03
 * placeholder).
 *
 * Pre-install: empty installations → <InstallButton/> + helper copy.
 * Post-install: list installations + per-row <ScanTriggerForm/> composed
 * from RepoCombobox + BranchPicker + path input + Scan button (Plan 08).
 *
 * Post-install hydration poll: when the user lands back here with
 * ?install=success and the GET hasn't yet seen the new install row (GitHub
 * redirect races our backend's upsert), poll every 3s for up to 5 attempts
 * (~15s) until the list is non-empty (T-07.5-09-01 caps the loop so a hung
 * backend can't pin the page).
 *
 * Slack stub block preserved verbatim (Phase 8 wires it up).
 */

const POLL_INTERVAL_MS = 3000
const POLL_MAX_ATTEMPTS = 5

const fetchInstallations = async (): Promise<InstallationResp[]> => {
  const res = await fetch('/api/github/installations')
  if (!res.ok) throw new Error(`http_${res.status}`)
  return (await res.json()) as InstallationResp[]
}

export default function IntegrationsPage() {
  const searchParams = useSearchParams()
  const installSuccess = searchParams?.get('install') === 'success'

  const [installations, setInstallations] = useState<InstallationResp[] | null>(
    null,
  )
  const [error, setError] = useState<string | null>(null)

  // Initial fetch on mount.
  useEffect(() => {
    let cancelled = false
    fetchInstallations()
      .then((data) => {
        if (cancelled) return
        setInstallations(data)
      })
      .catch((err) => {
        if (cancelled) return
        setError(err instanceof Error ? err.message : 'failed_to_load')
        setInstallations([])
      })
    return () => {
      cancelled = true
    }
  }, [])

  // Post-install hydration poll: while install=success AND list still empty,
  // refetch every 3s up to POLL_MAX_ATTEMPTS times.
  useEffect(() => {
    if (!installSuccess) return
    if (installations === null) return // still loading initial fetch
    if (installations.length > 0) return

    let cancelled = false
    let attempts = 0
    const id = setInterval(() => {
      if (cancelled) return
      attempts += 1
      if (attempts > POLL_MAX_ATTEMPTS) {
        clearInterval(id)
        return
      }
      fetchInstallations()
        .then((data) => {
          if (cancelled) return
          setInstallations(data)
          if (data.length > 0) {
            clearInterval(id)
          }
        })
        .catch(() => {
          // Swallow — next tick retries; the cap prevents infinite spin.
        })
    }, POLL_INTERVAL_MS)

    return () => {
      cancelled = true
      clearInterval(id)
    }
  }, [installSuccess, installations])

  return (
    <div className="flex flex-col gap-3 max-w-2xl">
      {/* Slack card — preserved Phase 7 stub (Phase 8 wires it up). */}
      <div className="bg-white border border-slate-200 rounded-lg p-4">
        <div className="flex items-center gap-2">
          <MessageSquare />
          <h2 className="text-sm font-semibold text-slate-900">Slack</h2>
        </div>
        <p className="text-xs text-slate-500 mt-1">
          Send Critical findings to a Slack channel (Phase 8).
        </p>
        <form
          className="flex items-center gap-2 mt-3"
          action="#"
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          onSubmit={(e: any) => {
            e.preventDefault()
            // TODO Phase 8: POST /v1/integrations/slack { webhook_url }
          }}
        >
          <input
            type="url"
            name="slack_webhook"
            placeholder="https://hooks.slack.com/..."
            className="flex-1 border border-slate-200 rounded-md px-3 py-2 text-sm placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-slate-400"
          />
          <button
            type="submit"
            className="border border-slate-300 hover:bg-slate-50 text-slate-900 text-sm font-medium px-3 py-2 rounded-md transition-colors"
          >
            Save webhook URL
          </button>
        </form>
      </div>

      {/* GitHub card — live (Plan 09). */}
      <div className="bg-white border border-slate-200 rounded-lg p-4">
        <div className="flex items-center gap-2">
          <Github />
          <h2 className="text-sm font-semibold text-slate-900">GitHub</h2>
        </div>

        {/* Loading state */}
        {installations === null && (
          <div
            data-testid="github-loading"
            className="mt-3 text-sm text-slate-500"
          >
            Loading installations…
          </div>
        )}

        {/* Pre-install: empty list */}
        {installations !== null && installations.length === 0 && (
          <div className="mt-3 space-y-2">
            <p className="text-xs text-slate-500">
              Connect a repo to scan it on demand.
            </p>
            <InstallButton />
            {installSuccess && (
              <p className="text-xs text-slate-400">
                Waiting for GitHub to confirm the install…
              </p>
            )}
          </div>
        )}

        {/* Post-install: per-installation rows */}
        {installations !== null && installations.length > 0 && (
          <ul className="mt-3 space-y-3">
            {installations.map((row) => (
              <li
                key={row.installation_id}
                className="space-y-2 border-t border-slate-100 pt-3 first:border-t-0 first:pt-0"
              >
                <div className="flex items-center justify-between text-sm">
                  <div className="text-slate-900 font-medium">
                    {row.github_account_login}
                    <span className="ml-2 text-xs font-normal text-slate-500">
                      installed{' '}
                      {new Date(row.installed_at).toLocaleDateString()}
                    </span>
                  </div>
                  <a
                    href={`https://github.com/settings/installations/${row.installation_id}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-slate-600 hover:text-slate-900 underline"
                  >
                    Manage on GitHub
                  </a>
                </div>
                <ScanTriggerForm installationId={row.installation_id} />
              </li>
            ))}
          </ul>
        )}

        {error && (
          <p className="mt-3 text-xs text-red-600" role="alert">
            Could not load installations. Please refresh.
          </p>
        )}
      </div>
    </div>
  )
}
