/**
 * UUID v1-v5 regex matcher (RFC 4122).
 *
 * Used by `app/(dashboard)/scans/compare/page.tsx` to validate the `a` and
 * `b` searchParams BEFORE making any backend call (T-07-08-01 mitigation —
 * never let a user-controlled string flow into a backend URL unvalidated).
 */
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

export function isUUID(s: string | undefined): s is string {
  return !!s && UUID_RE.test(s)
}
