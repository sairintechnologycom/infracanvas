import { describe, it, expect } from 'vitest'
import { existsSync, readdirSync, readFileSync } from 'node:fs'
import { join } from 'node:path'

const ROOT = join(__dirname, '..')
const UI = join(ROOT, 'components', 'ui')

describe('shadcn init (Phase 7.1 Wave 0)', () => {
  it('components.json exists', () => {
    expect(existsSync(join(ROOT, 'components.json'))).toBe(true)
  })
  it('lib/utils.ts exists with cn()', () => {
    const utils = readFileSync(join(ROOT, 'lib', 'utils.ts'), 'utf8')
    expect(utils).toMatch(/export function cn/)
  })
  it('17 shadcn blocks present in components/ui/', () => {
    const files = readdirSync(UI).filter(f => f.endsWith('.tsx'))
    const required = [
      'button', 'dialog', 'alert-dialog', 'dropdown-menu', 'select',
      'input', 'popover', 'calendar', 'table', 'tabs', 'sheet',
      'skeleton', 'sonner', 'pagination', 'form', 'label', 'card',
    ]
    for (const block of required) {
      expect(files).toContain(`${block}.tsx`)
    }
  })
  it('globals.css preserves viewer styles import on line 1', () => {
    const css = readFileSync(join(ROOT, 'app', 'globals.css'), 'utf8')
    const firstLine = css.split('\n').find(l => l.trim().length > 0) ?? ''
    expect(firstLine).toMatch(/@import\s+["']@infracanvas\/viewer\/styles\.css["']/)
  })
  it('globals.css preserves .sidebar-collapsed custom utility', () => {
    const css = readFileSync(join(ROOT, 'app', 'globals.css'), 'utf8')
    expect(css).toMatch(/\.sidebar-collapsed/)
  })
})
