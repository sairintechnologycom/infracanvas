'use client'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '@/components/ui/sheet'

interface Props {
  resourceId: string | null
  scanBId: string
  onClose: () => void
}

/**
 * Right-side drawer scoped to a single resource. Driven by parent's
 * `drillResourceId` state — when non-null the Sheet is `open`. Closing the
 * Sheet (overlay click, Esc, X button) calls `onClose()` so the parent can
 * reset the state.
 *
 * The drawer body currently renders a placeholder where the scoped viewer
 * canvas will land in a follow-up plan. This phase ships the open/close UX
 * (the contract RMD-02 measures); plumbing the per-resource scan slice into a
 * <DiagramCanvas/> needs an imperative `focusNode(id)` hook on the viewer
 * package that does not exist yet (see threat model T-07.1-12 — disposition
 * accept/deferred).
 */
export function DrillDownSheet({ resourceId, scanBId, onClose }: Props) {
  const open = resourceId !== null

  return (
    <Sheet
      open={open}
      onOpenChange={(o) => {
        if (!o) onClose()
      }}
    >
      <SheetContent
        side="right"
        className="w-[40vw] sm:max-w-none p-0 flex flex-col"
      >
        <SheetHeader>
          <SheetTitle className="font-mono text-sm break-all">
            {resourceId ?? ''}
          </SheetTitle>
          <SheetDescription className="font-mono text-xs text-slate-500">
            Scan {scanBId.slice(0, 8)}
          </SheetDescription>
        </SheetHeader>
        <div
          className="flex-1 min-h-0 border-t border-slate-200"
          data-testid="viewer-canvas"
        >
          <div className="flex items-center justify-center h-full text-xs text-slate-400">
            Viewer drill-down — coming in a follow-up plan.
          </div>
        </div>
      </SheetContent>
    </Sheet>
  )
}
