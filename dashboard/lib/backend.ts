import { devStub } from './dev-stubs'

const DEV_BYPASS = process.env.DEV_BYPASS_AUTH === '1'

/**
 * Fetch from the InfraCanvas backend with the Clerk Bearer token attached.
 * Always no-store — all dashboard data is per-user and must not be cached on Vercel.
 * Never log the Authorization header.
 *
 * Note: `@clerk/nextjs/server` is server-only. We import it dynamically so this
 * module remains client-import-safe (e.g. when called from `'use client'`
 * components like ScanPickerModal that hit the dashboard's own /api routes).
 *
 * When DEV_BYPASS_AUTH=1, returns synthesized stub data for offline UI verification.
 */
export async function backendFetch<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  if (DEV_BYPASS) {
    return devStub<T>(path, init)
  }
  const { auth } = await import('@clerk/nextjs/server')
  const { getToken } = await auth()
  const token = await getToken()
  const backendUrl = process.env.BACKEND_URL
  if (!backendUrl) {
    throw new Error('BACKEND_URL environment variable is not set')
  }
  const res = await fetch(`${backendUrl}${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
      ...init?.headers,
    },
    cache: 'no-store',
  })
  if (!res.ok) {
    throw new Error(`${res.status}`)
  }
  return res.json() as Promise<T>
}
