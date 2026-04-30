'use client'
import { createContext, useContext, useState, useCallback, type ReactNode } from 'react'

/**
 * Page-level top-bar action slot pattern (RMD-05).
 *
 * The (dashboard) layout wraps its shell in <TopBarActionsProvider/>; the TopBar
 * renders <TopBarActionsSlot/> on the right side. Detail pages mount a thin
 * client component (e.g. <ScanDetailActions/>) that calls
 * useTopBarActions().set(...) on mount and clear() on unmount to inject route-
 * specific buttons (Compare, Share) into the top bar.
 *
 * Per UI-REVIEW Pillar 2 BLOCKER #3 — actions live ONLY in the top bar; the
 * MetadataHeader keeps its 52px metadata strip but no longer renders Compare
 * and Share buttons.
 */

type ActionsContextShape = {
  actions: ReactNode
  set: (jsx: ReactNode) => void
  clear: () => void
}

const ActionsContext = createContext<ActionsContextShape | null>(null)

export function TopBarActionsProvider({ children }: { children: ReactNode }) {
  const [actions, setActions] = useState<ReactNode>(null)
  const set = useCallback((jsx: ReactNode) => setActions(jsx), [])
  const clear = useCallback(() => setActions(null), [])
  return (
    <ActionsContext.Provider value={{ actions, set, clear }}>
      {children}
    </ActionsContext.Provider>
  )
}

export function useTopBarActions() {
  const ctx = useContext(ActionsContext)
  if (!ctx) {
    throw new Error('useTopBarActions must be used inside <TopBarActionsProvider/>')
  }
  return ctx
}

export function TopBarActionsSlot() {
  const ctx = useContext(ActionsContext)
  return <>{ctx?.actions ?? null}</>
}
