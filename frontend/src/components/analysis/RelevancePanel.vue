<script setup lang="ts">
import { ref } from 'vue'
import { AimOutlined, TagsOutlined, CheckCircleOutlined } from '@ant-design/icons-vue'
import { usePaperStore, useUserStore } from '@/stores'
import type { RelevanceAnalysis } from '@/types'
import * as api from '@/api'

const paperStore = usePaperStore()
const userStore = useUserStore()

const result = ref<RelevanceAnalysis | null>(null)
const loading = ref(false)

const valueColorMap: Record<string, { bg: string; text: string; label: string }> = {
  high: { bg: 'bg-success/10', text: 'text-success', label: '高' },
  medium: { bg: 'bg-warning/10', text: 'text-warning', label: '中' },
  low: { bg: 'bg-text-muted/10', text: 'text-text-muted', label: '低' },
}

async function analyze() {
  if (!paperStore.currentPaper) return
  loading.value = true
  try {
    result.value = await api.getRelevanceAnalysis(
      paperStore.currentPaper.id,
      userStore.profile.researchDirection,
      userStore.profile.keywords,
    )
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="p-4 space-y-5 overflow-auto h-full">
    <!-- User profile check -->
    <div
      v-if="!userStore.hasProfile"
      class="flex flex-col items-center justify-center h-60 text-center"
    >
      <div class="w-12 h-12 mx-auto mb-3 rounded-xl bg-warning/10 flex items-center justify-center">
        <span class="text-2xl">🎯</span>
      </div>
      <p class="text-sm text-text-secondary mb-1">请先设置您的研究方向</p>
      <p class="text-xs text-text-muted">
        点击右上角设置图标，填写研究方向和关键词
      </p>
    </div>

    <template v-else>
      <!-- Your profile -->
      <section class="bg-surface-alt rounded-lg p-3">
        <div class="flex items-center gap-2 mb-2">
          <TagsOutlined class="text-primary" />
          <h4 class="text-xs font-semibold text-text-secondary">您的研究方向</h4>
        </div>
        <p class="text-sm text-text-primary font-medium">
          {{ userStore.profile.researchDirection }}
        </p>
        <div v-if="userStore.profile.keywords.length" class="flex flex-wrap gap-1 mt-2">
          <span
            v-for="kw in userStore.profile.keywords"
            :key="kw"
            class="px-2 py-0.5 rounded-full bg-primary/10 text-primary text-xs"
          >
            {{ kw }}
          </span>
        </div>
      </section>

      <!-- Analyze button -->
      <button
        v-if="!result"
        class="w-full h-10 rounded-lg bg-primary text-white text-sm font-medium
               hover:bg-primary-light transition-colors disabled:opacity-50"
        :disabled="loading"
        @click="analyze"
      >
        {{ loading ? '分析中...' : '分析契合度' }}
      </button>

      <!-- Result -->
      <template v-if="result">
        <!-- Score -->
        <section class="text-center">
          <div class="relative w-24 h-24 mx-auto">
            <svg class="w-full h-full -rotate-90" viewBox="0 0 100 100">
              <circle cx="50" cy="50" r="42" fill="none" stroke="#e2e8f0" stroke-width="8" />
              <circle
                cx="50" cy="50" r="42" fill="none"
                :stroke="result.readingValue === 'high' ? '#10b981' : result.readingValue === 'medium' ? '#f59e0b' : '#94a3b8'"
                stroke-width="8" stroke-linecap="round"
                :stroke-dasharray="`${result.score * 2.64} 264`"
              />
            </svg>
            <div class="absolute inset-0 flex items-center justify-center">
              <span class="text-2xl font-bold text-text-primary">{{ result.score }}</span>
            </div>
          </div>
          <div class="mt-2">
            <span
              class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium"
              :class="[
                valueColorMap[result.readingValue].bg,
                valueColorMap[result.readingValue].text,
              ]"
            >
              <CheckCircleOutlined />
              阅读价值：{{ valueColorMap[result.readingValue].label }}
            </span>
          </div>
        </section>

        <!-- Matched topics -->
        <section v-if="result.matchedTopics.length">
          <div class="flex items-center gap-2 mb-2">
            <AimOutlined class="text-success" />
            <h4 class="text-sm font-semibold text-text-primary">匹配话题</h4>
          </div>
          <div class="flex flex-wrap gap-1.5">
            <span
              v-for="topic in result.matchedTopics"
              :key="topic"
              class="px-2.5 py-1 rounded-md bg-success/10 text-success text-xs"
            >
              {{ topic }}
            </span>
          </div>
        </section>

        <!-- Recommendation -->
        <section>
          <h4 class="text-sm font-semibold text-text-primary mb-2">AI 建议</h4>
          <p class="text-sm text-text-secondary leading-relaxed bg-surface-alt rounded-lg p-3">
            {{ result.recommendation }}
          </p>
        </section>

        <!-- Details -->
        <section>
          <h4 class="text-sm font-semibold text-text-primary mb-2">详细分析</h4>
          <p class="text-sm text-text-secondary leading-relaxed">
            {{ result.details }}
          </p>
        </section>
      </template>
    </template>
  </div>
</template>
