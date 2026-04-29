'use client'
import { useState } from 'react'
import { GitCompare } from 'lucide-react'
import { ScanPickerModal } from './ScanPickerModal'

interface Props {
  scanId: string
  branch: string | null
}

/**
 * "Compare against…" button on the scan-detail header strip.
 *
 * Opens the ScanPickerModal — the modal handles loading the team's recent
 * scans, grouping by branch, and navigating to /scans/compare?a=&b= on
 * confirm. Wired into MetadataHeader (Plan 07-07) by Plan 07-08 D-09.
 */
export function CompareButton({ scanId, branch }: Props) {
  const [open, setOpen] = useState(false)

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="flex items-center gap-1.5 px-3 py-1.5 text-sm border border-slate-300 rounded-md text-slate-600 hover:bg-slate-100 whitespace-nowrap"
        aria-label="Compare this scan against another"
        data-testid="compare-button"
      >
        <GitCompare size={14} />
        Compare
      </button>
      <ScanPickerModal
        currentScanId={scanId}
        currentBranch={branch ?? undefined}
        isOpen={open}
        onClose={() => setOpen(false)}
      />
    </>
  )
}
