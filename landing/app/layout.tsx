import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import Nav from '../components/Nav'
import Footer from '../components/Footer'
import './globals.css'

const inter = Inter({
  subsets: ['latin'],
  display: 'swap',
})

export const metadata: Metadata = {
  title: 'InfraCanvas — Your infrastructure, visualised',
  description:
    'One command gives you a complete, annotated picture of your hybrid infrastructure — security blind spots, cost, and drift — across AWS, Azure, and physical data centres.',
  openGraph: {
    title: 'InfraCanvas — One command. Your entire infrastructure.',
    description:
      'One command gives you a complete, annotated picture of your hybrid infrastructure — security blind spots, cost, and drift — across AWS, Azure, and physical data centres.',
    images: ['/og-image.png'],
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className={`dark ${inter.className}`}>
      <body className="bg-slate-950 text-slate-50 antialiased">
        <header>
          <Nav />
        </header>
        <main>{children}</main>
        <footer>
          <Footer />
        </footer>
      </body>
    </html>
  )
}
