import { describe, it, expect } from 'vitest'
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join } from 'node:path'

const ROOT = join(__dirname, '..')
const ROOTS = ['app', 'components']

/**
 * Polish-drift gates (RMD-06) — codifies UI-REVIEW Pillars 3 (Color), 4
 * (Typography), 5 (Spacing) so the drift cannot regress without a CI failure.
 *
 * Exemptions (mirrored in polish-drift-grep.sh):
 *   - components/ui/ — vendored shadcn primitives, exempt by UI-SPEC
 *   - components/compare/ — uses the drift palette (changed = amber) per
 *     UI-SPEC §Color "Drift palette"; this is an in-spec semantic use of
 *     amber-50/amber-500, NOT polish drift.
 */

function isExempt(p: string): boolean {
  // Use forward-slash comparison; tests run on macOS/Linux CI.
  return (
    p.includes('/components/ui/') ||
    p.includes('/components/compare/')
  )
}

function* walk(dir: string): Generator<string> {
  for (const ent of readdirSync(dir)) {
    const p = join(dir, ent)
    if (statSync(p).isDirectory()) {
      if (isExempt(p + '/')) continue
      yield* walk(p)
    } else if (/\.(tsx?|jsx?)$/.test(ent)) {
      if (isExempt(p)) continue
      yield p
    }
  }
}

function allSources(): { path: string; src: string }[] {
  const out: { path: string; src: string }[] = []
  for (const r of ROOTS) {
    for (const file of walk(join(ROOT, r))) {
      out.push({ path: file, src: readFileSync(file, 'utf8') })
    }
  }
  return out
}

const SOURCES = allSources()
const HOME = readFileSync(join(ROOT, 'app', '(dashboard)', 'page.tsx'), 'utf8')

function findHits(re: RegExp): string[] {
  const hits: string[] = []
  for (const { path, src } of SOURCES) {
    if (re.test(src)) hits.push(path)
  }
  return hits
}

describe('Polish drift gates (RMD-06)', () => {
  it('no text-xl headings outside vendored shadcn', () => {
    expect(findHits(/\btext-xl\b/)).toEqual([])
  })

  it('no text-lg headings outside vendored shadcn', () => {
    expect(findHits(/\btext-lg\b/)).toEqual([])
  })

  it('no bg-amber-500 or bg-amber-600 (CTA shade drift)', () => {
    expect(findHits(/\bbg-amber-(500|600)\b/)).toEqual([])
  })

  it('no ring-amber-* (focus-ring drift)', () => {
    expect(findHits(/\bring-amber-/)).toEqual([])
  })

  it('no bg-amber-50 decorative chips', () => {
    expect(findHits(/\bbg-amber-50\b/)).toEqual([])
  })

  it('no text-amber-600 outside spec-mandated CTAs (D-08, D-12)', () => {
    // Per spec the amber-600 token is reserved for three surfaces:
    //   - components/home/RecentScansTable.tsx ("View all" link, D-12 plan 07.2-08)
    //   - components/home/TopFindings.tsx       ("Open scan" link, D-12 plan 07.2-08)
    //   - components/share/ShareModal.tsx       ("Never" expiry warning,  D-08 plan 07.2-07)
    // text-amber-700 is allowed for the grade-C pill across the codebase.
    const allowed = (p: string) =>
      p.endsWith('/components/home/RecentScansTable.tsx') ||
      p.endsWith('/components/home/TopFindings.tsx') ||
      p.endsWith('/components/share/ShareModal.tsx')
    expect(findHits(/\btext-amber-600\b/).filter((p) => !allowed(p))).toEqual([])
  })

  it('home page uses px-8 py-12 gap-6 gutters (D-11 dropped gap-12)', () => {
    expect(HOME).toMatch(/px-8/)
    expect(HOME).toMatch(/py-12/)
    expect(HOME).toMatch(/gap-6/)
  })

  it('home page does not render an unspec "Overview" h1', () => {
    expect(HOME).not.toMatch(/<h1[^>]*>\s*Overview\s*</)
  })
})
