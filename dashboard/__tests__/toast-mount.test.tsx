import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

const ROOT_LAYOUT = readFileSync(join(__dirname, '..', 'app', 'layout.tsx'), 'utf8')
const DASHBOARD_LAYOUT = readFileSync(
  join(__dirname, '..', 'app', '(dashboard)', 'layout.tsx'),
  'utf8',
)

describe('Toaster root mount (RMD-03)', () => {
  it('imports Toaster from @/components/ui/sonner in app/layout.tsx', () => {
    expect(ROOT_LAYOUT).toMatch(
      /import\s*\{\s*Toaster\s*\}\s*from\s*['"]@\/components\/ui\/sonner['"]/,
    )
  })

  it('renders <Toaster/> in app/layout.tsx', () => {
    expect(ROOT_LAYOUT).toMatch(/<Toaster\b/)
  })

  it('Toaster is positioned bottom-right (UI-SPEC §Interaction)', () => {
    expect(ROOT_LAYOUT).toMatch(/position=["']bottom-right["']/)
  })

  it('Toaster is NOT mounted inside (dashboard)/layout.tsx (Pitfall 3 — must be at root for /share/[token])', () => {
    expect(DASHBOARD_LAYOUT).not.toMatch(/<Toaster\b/)
  })
})
