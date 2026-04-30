'use client'
import { MessageSquare, Github } from 'lucide-react'

/**
 * /settings/integrations — v1 stubs for Slack + GitHub integrations.
 *
 * Slack: input + Save button — URL is not persisted yet (Phase 8 backend).
 * GitHub: disabled "Connect GitHub (coming in 7.5)" button per UI-SPEC copy.
 */
export default function IntegrationsPage() {
  return (
    <div className="flex flex-col gap-3 max-w-2xl">
      {/* Slack card */}
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

      {/* GitHub card */}
      <div className="bg-white border border-slate-200 rounded-lg p-4">
        <div className="flex items-center gap-2">
          <Github />
          <h2 className="text-sm font-semibold text-slate-900">GitHub</h2>
        </div>
        <p className="text-xs text-slate-500 mt-1">
          Connect a repo and scan on push (coming in 7.5).
        </p>
        <button
          type="button"
          disabled
          data-testid="github-connect-btn"
          aria-disabled="true"
          className="mt-3 inline-flex items-center border border-slate-300 text-slate-500 text-sm font-medium px-3 py-2 rounded-md opacity-50 cursor-not-allowed"
        >
          Connect GitHub (coming in 7.5)
        </button>
      </div>
    </div>
  )
}
