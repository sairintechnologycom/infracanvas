import { auth } from '@clerk/nextjs/server'

/**
 * Fetch from the InfraCanvas backend with the Clerk Bearer token attached.
 * Always no-store — all dashboard data is per-user and must not be cached on Vercel.
 * Never log the Authorization header.
 */
export async function backendFetch<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
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
