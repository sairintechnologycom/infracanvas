'use client'
import { useState } from 'react'
import { ClerkProvider } from '@clerk/nextjs'
import { Sidebar } from '@/components/layout/Sidebar'
import { TopBar } from '@/components/layout/TopBar'

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const [mobileOpen, setMobileOpen] = useState(false)
  return (
    <ClerkProvider>
      <div className="flex h-screen bg-white overflow-hidden">
        <Sidebar mobileOpen={mobileOpen} />
        <div className="flex flex-col flex-1 min-w-0">
          <TopBar onMenuToggle={() => setMobileOpen((o) => !o)} />
          <main className="flex-1 overflow-auto">
            {children}
          </main>
        </div>
      </div>
    </ClerkProvider>
  )
}
