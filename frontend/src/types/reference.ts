export interface Reference {
  id: string
  title: string
  authors: string[]
  year: number
  source: string
  sourceType: 'journal' | 'conference' | 'preprint' | 'book' | 'other'
  level?: string
  doi?: string
}

export interface ReferenceAnalysis {
  totalCount: number
  yearDistribution: YearDistribution[]
  recentThreeYearRatio: number
  recentTenYearRatio: number
  sourceTypeDistribution: SourceTypeDistribution[]
  topSources: SourceCount[]
}

export interface YearDistribution {
  year: number
  count: number
}

export interface SourceTypeDistribution {
  type: Reference['sourceType']
  count: number
  ratio: number
}

export interface SourceCount {
  source: string
  count: number
  type: Reference['sourceType']
  level?: string
}
