export interface TranslationSegment {
  id: string
  original: string
  translated: string
  pageNumber: number
  domain: string
}

export interface TranslationCache {
  paperId: string
  segments: Map<string, TranslationSegment>
  domain: string
}
