export interface GradeInfo {
  letter: string
}

export function gradeInfo(score: number): GradeInfo {
  if (score >= 95) return { letter: 'A+' }
  if (score >= 90) return { letter: 'A' }
  if (score >= 85) return { letter: 'B+' }
  if (score >= 80) return { letter: 'B' }
  if (score >= 70) return { letter: 'C' }
  if (score >= 60) return { letter: 'D' }
  return { letter: 'F' }
}
