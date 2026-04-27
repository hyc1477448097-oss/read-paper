<script setup lang="ts">
import { ref, computed } from 'vue'
import { MenuUnfoldOutlined, MenuFoldOutlined } from '@ant-design/icons-vue'
import { usePaperStore, useTranslationStore } from '@/stores'
import type { PaperSection } from '@/types'
import CatalogPanel from '@/components/catalog/CatalogPanel.vue'
import PdfViewer from '@/components/pdf/PdfViewer.vue'
import FunctionPanel from '@/components/function/FunctionPanel.vue'

const paperStore = usePaperStore()
const translationStore = useTranslationStore()
const functionPanelRef = ref<InstanceType<typeof FunctionPanel>>()

const selectedContext = ref<{ text: string; pageNumber: number } | null>(null)
const selectedSection = ref<PaperSection | null>(null)
const translationResult = ref<{ original: string; translated: string } | null>(null)

const catalogOpen = ref(true)
const functionOpen = ref(true)

const catalogWidth = ref(Math.round(window.innerWidth * 0.2))
const functionWidth = ref(Math.round(window.innerWidth * 0.35))

const isResizing = ref(false)

const pdfFileUrl = computed(() =>
  paperStore.currentPaper ? `/api/papers/${paperStore.currentPaper.id}/file` : undefined,
)

function handleTextSelected(payload: { text: string; pageNumber: number }) {
  const activeFunc = functionPanelRef.value?.activeFunc
  if (activeFunc === 'translate') {
    if (!paperStore.currentPaper) return
    translationResult.value = null
    const domain = functionPanelRef.value?.userDomain || undefined
    translationStore
      .translate(paperStore.currentPaper.id, payload.text, payload.pageNumber, domain, 'llm')
      .then((seg) => {
        translationResult.value = { original: seg.original, translated: seg.translated }
      })
      .catch(() => {})
  } else if (activeFunc === 'chat') {
    selectedContext.value = payload
  }
}

function handleParagraphClick(payload: { text: string; pageNumber: number; rect: DOMRect }) {
  const activeFunc = functionPanelRef.value?.activeFunc
  if (activeFunc === 'summary') {
    const match = paperStore.sections.find(
      (s: PaperSection) => s.content && s.content.includes(payload.text),
    )
    if (match) selectedSection.value = match
  }
}

function handleSelectPaper(paperId: string) {
  paperStore.loadPaper(paperId)
}

function startResize(
  widthRef: { value: number },
  min: number,
  max: number,
  direction: 'left' | 'right',
) {
  return (e: MouseEvent) => {
    e.preventDefault()
    isResizing.value = true
    const startX = e.clientX
    const startWidth = widthRef.value

    function onMove(ev: MouseEvent) {
      const delta = ev.clientX - startX
      const newWidth = direction === 'left'
        ? startWidth + delta
        : startWidth - delta
      widthRef.value = Math.max(min, Math.min(max, newWidth))
    }

    function onUp() {
      isResizing.value = false
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }

    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
  }
}

const startCatalogResize = startResize(
  catalogWidth,
  Math.round(window.innerWidth * 0.1),
  Math.round(window.innerWidth * 0.3),
  'left',
)
const startFunctionResize = startResize(
  functionWidth,
  Math.round(window.innerWidth * 0.2),
  Math.round(window.innerWidth * 0.45),
  'right',
)
</script>

<template>
  <div
    class="flex-1 flex flex-row overflow-hidden"
    :class="{ 'select-none': isResizing }"
  >
    <!-- ========== LEFT: Catalog Panel ========== -->
    <template v-if="catalogOpen">
      <div
        class="shrink-0 overflow-hidden border-r border-border"
        :style="{ width: `${catalogWidth}px` }"
      >
        <CatalogPanel
          @select-paper="handleSelectPaper"
          @collapse="catalogOpen = false"
        />
      </div>

      <!-- Resize handle: catalog | PDF -->
      <div
        class="w-1 hover:w-1.5 bg-transparent hover:bg-primary/20 cursor-col-resize
               transition-all shrink-0 active:bg-primary/30"
        @mousedown="startCatalogResize"
      />
    </template>

    <!-- Collapsed catalog toggle -->
    <div
      v-else
      class="w-8 shrink-0 flex flex-col items-center pt-3 bg-panel border-r border-border
             cursor-pointer hover:bg-surface-alt transition-colors"
      title="展开目录"
      @click="catalogOpen = true"
    >
      <MenuUnfoldOutlined class="text-sm text-text-muted" />
      <span class="mt-2 text-[10px] text-text-muted writing-vertical">目录</span>
    </div>

    <!-- ========== CENTER: PDF Viewer ========== -->
    <div class="flex-1 min-w-0 overflow-hidden">
      <PdfViewer
        :file-url="pdfFileUrl"
        @text-selected="handleTextSelected"
        @paragraph-click="handleParagraphClick"
      />
    </div>

    <!-- ========== RIGHT: Function Panel ========== -->
    <template v-if="functionOpen">
      <!-- Resize handle: PDF | function -->
      <div
        class="w-1 hover:w-1.5 bg-transparent hover:bg-primary/20 cursor-col-resize
               transition-all shrink-0 active:bg-primary/30"
        @mousedown="startFunctionResize"
      />

      <div
        class="shrink-0 overflow-hidden border-l border-border"
        :style="{ width: `${functionWidth}px` }"
      >
        <FunctionPanel
          ref="functionPanelRef"
          :selected-context="selectedContext"
          :selected-section="selectedSection"
          :translation-result="translationResult"
          @collapse="functionOpen = false"
        />
      </div>
    </template>

    <!-- Collapsed function toggle -->
    <div
      v-else
      class="w-8 shrink-0 flex flex-col items-center pt-3 bg-panel border-l border-border
             cursor-pointer hover:bg-surface-alt transition-colors"
      title="展开功能面板"
      @click="functionOpen = true"
    >
      <MenuFoldOutlined class="text-sm text-text-muted" />
      <span class="mt-2 text-[10px] text-text-muted writing-vertical">功能</span>
    </div>
  </div>
</template>

<style scoped>
.writing-vertical {
  writing-mode: vertical-rl;
  text-orientation: mixed;
}
</style>
