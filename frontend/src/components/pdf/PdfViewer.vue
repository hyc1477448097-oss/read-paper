<script setup lang="ts">
import { ref, shallowRef, watch, onMounted } from 'vue'
import { loadPdfDocument } from '@/utils/pdf'
import { usePaperStore } from '@/stores'
import PdfToolbar from './PdfToolbar.vue'
import PdfPage from './PdfPage.vue'
import ParsedTextView from './ParsedTextView.vue'

const props = defineProps<{
  fileUrl?: string
}>()

const emit = defineEmits<{
  textSelected: [payload: { text: string; pageNumber: number }]
  paragraphClick: [payload: { text: string; pageNumber: number; rect: DOMRect }]
  fileLoaded: []
}>()

const paperStore = usePaperStore()
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const pdfDoc = shallowRef<any>(null)
const containerRef = ref<HTMLDivElement>()
const loadError = ref('')

async function loadFile(url: string) {
  try {
    loadError.value = ''
    pdfDoc.value = await loadPdfDocument(url)
    paperStore.totalPages = pdfDoc.value.numPages
    paperStore.setPage(1)
    emit('fileLoaded')
  } catch (e) {
    loadError.value = 'PDF 加载失败，请检查文件是否有效。'
    console.error(e)
  }
}

function handleHighlight(color: string) {
  const selection = window.getSelection()
  if (!selection || selection.isCollapsed) return

  const range = selection.getRangeAt(0)
  const span = document.createElement('span')
  span.style.backgroundColor = color
  span.style.borderRadius = '2px'
  range.surroundContents(span)
  selection.removeAllRanges()
}

function scrollToPage(page: number) {
  if (!containerRef.value) return
  const pageEl = containerRef.value.querySelector(`[data-page="${page}"]`)
  pageEl?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

watch(
  () => props.fileUrl,
  (url) => {
    if (url) loadFile(url)
  },
)

watch(
  () => paperStore.currentPage,
  (page) => scrollToPage(page),
)

onMounted(() => {
  if (props.fileUrl) loadFile(props.fileUrl)
})

defineExpose({ scrollToPage })
</script>

<template>
  <div class="flex flex-col h-full bg-surface-alt">
    <PdfToolbar @highlight="handleHighlight" />

    <!-- Parsed text view -->
    <ParsedTextView v-if="paperStore.viewMode === 'parsed'" class="flex-1" />

    <!-- PDF view -->
    <div
      v-else
      ref="containerRef"
      class="flex-1 overflow-auto px-4 py-2"
    >
      <!-- Loading -->
      <div
        v-if="!pdfDoc && !loadError"
        class="flex items-center justify-center h-full text-text-muted"
      >
        <div class="text-center">
          <div class="w-12 h-12 mx-auto mb-3 rounded-xl bg-primary/10 flex items-center justify-center">
            <span class="text-2xl">📄</span>
          </div>
          <p class="text-sm">上传或选择一篇论文开始阅读</p>
        </div>
      </div>

      <!-- Error -->
      <div
        v-else-if="loadError"
        class="flex items-center justify-center h-full"
      >
        <div class="text-center text-danger">
          <p class="text-sm">{{ loadError }}</p>
        </div>
      </div>

      <!-- Pages -->
      <template v-else-if="pdfDoc">
        <div
          v-for="page in pdfDoc.numPages"
          :key="page"
          :data-page="page"
        >
          <PdfPage
            :pdf="pdfDoc"
            :page-number="page"
            @text-selected="emit('textSelected', $event)"
            @paragraph-click="emit('paragraphClick', $event)"
          />
        </div>
      </template>
    </div>
  </div>
</template>
