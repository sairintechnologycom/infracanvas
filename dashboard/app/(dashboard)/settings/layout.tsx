'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'

const TAB_ROUTES = [
  { value: 'members', label: 'Members', href: '/settings/members' },
  { value: 'billing', label: 'Billing', href: '/settings/billing' },
  { value: 'integrations', label: 'Integrations', href: '/settings/integrations' },
] as const

export default function SettingsLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const pathname = usePathname() ?? ''
  const active =
    TAB_ROUTES.find(t => pathname.startsWith(t.href))?.value ?? 'members'

  return (
    <div className="max-w-7xl mx-auto px-8 py-8">
      <h1 className="text-base font-semibold text-slate-900 mb-6">Settings</h1>
      <Tabs value={active} className="w-full">
        <TabsList variant="line" aria-label="Settings sections">
          {TAB_ROUTES.map(t => (
            <TabsTrigger key={t.value} value={t.value} asChild>
              <Link href={t.href}>{t.label}</Link>
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>
      <div className="mt-6">{children}</div>
    </div>
  )
}
