import { describe, it, expect } from 'vitest'
import { gradeInfo } from './grade'

describe('gradeInfo', () => {
  it.each([
    [100, 'A+'], [95, 'A+'],
    [94, 'A'], [90, 'A'],
    [89, 'B+'], [85, 'B+'],
    [84, 'B'], [80, 'B'],
    [79, 'C'], [70, 'C'],
    [69, 'D'], [60, 'D'],
    [59, 'F'], [0, 'F'],
  ])('score %i → %s', (score, letter) => {
    expect(gradeInfo(score).letter).toBe(letter)
  })
})
