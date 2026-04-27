import { defineStore } from 'pinia'
import { ref, computed, shallowRef } from 'vue'
import type {
  Paper,
  PaperSection,
  PaperHighlight,
  PaperOneSentenceSummary,
  ReadingPurpose,
} from '@/types'
import type { PdfOutlineNode } from '@/utils/pdf-outline'
import * as api from '@/api'

export const usePaperStore = defineStore('paper', () => {
  const currentPaper = ref<Paper | null>(null)
  const sections = ref<PaperSection[]>([])
  const highlights = ref<PaperHighlight[]>([])
  const oneSentenceSummary = ref<PaperOneSentenceSummary | null>(null)
  const recommendedSections = ref<PaperSection[]>([])
  const recommendReason = ref('')

  const currentPage = ref(1)
  const totalPages = ref(0)
  const scale = ref(1.0)
  const isTranslateMode = ref(false)
  /** 全文/PDF 翻译会话：关翻译时 abort，取消进行中的请求 */
  const fullPageTranslateAbort = shallowRef<AbortController | null>(null)
  const viewMode = ref<'pdf' | 'parsed'>('pdf')
  /** PDF 书签大纲（getOutline），切换论文或重置时清空 */
  const pdfOutline = ref<PdfOutlineNode[] | null>(null)

  const loading = ref(false)

  const isLoaded = computed(() => currentPaper.value !== null)

  async function uploadPaper(file: File) {
    loading.value = true
    try {
      currentPaper.value = await api.uploadPaper(file)
      await loadSections()
    } finally {
      loading.value = false
    }
  }

  async function loadPaper(paperId: string) {
    pdfOutline.value = null
    loading.value = true
    try {
      currentPaper.value = await api.getPaper(paperId)
      await loadSections()
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status
      if (status === 404) {
        currentPaper.value = null
        sections.value = []
        return
      }
      throw err
    } finally {
      loading.value = false
    }
  }

  async function loadSections() {
    if (!currentPaper.value) return
    sections.value = await api.getPaperSections(currentPaper.value.id)
  }

  async function loadOneSentenceSummary() {
    if (!currentPaper.value) return
    oneSentenceSummary.value = await api.getOneSentenceSummary(
      currentPaper.value.id,
    )
  }

  async function getRecommendation(purpose: ReadingPurpose) {
    if (!currentPaper.value) return
    const result = await api.getReadingRecommendation(
      currentPaper.value.id,
      purpose,
    )
    recommendedSections.value = result.sections
    recommendReason.value = result.reason
  }

  async function updateDomain(domain: string) {
    if (!currentPaper.value) return
    const updated = await api.patchPaper(currentPaper.value.id, {
      domain: domain || null,
    })
    currentPaper.value = updated
  }

  function addHighlight(highlight: PaperHighlight) {
    highlights.value.push(highlight)
  }

  function removeHighlight(id: string) {
    highlights.value = highlights.value.filter((h: PaperHighlight) => h.id !== id)
  }

  function setPage(page: number) {
    currentPage.value = page
  }

  function setScale(s: number) {
    scale.value = Math.max(0.5, Math.min(3.0, s))
  }

  function toggleTranslateMode() {
    if (isTranslateMode.value) {
      fullPageTranslateAbort.value?.abort()
      fullPageTranslateAbort.value = null
    } else {
      fullPageTranslateAbort.value = new AbortController()
    }
    isTranslateMode.value = !isTranslateMode.value
  }

  function setViewMode(mode: 'pdf' | 'parsed') {
    viewMode.value = mode
  }

  function setPdfOutline(nodes: PdfOutlineNode[] | null) {
    pdfOutline.value = nodes
  }

  function $reset() {
    fullPageTranslateAbort.value?.abort()
    fullPageTranslateAbort.value = null
    pdfOutline.value = null
    currentPaper.value = null
    sections.value = []
    highlights.value = []
    oneSentenceSummary.value = null
    recommendedSections.value = []
    recommendReason.value = ''
    currentPage.value = 1
    totalPages.value = 0
    scale.value = 1.0
    isTranslateMode.value = false
    viewMode.value = 'pdf'
  }

  return {
    currentPaper,
    sections,
    highlights,
    oneSentenceSummary,
    recommendedSections,
    recommendReason,
    currentPage,
    totalPages,
    scale,
    isTranslateMode,
    fullPageTranslateAbort,
    viewMode,
    pdfOutline,
    loading,
    isLoaded,
    uploadPaper,
    loadPaper,
    loadSections,
    loadOneSentenceSummary,
    getRecommendation,
    updateDomain,
    addHighlight,
    removeHighlight,
    setPage,
    setScale,
    toggleTranslateMode,
    setViewMode,
    setPdfOutline,
    $reset,
  }
})
