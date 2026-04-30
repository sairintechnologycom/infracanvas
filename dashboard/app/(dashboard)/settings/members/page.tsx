import { OrganizationProfile } from '@clerk/nextjs'

const DEV_BYPASS = process.env.DEV_BYPASS_AUTH === '1'

/**
 * /settings/members — Clerk OrganizationProfile restyled with the dashboard's
 * amber primary color. Clerk handles all team-member CRUD and role enforcement;
 * we only theme the surface.
 */
export default function MembersPage() {
  if (DEV_BYPASS) {
    return (
      <div className="bg-white border border-slate-200 rounded-lg p-12 text-center">
        <p className="text-sm font-semibold text-slate-900 mb-1">Members (Clerk)</p>
        <p className="text-xs text-slate-500 max-w-md mx-auto">
          Clerk's OrganizationProfile widget renders here in production. It's
          stubbed in dev-bypass mode because it requires a real Clerk session.
        </p>
      </div>
    )
  }
  return (
    <div className="bg-white border border-slate-200 rounded-lg p-2">
      <OrganizationProfile
        appearance={{
          variables: {
            colorPrimary: '#f59e0b',
          },
        }}
      />
    </div>
  )
}
