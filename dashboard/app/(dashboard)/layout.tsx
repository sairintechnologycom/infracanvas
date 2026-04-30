'use client'
import { useState } from 'react'
import { ClerkProvider } from '@clerk/nextjs'
import { Sidebar } from '@/components/layout/Sidebar'
import { TopBar } from '@/components/layout/TopBar'
import { TopBarActionsProvider } from '@/components/layout/TopBarActions'

const DEV_BYPASS = process.env.NEXT_PUBLIC_DEV_BYPASS_AUTH === '1'

function Shell({ children }: { children: React.ReactNode }) {
  const [mobileOpen, setMobileOpen] = useState(false)
  return (
    <TopBarActionsProvider>
      <div className="flex h-screen bg-white overflow-hidden">
        <Sidebar mobileOpen={mobileOpen} />
        <div className="flex flex-col flex-1 min-w-0">
          <TopBar onMenuToggle={() => setMobileOpen((o) => !o)} />
          <main className="flex-1 overflow-auto">{children}</main>
        </div>
      </div>
    </TopBarActionsProvider>
  )
}

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  if (DEV_BYPASS) {
    return <Shell>{children}</Shell>
  }
  return (
    <ClerkProvider>
      <Shell>{children}</Shell>
    </ClerkProvider>
  )
}
