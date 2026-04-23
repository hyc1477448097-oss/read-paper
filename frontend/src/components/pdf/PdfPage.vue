<script setup lang="ts">
import { ref, onMounted, watch, nextTick, toRaw } from 'vue'
import { TextLayer } from 'pdfjs-dist'
import { renderPage } from '@/utils/pdf'
import { usePaperStore, useTranslationStore } from '@/stores'

const props = defineProps<{
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  pdf: any
  pageNumber: number
}>()

const emit = defineEmits<{
  textSelected: [payload: { text: string; pageNumber: number }]
  paragraphClick: [payload: { text: string; pageNumber: number; rect: DOMRect }]
}>()

const paperStore = usePaperStore()
const translationStore = useTranslationStore()

const canvasRef = ref<HTMLCanvasElement>()
const textLayerRef = ref<HTMLDivElement>()
const pageWidth = ref(0)
const pageHeight = ref(0)

interface TranslationBlock {
  text: string
  el: HTMLElement
  translation?: string
}

const translationBlocks = ref<TranslationBlock[]>([])

let activeTextLayer: InstanceType<typeof TextLayer> | null = null

async function render() {
  if (!canvasRef.value || !props.pdf) return

  const rawPdf = toRaw(props.pdf)
  const { width, height } = await renderPage(
    rawPdf,
    props.pageNumber,
    canvasRef.value,
    paperStore.scale,
  )
  pageWidth.value = width
  pageHeight.value = height

  await buildTextLayer(rawPdf)
}

async function buildTextLayer(rawPdf: any) {
  if (!textLayerRef.value) return

  if (activeTextLayer) {
    activeTextLayer.cancel()
    activeTextLayer = null
  }
  textLayerRef.value.replaceChildren()

  const page = await rawPdf.getPage(props.pageNumber)
  const viewport = page.getViewport({ scale: paperStore.scale })
  const textContent = await page.getTextContent()

  if (!textLayerRef.value) return

  const textLayer = new TextLayer({
    textContentSource: textContent,
    container: textLayerRef.value,
    viewport,
  })
  activeTextLayer = textLayer
  await textLayer.render()

  attachSpanEvents()
  collectTranslationBlocks()
}

function attachSpanEvents() {
  if (!textLayerRef.value) return
  const spans = textLayerRef.value.querySelectorAll<HTMLSpanElement>('span')
  for (const span of spans) {
    if (!span.textContent?.trim()) continue
    span.addEventListener('click', (e) => {
      const rect = span.getBoundingClientRect()
      emit('paragraphClick', {
        text: span.textContent?.trim() || '',
        pageNumber: props.pageNumber,
        rect,
      })
    })
  }
}

function collectTranslationBlocks() {
  if (!textLayerRef.value) return
  const blocks: TranslationBlock[] = []
  const spans = textLayerRef.value.querySelectorAll<HTMLSpanElement>('span')
  for (const span of spans) {
    const text = span.textContent?.trim()
    if (!text || text.length < 3) continue
    blocks.push({ text, el: span })
  }
  translationBlocks.value = blocks
}

async function loadTranslations() {
  if (!paperStore.isTranslateMode || !paperStore.currentPaper) return
  for (const block of translationBlocks.value) {
    const cached = translationStore.getCached(
      paperStore.currentPaper.id,
      block.text,
    )
    if (cached) {
      block.translation = cached.translated
    } else {
      try {
        const seg = await translationStore.translate(
          paperStore.currentPaper.id,
          block.text,
          props.pageNumber,
        )
        block.translation = seg.translated
      } catch {
        // skip failed translations silently
      }
    }
  }
}

function handleMouseUp() {
  const selection = window.getSelection()
  if (!selection || selection.isCollapsed) return
  const text = selection.toString().trim()
  if (text) {
    emit('textSelected', { text, pageNumber: props.pageNumber })
  }
}

function getBlockPosition(block: TranslationBlock) {
  const container = textLayerRef.value
  if (!container) return { left: '0px', top: '0px', maxWidth: '200px', fontSize: '11px' }
  const containerRect = container.getBoundingClientRect()
  const elRect = block.el.getBoundingClientRect()
  return {
    left: `${elRect.left - containerRect.left}px`,
    top: `${elRect.top - containerRect.top + elRect.height + 2}px`,
    maxWidth: `${Math.max(elRect.width, 200)}px`,
    fontSize: `${Math.max(parseFloat(getComputedStyle(block.el).fontSize) * 0.8, 11)}px`,
  }
}

onMounted(render)

watch(() => paperStore.scale, render)
watch(
  () => paperStore.isTranslateMode,
  async (enabled) => {
    if (enabled) {
      await nextTick()
      await loadTranslations()
    }
  },
)
</script>

<template>
  <div
    class="pdf-page relative mx-auto bg-white shadow-card my-3"
    :style="{ width: `${pageWidth}px`, height: `${pageHeight}px` }"
    @mouseup="handleMouseUp"
  >
    <canvas ref="canvasRef" class="block" />

    <div
      ref="textLayerRef"
      class="textLayer absolute inset-0"
    />

    <!-- Translation overlay -->
    <div
      v-if="paperStore.isTranslateMode"
      class="absolute inset-0 pointer-events-none"
    >
      <div
        v-for="(block, idx) in translationBlocks.filter((b) => b.translation)"
        :key="`tr-${idx}`"
        class="absolute bg-white/90 text-primary-dark px-1 rounded-sm border border-primary/10"
        :style="{
          ...getBlockPosition(block),
          lineHeight: '1.4',
        }"
      >
        {{ block.translation }}
      </div>
    </div>
  </div>
</template>

<style>
.pdf-page .textLayer {
  opacity: 0.25;
  line-height: 1;
  text-size-adjust: none;
  forced-color-adjust: none;
}

.pdf-page .textLayer :is(span, br) {
  color: transparent;
  position: absolute;
  white-space: pre;
  cursor: text;
  transform-origin: 0% 0%;
}

.pdf-page .textLayer span::selection {
  background: rgba(0, 100, 200, 0.3);
}

.pdf-page .textLayer span:hover {
  background: rgba(var(--color-primary-rgb, 59, 130, 246), 0.05);
  border-radius: 2px;
}
</style>
