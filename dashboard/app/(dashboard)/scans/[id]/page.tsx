import { notFound } from 'next/navigation'
import { backendFetch } from '@/lib/backend'
import type { ScanGetResp } from '@/lib/types'
import { MetadataHeader } from '@/components/scans/MetadataHeader'
import { ScanViewerClient } from '@/components/scans/ScanViewerClient'
import { ScanDetailActions } from './ScanDetailActions'

interface PageProps {
  params: Promise<{ id: string }>
}

export default async function ScanDetailPage({ params }: PageProps) {
  const { id } = await params // MUST await — Next.js 15 breaking change

  let scan: ScanGetResp
  try {
    scan = await backendFetch<ScanGetResp>(`/v1/scans/${id}`)
  } catch (err) {
    const status = err instanceof Error ? err.message : ''
    if (status === '404') notFound()
    // Re-throw non-404 errors so Next.js error boundary handles them
    throw err
  }

  return (
    // Outer div fills remaining viewport after sidebar+topbar; no overflow on this container
    <div className="flex flex-col h-full">
      {/* Mounts on the client; injects [Compare] [Share] into the top-bar slot (RMD-05) */}
      <ScanDetailActions scanId={scan.id} branch={scan.branch} />
      <MetadataHeader scan={scan} />
      {/* ScanViewerClient fills remaining height; viewer manages its own pan/zoom */}
      <div className="flex-1 min-h-0">
        <ScanViewerClient scanId={id} initialPresignedUrl={scan.presigned_get_url} />
      </div>
    </div>
  )
}
