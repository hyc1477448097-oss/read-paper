export * from './paper'
export * from './chat'
export * from './translation'
export * from './reference'

export interface RelevanceAnalysis {
  score: number
  matchedTopics: string[]
  recommendation: string
  readingValue: 'high' | 'medium' | 'low'
  details: string
}

export interface UserProfile {
  researchDirection: string
  keywords: string[]
}
