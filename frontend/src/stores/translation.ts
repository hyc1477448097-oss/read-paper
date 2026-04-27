import { defineStore } from 'pinia'
import { ref, reactive } from 'vue'
import type { TranslationSegment } from '@/types'
import * as api from '@/api'
import type { TranslateEngine } from '@/api/paper'

export const useTranslationStore = defineStore('translation', () => {
  const cache = reactive<Map<string, TranslationSegment>>(new Map())
  const detectedDomain = ref('')
  const loading = ref(false)

  function cacheKey(paperId: string, text: string, engine: TranslateEngine): string {
    return `${paperId}::${engine}::${text.slice(0, 100)}`
  }

  function getCached(
    paperId: string,
    text: string,
    engine: TranslateEngine = 'baidu',
  ): TranslationSegment | undefined {
    return cache.get(cacheKey(paperId, text, engine))
  }

  async function translate(
    paperId: string,
    text: string,
    pageNumber: number,
    domain?: string,
    engine: TranslateEngine = 'baidu',
    signal?: AbortSignal,
  ): Promise<TranslationSegment> {
    const key = cacheKey(paperId, text, engine)
    const existing = cache.get(key)
    if (existing) return existing

    loading.value = true
    try {
      const { translated, domain: returnedDomain } = await api.translateText(
        paperId,
        text,
        pageNumber,
        domain,
        engine,
        signal,
      )
      detectedDomain.value = returnedDomain

      const segment: TranslationSegment = {
        id: crypto.randomUUID(),
        original: text,
        translated,
        pageNumber,
        domain: returnedDomain,
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
