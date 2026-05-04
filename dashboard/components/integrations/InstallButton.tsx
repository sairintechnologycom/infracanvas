'use client'

import { useOrganization } from '@clerk/nextjs'
import { Button } from '@/components/ui/button'

/**
 * GitHub App install entry point.
 *
 * Opens the InfraCanvas GitHub App install URL in a new tab, passing the
 * Clerk org id as `state` so the backend install-callback (Plan 04) can
 * resolve the team via `resolve_team_from_clerk_org` and validate
 * `state == team.clerk_org_id` (CSRF mitigation, divergence from D-14 —
 * the dashboard never knows team_id client-side).
 *
 * Returns null when no Clerk org is active (signed-out, or personal
 * account without an org); the parent surface (settings/integrations
 * page in Plan 09) is expected to render its own "Pick an org" prompt.
 */
const APP_SLUG = process.env.NEXT_PUBLIC_GITHUB_APP_SLUG ?? 'infracanvas-dev'

export function InstallButton() {
  const { organization } = useOrganization()
  if (!organization) return null

  const installUrl = `https://github.com/apps/${APP_SLUG}/installations/new?state=${organization.id}`

  return (
    <Button
      onClick={() => window.open(installUrl, '_blank', 'noopener,noreferrer')}
      variant="default"
    >
      Install InfraCanvas GitHub App
    </Button>
  )
}
