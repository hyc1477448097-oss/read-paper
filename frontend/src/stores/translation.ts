import { defineStore } from 'pinia'
import { ref, reactive } from 'vue'
import type { TranslationSegment } from '@/types'
import * as api from '@/api'

export const useTranslationStore = defineStore('translation', () => {
  const cache = reactive<Map<string, TranslationSegment>>(new Map())
  const detectedDomain = ref('')
  const loading = ref(false)

  function cacheKey(paperId: string, text: string): string {
    return `${paperId}::${text.slice(0, 100)}`
  }

  function getCached(
    paperId: string,
    text: string,
  ): TranslationSegment | undefined {
    return cache.get(cacheKey(paperId, text))
  }

  async function translate(
    paperId: string,
    text: string,
    pageNumber: number,
  ): Promise<TranslationSegment> {
    const key = cacheKey(paperId, text)
    const existing = cache.get(key)
    if (existing) return existing

    loading.value = true
    try {
      const { translated, domain } = await api.translateText(
        paperId,
        text,
        pageNumber,
      )
      detectedDomain.value = domain

      const segment: TranslationSegment = {
        id: crypto.randomUUID(),
        original: text,
        translated,
        pageNumber,
        domain,
      }
      cache.set(key, segment)
      return segment
    } finally {
      loading.value = false
    }
  }

  function clearCache() {
    cache.clear()
    detectedDomain.value = ''
  }

  function $reset() {
    clearCache()
    loading.value = false
  }

  return {
    cache,
    detectedDomain,
    loading,
    getCached,
    translate,
    clearCache,
    $reset,
  }
})
