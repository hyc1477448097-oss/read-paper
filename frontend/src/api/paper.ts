import apiClient from './client'
import type {
  Paper,
  PaperBrief,
  PaperSection,
  PaperOneSentenceSummary,
  ReadingPurpose,
  ReferenceAnalysis,
  RelevanceAnalysis,
} from '@/types'

export async function listPapers(): Promise<PaperBrief[]> {
  const { data } = await apiClient.get<PaperBrief[]>('/papers/')
  return data
}

export async function uploadPaper(file: File): Promise<Paper> {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await apiClient.post<Paper>('/papers/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function deletePaper(paperId: string): Promise<void> {
  await apiClient.delete(`/papers/${paperId}`)
}

export async function getPaper(paperId: string): Promise<Paper> {
  const { data } = await apiClient.get<Paper>(`/papers/${paperId}`)
  return data
}

export async function patchPaper(
  paperId: string,
  fields: { domain?: string | null },
): Promise<Paper> {
  const { data } = await apiClient.patch<Paper>(`/papers/${paperId}`, fields)
  return data
}

export async function getPaperSections(paperId: string): Promise<PaperSection[]> {
  const { data } = await apiClient.get<PaperSection[]>(`/papers/${paperId}/sections`)
  return data
}

export async function translateText(
  paperId: string,
  text: string,
  pageNumber: number,
  domain?: string,
): Promise<{ translated: string; domain: string }> {
  const { data } = await apiClient.post(`/papers/${paperId}/translate`, {
    text,
    page_number: pageNumber,
    domain: domain || undefined,
  })
  return data
}

export async function askQuestion(
  paperId: string,
  question: string,
  context?: { selectedText?: string; pageNumber?: number },
): Promise<{ answer: string }> {
  const { data } = await apiClient.post(`/papers/${paperId}/ask`, {
    question,
    context,
  })
  return data
}

export async function summarizeSections(
  paperId: string,
): Promise<PaperSection[]> {
  const { data } = await apiClient.post<PaperSection[]>(
    `/papers/${paperId}/summarize`,
  )
  return data
}

export async function getReadingRecommendation(
  paperId: string,
  purpose: ReadingPurpose,
): Promise<{ sections: PaperSection[]; reason: string }> {
  const { data } = await apiClient.post(`/papers/${paperId}/recommend`, {
    purpose,
  })
  return data
}

export async function getOneSentenceSummary(
  paperId: string,
): Promise<PaperOneSentenceSummary> {
  const { data } = await apiClient.get<PaperOneSentenceSummary>(
    `/papers/${paperId}/one-sentence`,
  )
  return data
}

export async function getReferenceAnalysis(
  paperId: string,
): Promise<ReferenceAnalysis> {
  const { data } = await apiClient.get<ReferenceAnalysis>(
    `/papers/${paperId}/references`,
  )
  return data
}

export async function getRelevanceAnalysis(
  paperId: string,
  researchDirection: string,
  keywords: string[],
): Promise<RelevanceAnalysis> {
  const { data } = await apiClient.post<RelevanceAnalysis>(
    `/papers/${paperId}/relevance`,
    { research_direction: researchDirection, keywords },
  )
  return data
}
