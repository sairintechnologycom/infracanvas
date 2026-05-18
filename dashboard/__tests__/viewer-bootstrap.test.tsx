import { describe, it, expect, afterEach, vi } from 'vitest'
import { render } from '@testing-library/react'
import '@testing-library/jest-dom'

// Phase 12 FMV-02 — Blocker 1 closure verification.
//
// ViewerBootstrap must install the dashboard's backendFetch on
// window.__INFRACANVAS_BACKEND_FETCH__ at mount time so the bundled
// viewer's asymmetryFetcher can reach the backend under Clerk-JWT auth.
//
// `dashboard/lib/backend.ts` dynamically imports `@clerk/nextjs/server`,
// which is server-only. Stub the entire `@/lib/backend` module to a
// no-op identity-stable function so the test can verify the install
// without needing a real Next.js / Clerk runtime.
vi.mock('@/lib/backend', () => {
  const stubBackendFetch = vi.fn(async () => [])
  return { backendFetch: stubBackendFetch }
})

import { ViewerBootstrap } from '@/components/viewer/ViewerBootstrap'
import { backendFetch } from '@/lib/backend'

type WindowWithInjectable = Window & typeof globalThis & {
  __INFRACANVAS_BACKEND_FETCH__?: typeof backendFetch
}

describe('ViewerBootstrap (Blocker 1 — installs window.__INFRACANVAS_BACKEND_FETCH__)', () => {
  afterEach(() => {
    delete (window as WindowWithInjectable).__INFRACANVAS_BACKEND_FETCH__
  })

  it('installs backendFetch on window.__INFRACANVAS_BACKEND_FETCH__ after mount', () => {
    render(<ViewerBootstrap />)
    const installed = (window as WindowWithInjectable).__INFRACANVAS_BACKEND_FETCH__
    expect(typeof installed).toBe('function')
  })

  it('installed function is identity-equal to the backendFetch import', () => {
    render(<ViewerBootstrap />)
    const installed = (window as WindowWithInjectable).__INFRACANVAS_BACKEND_FETCH__
    expect(installed).toBe(backendFetch)
  })

  it('renders null (no visible DOM output)', () => {
    const { container } = render(<ViewerBootstrap />)
    expect(container.firstChild).toBeNull()
  })
})
