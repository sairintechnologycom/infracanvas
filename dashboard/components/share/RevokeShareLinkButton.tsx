'use client'

/**
 * Stub: replaced by Plan 07.1-06 Task 2 with full AlertDialog destructive
 * confirm flow. This minimal version exists so ShareLinksList builds during
 * Task 1's TDD cycle.
 */
type Props = { scanId: string; shareId: string; onRevoked: () => void }

// eslint-disable-next-line @typescript-eslint/no-unused-vars
export function RevokeShareLinkButton(_: Props) {
  return (
    <button type="button" className="text-sm text-red-600 hover:underline">
      Revoke
    </button>
  )
}
