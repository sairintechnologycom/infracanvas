import { OrganizationProfile } from '@clerk/nextjs'

/**
 * /settings/members — Clerk OrganizationProfile restyled with the dashboard's
 * amber primary color. Clerk handles all team-member CRUD and role enforcement;
 * we only theme the surface.
 */
export default function MembersPage() {
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
