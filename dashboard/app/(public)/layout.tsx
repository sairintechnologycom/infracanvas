import { ClerkProvider } from '@clerk/nextjs'

export default function PublicLayout({ children }: { children: React.ReactNode }) {
  return (
    <ClerkProvider>
      {children}
    </ClerkProvider>
  )
}
