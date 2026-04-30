import type { Metadata } from 'next'
import { Inter, JetBrains_Mono, Geist } from 'next/font/google'
import { Toaster } from '@/components/ui/sonner'
import './globals.css'
import { cn } from "@/lib/utils";

const geist = Geist({subsets:['latin'],variable:'--font-sans'})
const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-mono',
})

export const metadata: Metadata = {
  title: 'InfraCanvas',
  description: 'Cloud infrastructure visibility platform',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={cn(jetbrainsMono.variable, "font-sans", geist.variable)}>
      <body className="bg-white text-slate-900 antialiased font-sans">
        {children}
        <Toaster richColors position="bottom-right" />
      </body>
    </html>
  )
}
