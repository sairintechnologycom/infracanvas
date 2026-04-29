#!/usr/bin/env node
// lighthouse-check.mjs
// Runs Lighthouse against the locally-built dashboard and asserts performance budgets.
// Usage: node dashboard/scripts/lighthouse-check.mjs
// Prerequisites: `next build && next start` running on localhost:3000
// CI integration: deferred (DSH-05/06 budget declared here; wired to CI later).

import { readFileSync } from 'fs'
import { fileURLToPath } from 'url'
import path from 'path'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const configPath = path.join(__dirname, '..', 'lighthouse.config.json')
const config = JSON.parse(readFileSync(configPath, 'utf8'))

let lighthouse, chromeLauncher
try {
  lighthouse = (await import('lighthouse')).default
  chromeLauncher = await import('chrome-launcher')
} catch {
  console.error('[lighthouse-check] lighthouse or chrome-launcher not installed.')
  console.error('[lighthouse-check] Run: npm install --save-dev lighthouse chrome-launcher')
  process.exit(2)
}

const TARGET_URL = process.env.LIGHTHOUSE_URL ?? 'http://localhost:3000/scans'
const budgets = config.budgets?.[0]?.timings ?? []

console.log(`[lighthouse-check] Running Lighthouse against ${TARGET_URL}`)

const chrome = await chromeLauncher.launch({ chromeFlags: ['--headless', '--no-sandbox'] })
const result = await lighthouse(TARGET_URL, {
  port: chrome.port,
  onlyCategories: ['performance'],
  output: 'json',
})
await chrome.kill()

const lhr = result.lhr
let failed = false
const METRIC_MAP = {
  'first-contentful-paint':   'first-contentful-paint',
  'largest-contentful-paint': 'largest-contentful-paint',
  'total-blocking-time':      'total-blocking-time',
  'cumulative-layout-shift':  'cumulative-layout-shift',
}

for (const { metric, budget } of budgets) {
  const key = METRIC_MAP[metric]
  if (!key) continue
  const actual = lhr.audits[key]?.numericValue ?? 0
  const pass = actual <= budget
  const symbol = pass ? '✓' : '✗'
  console.log(`  ${symbol} ${metric}: ${actual.toFixed(1)} (budget: ${budget})`)
  if (!pass) failed = true
}

if (failed) {
  console.error('[lighthouse-check] One or more budgets exceeded.')
  process.exit(1)
} else {
  console.log('[lighthouse-check] All budgets passed.')
  process.exit(0)
}
