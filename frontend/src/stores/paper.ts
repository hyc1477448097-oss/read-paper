import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  Paper,
  PaperSection,
  PaperHighlight,
  PaperOneSentenceSummary,
  ReadingPurpose,
  SectionCategory,
} from '@/types'
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
  const viewMode = ref<'pdf' | 'parsed'>('pdf')

  const loading = ref(false)
  const summarizing = ref(false)

  const isLoaded = computed(() => currentPaper.value !== null)

  const sectionsByCategory = computed(() => {
    const map: Partial<Record<SectionCategory, PaperSection[]>> = {}
    for (const section of sections.value) {
      const cat =
        section.category ??
        (typeof section.summary === 'object' && section.summary
          ? section.summary.category
          : undefined)
      if (!cat) continue
      if (!map[cat]) map[cat] = []
      map[cat]!.push(section)
    }
    return map
  })

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

  async function summarizeAll() {
    if (!currentPaper.value) return
    summarizing.value = true
    try {
      sections.value = await api.summarizeSections(currentPaper.value.id)
    } finally {
      summarizing.value = false
    }
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
    isTranslateMode.value = !isTranslateMode.value
  }

  function setViewMode(mode: 'pdf' | 'parsed') {
    viewMode.value = mode
  }

  function $reset() {
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
    viewMode,
    loading,
    summarizing,
    isLoaded,
    sectionsByCategory,
    uploadPaper,
    loadPaper,
    loadSections,
    summarizeAll,
    loadOneSentenceSummary,
    getRecommendation,
    addHighlight,
    removeHighlight,
    setPage,
    setScale,
    toggleTranslateMode,
    setViewMode,
    $reset,
  }
})
