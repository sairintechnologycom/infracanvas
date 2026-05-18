'use client'

import { useEffect } from 'react'
import { backendFetch } from '@/lib/backend'

/**
 * Phase 12 FMV-02 — Blocker 1 closure.
 *
 * The bundled viewer ships as a standalone HTML asset and cannot import
 * `@clerk/nextjs/server` directly (Clerk's server SDK is Node-only). The
 * dashboard owns the Clerk JWT boundary, so it exposes its `backendFetch`
 * helper to the viewer at runtime by installing it on
 * `window.__INFRACANVAS_BACKEND_FETCH__`.
 *
 * The viewer's `lib/asymmetryFetcher.ts:getInjectableFetch()` reads that
 * slot and uses the installed callable when present; when absent (offline
 * / standalone bundle) it returns [] cleanly. With this bootstrap mounted
 * inside ScanViewerClient, `fetchAsymmetries(siteId)` reaches
 * `/v1/sites/{siteId}/asymmetries` and `selectedPath.asymmetry` populates
 * — FMV-02 observable end-to-end.
 *
 * This component is render-null — it only runs the install effect on mount.
 * Mount it as a sibling of the existing `<ViewerApp />` so the install
 * happens before the viewer's FlowMapCanvas useEffect dispatches its first
 * fetchAsymmetries call.
 *
 * T-12-07-07 (no Authorization-header logging) is upheld at the
 * dashboard/lib/backend.ts boundary; this component only forwards the
 * function reference and never inspects request headers.
 */
type BackendFetch = typeof backendFetch

export function ViewerBootstrap(): null {
  useEffect(() => {
    if (typeof window === 'undefined') return
    ;(window as Window &
      typeof globalThis & {
        __INFRACANVAS_BACKEND_FETCH__?: BackendFetch
      }).__INFRACANVAS_BACKEND_FETCH__ = backendFetch
  }, [])
  return null
}

export default ViewerBootstrap
