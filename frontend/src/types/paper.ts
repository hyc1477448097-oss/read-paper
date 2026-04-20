export interface Paper {
  id: string
  title: string
  authors: string[]
  abstract: string
  domain: string
  uploadedAt: string
  pageCount: number
  fileName: string
}

/** 与后端 PaperBrief 一致（列表接口） */
export interface PaperBrief {
  id: string
  title: string
  domain: string | null
  page_count: number
  created_at: string
}

export interface PaperSection {
  id: string
  idx: number
  title: string | null
  content: string
  level: number
  page_start: number | null
  page_end: number | null
  category: SectionCategory | null
  /** 后端返回的是字符串总结；老字段结构保留为兼容用 */
  summary?: string | SectionSummary | null
}

export interface SectionSummary {
  content: string
  category: SectionCategory
  keywords: string[]
}

export type SectionCategory =
  | 'background'
  | 'methodology'
  | 'innovation'
  | 'experiment'
  | 'discussion'
  | 'conclusion'
  | 'other'

export const SECTION_CATEGORY_LABELS: Record<SectionCategory, string> = {
  background: '研究背景',
  methodology: '方法论',
  innovation: '创新点',
  experiment: '实验',
  discussion: '讨论',
  conclusion: '总结展望',
  other: '其他',
}

export interface PaperHighlight {
  id: string
  paperId: string
  pageNumber: number
  text: string
  position: HighlightPosition
  color: string
  note?: string
  createdAt: string
}

export interface HighlightPosition {
  rects: DOMRect[]
  pageIndex: number
}

export interface InnovationPoint {
  title: string
  description: string
  significance: 'high' | 'medium' | 'low'
}

export interface PaperOneSentenceSummary {
  summary: string
  innovations: InnovationPoint[]
}

export type ReadingPurpose =
  | 'innovation'
  | 'background'
  | 'writing'
  | 'preprocessing'
  | 'visualization'
  | 'outlook'

export const READING_PURPOSE_LABELS: Record<ReadingPurpose, string> = {
  innovation: '创新点灵感',
  background: '研究背景',
  writing: '写作方法',
  preprocessing: '预处理方法',
  visualization: '画图技巧',
  outlook: '总结展望',
}
