<script setup lang="ts">
import {
  ZoomInOutlined,
  ZoomOutOutlined,
  LeftOutlined,
  RightOutlined,
  TranslationOutlined,
  HighlightOutlined,
} from '@ant-design/icons-vue'
import { usePaperStore } from '@/stores'

const paperStore = usePaperStore()

const highlightColors = ['#fef08a', '#bbf7d0', '#bfdbfe', '#fbcfe8']
const emit = defineEmits<{
  highlight: [color: string]
}>()

function zoomIn() {
  paperStore.setScale(paperStore.scale + 0.15)
}

function zoomOut() {
  paperStore.setScale(paperStore.scale - 0.15)
}

function prevPage() {
  if (paperStore.currentPage > 1) {
    paperStore.setPage(paperStore.currentPage - 1)
  }
}

function nextPage() {
  if (paperStore.currentPage < paperStore.totalPages) {
    paperStore.setPage(paperStore.currentPage + 1)
  }
}
</script>

<template>
  <div
    class="h-11 bg-panel border-b border-border flex items-center justify-between px-4 shrink-0"
  >
    <!-- Left: view mode + page navigation -->
    <div class="flex items-center gap-3">
      <div class="flex items-center rounded-md bg-surface-alt p-0.5 text-xs">
        <button
          class="h-6 rounded px-2 transition-colors"
          :class="
            paperStore.viewMode === 'pdf'
              ? 'bg-panel text-text-primary shadow-sm'
              : 'text-text-muted hover:text-text-primary'
          "
          @click="paperStore.setViewMode('pdf')"
        >
          PDF
        </button>
        <button
          class="h-6 rounded px-2 transition-colors"
          :class="
            paperStore.viewMode === 'parsed'
              ? 'bg-panel text-text-primary shadow-sm'
              : 'text-text-muted hover:text-text-primary'
          "
          @click="paperStore.setViewMode('parsed')"
        >
          解析文本
        </button>
      </div>

      <div
        v-if="paperStore.viewMode === 'pdf'"
        class="flex items-center gap-2"
      >
        <button
          class="w-7 h-7 rounded flex items-center justify-center text-text-secondary
                 hover:bg-surface-alt disabled:opacity-40 transition-colors"
          :disabled="paperStore.currentPage <= 1"
          @click="prevPage"
        >
          <LeftOutlined class="text-xs" />
        </button>
        <span class="text-sm text-text-secondary min-w-[80px] text-center tabular-nums">
          {{ paperStore.currentPage }} / {{ paperStore.totalPages }}
        </span>
        <button
          class="w-7 h-7 rounded flex items-center justify-center text-text-secondary
                 hover:bg-surface-alt disabled:opacity-40 transition-colors"
          :disabled="paperStore.currentPage >= paperStore.totalPages"
          @click="nextPage"
        >
          <RightOutlined class="text-xs" />
        </button>
      </div>
      <span
        v-else
        class="text-xs text-text-muted tabular-nums"
      >
        共 {{ paperStore.sections.length }} 段章节
      </span>
    </div>

    <!-- Center: Zoom (PDF only) -->
    <div
      v-if="paperStore.viewMode === 'pdf'"
      class="flex items-center gap-2"
    >
      <button
        class="w-7 h-7 rounded flex items-center justify-center text-text-secondary
               hover:bg-surface-alt transition-colors"
        @click="zoomOut"
      >
        <ZoomOutOutlined class="text-xs" />
      </button>
      <span class="text-xs text-text-muted min-w-[40px] text-center tabular-nums">
        {{ Math.round(paperStore.scale * 100) }}%
      </span>
      <button
        class="w-7 h-7 rounded flex items-center justify-center text-text-secondary
               hover:bg-surface-alt transition-colors"
        @click="zoomIn"
      >
        <ZoomInOutlined class="text-xs" />
      </button>
    </div>
    <div v-else />

    <!-- Right: Tools -->
    <div
      v-if="paperStore.viewMode === 'pdf'"
      class="flex items-center gap-2"
    >
      <!-- Highlight colors -->
      <div class="flex items-center gap-1 mr-2">
        <HighlightOutlined class="text-sm text-text-muted mr-1" />
        <button
          v-for="color in highlightColors"
          :key="color"
          class="w-5 h-5 rounded-full border-2 border-transparent hover:border-text-muted
                 transition-colors"
          :style="{ backgroundColor: color }"
          :title="`高亮颜色`"
          @click="emit('highlight', color)"
        />
      </div>

      <div class="w-px h-5 bg-border mx-1" />

      <!-- Translation toggle -->
      <button
        class="h-7 px-2.5 rounded-md flex items-center gap-1.5 text-xs font-medium transition-colors"
        :class="
          paperStore.isTranslateMode
            ? 'bg-primary text-white'
            : 'text-text-secondary hover:bg-surface-alt'
        "
        @click="paperStore.toggleTranslateMode()"
      >
        <TranslationOutlined class="text-sm" />
        翻译
      </button>
    </div>
  </div>
</template>
