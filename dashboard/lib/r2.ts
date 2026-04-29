import type { ResourceGraph } from '@infracanvas/viewer'

export interface FetchScanJsonOptions {
  presignedUrl: string
  /**
   * Called once when the first fetch returns 403 (expired TTL per D-12).
   * Should return a fresh presigned URL. If it throws, the error propagates.
   */
  onPresignedExpired: () => Promise<string>
}

/**
 * fetchScanJson — fetch scan JSON from an R2 presigned URL with one-shot retry.
 *
 * On 403 (TTL expired), calls onPresignedExpired() to get a fresh URL and retries
 * exactly once.
 *
 * D-08: scan JSON is always fetched client-direct from R2 (never proxied).
 * D-12: presigned URL TTL is <=300s — 403 is expected in slow networks/tabs.
 *
 * The retry executes AT MOST ONCE — on a second 403, the error is surfaced.
 * This bounds blast radius for T-07-07-05 (no infinite retry loop).
 */
export async function fetchScanJson(opts: FetchScanJsonOptions): Promise<ResourceGraph> {
  const attempt = async (url: string): Promise<Response> => {
    const res = await fetch(url)
    return res
  }

  let res = await attempt(opts.presignedUrl)

  if (res.status === 403) {
    // Presigned URL expired — get a fresh one and retry once
    const freshUrl = await opts.onPresignedExpired()
    res = await attempt(freshUrl)
  }

  if (!res.ok) {
    throw new Error(`R2 fetch failed: ${res.status}`)
  }

  return res.json() as Promise<ResourceGraph>
}
