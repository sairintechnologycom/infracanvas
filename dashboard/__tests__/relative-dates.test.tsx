import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { formatRelativeDate } from '@/components/home/RecentScansTable'

const NOW = new Date('2026-04-29T12:00:00Z')

beforeEach(() => {
  vi.useFakeTimers()
  vi.setSystemTime(NOW)
})
afterEach(() => {
  vi.useRealTimers()
})

describe('formatRelativeDate (RMD-06 voice rules)', () => {
  it('< 1 hour -> "Just now"', () => {
    expect(formatRelativeDate('2026-04-29T11:30:00Z')).toBe('Just now')
  })
  it('exactly 1 hour ago -> "1 hour ago" (singular)', () => {
    expect(formatRelativeDate('2026-04-29T11:00:00Z')).toBe('1 hour ago')
  })
  it('2 hours ago -> "2 hours ago" (plural)', () => {
    expect(formatRelativeDate('2026-04-29T10:00:00Z')).toBe('2 hours ago')
  })
  it('1 calendar day ago -> "Yesterday"', () => {
    expect(formatRelativeDate('2026-04-28T12:00:00Z')).toBe('Yesterday')
  })
  it('7 days ago -> month-day form (e.g. "Apr 22")', () => {
    expect(formatRelativeDate('2026-04-22T12:00:00Z')).toBe('Apr 22')
  })
})
