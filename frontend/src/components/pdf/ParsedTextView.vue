<script setup lang="ts">
import { computed } from 'vue'
import { usePaperStore } from '@/stores'
import type { PaperSection } from '@/types'

const paperStore = usePaperStore()

const sortedSections = computed<PaperSection[]>(() =>
  [...paperStore.sections].sort((a, b) => a.idx - b.idx),
)

function pageLabel(s: PaperSection): string {
  if (s.page_start == null) return ''
  if (s.page_end == null || s.page_end === s.page_start) return `P${s.page_start}`
  return `P${s.page_start}-${s.page_end}`
}

function headingClass(level: number): string {
  if (level <= 1) return 'text-lg font-semibold text-text-primary'
  if (level === 2) return 'text-base font-semibold text-text-primary'
  return 'text-sm font-medium text-text-secondary'
}

function summaryText(s: PaperSection): string {
  if (!s.summary) return ''
  if (typeof s.summary === 'string') return s.summary
  return s.summary.content ?? ''
}
</script>

<template>
  <div class="h-full overflow-auto bg-surface">
    <div class="mx-auto max-w-[880px] px-8 py-8">
      <!-- Paper header -->
      <div v-if="paperStore.currentPaper" class="mb-6 border-b border-border pb-5">
        <h1 class="text-2xl font-bold text-text-primary leading-tight">
          {{ paperStore.currentPaper.title || '未命名论文' }}
        </h1>
        <div
          v-if="paperStore.currentPaper.authors || paperStore.currentPaper.domain"
          class="mt-2 flex flex-wrap items-center gap-3 text-xs text-text-muted"
        >
          <span v-if="paperStore.currentPaper.authors">
            {{ paperStore.currentPaper.authors }}
          </span>
          <span
            v-if="paperStore.currentPaper.domain"
            class="rounded-full bg-primary/10 px-2 py-0.5 text-primary"
          >
            {{ paperStore.currentPaper.domain }}
          </span>
        </div>
      </div>

      <!-- Empty state -->
      <div
        v-if="!paperStore.currentPaper"
        class="flex h-[60vh] flex-col items-center justify-center text-text-muted"
      >
        <div
          class="mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10"
        >
          <span class="text-2xl">📄</span>
        </div>
        <p class="text-sm">请先选择或导入一篇论文</p>
      </div>

      <div
        v-else-if="sortedSections.length === 0"
        class="flex h-[40vh] items-center justify-center text-sm text-text-muted"
      >
        <template v-if="paperStore.loading">加载解析内容中...</template>
        <template v-else>
          未从数据库读取到章节内容。可能解析失败或该论文暂未入库。
        </template>
      </div>

      <!-- Sections -->
      <article v-else class="space-y-6">
        <section
          v-for="s in sortedSections"
          :key="s.id"
          class="rounded-lg border border-border bg-panel px-5 py-4 shadow-[0_1px_2px_rgba(0,0,0,0.03)]"
        >
          <header class="mb-2 flex flex-wrap items-start justify-between gap-2">
            <h2 :class="headingClass(s.level || 1)">
              {{ s.title || '未命名章节' }}
            </h2>
            <div class="flex items-center gap-2 text-[11px] tabular-nums">
              <span
                v-if="pageLabel(s)"
                class="rounded bg-surface-alt px-1.5 py-0.5 text-text-muted"
              >
                {{ pageLabel(s) }}
              </span>
              <span
                v-if="s.category"
                class="rounded bg-primary/10 px-1.5 py-0.5 text-primary"
              >
                {{ s.category }}
              </span>
            </div>
          </header>

          <p
            v-if="summaryText(s)"
            class="mb-2 rounded bg-surface-alt px-3 py-2 text-xs text-text-secondary"
          >
            <span class="font-medium text-text-primary">摘要：</span>
            {{ summaryText(s) }}
          </p>

          <pre
            class="whitespace-pre-wrap break-words font-sans text-sm leading-relaxed text-text-primary"
          >{{ s.content }}</pre>
        </section>
      </article>
    </div>
  </div>
</template>
