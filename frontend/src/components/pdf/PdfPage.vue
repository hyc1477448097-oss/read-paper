<script setup lang="ts">
import { ref, onMounted, watch, nextTick } from 'vue'
import { renderPage, getPageTextContent } from '@/utils/pdf'
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
const _translationOverlayRef = ref<HTMLDivElement>()
const pageWidth = ref(0)
const pageHeight = ref(0)

interface TextBlock {
  text: string
  x: number
  y: number
  width: number
  height: number
  fontSize: number
  translation?: string
}

const textBlocks = ref<TextBlock[]>([])

async function render() {
  if (!canvasRef.value || !props.pdf) return
  const { width, height } = await renderPage(
    props.pdf,
    props.pageNumber,
    canvasRef.value,
    paperStore.scale,
  )
  pageWidth.value = width
  pageHeight.value = height

  await buildTextLayer()
}

async function buildTextLayer() {
  if (!textLayerRef.value) return
  const textContent = await getPageTextContent(props.pdf, props.pageNumber)

  const blocks: TextBlock[] = []
  for (const item of textContent.items) {
    if (!('str' in item) || !item.str.trim()) continue
    const tx = item.transform
    blocks.push({
      text: item.str,
      x: tx[4] * paperStore.scale,
      y: pageHeight.value - tx[5] * paperStore.scale - item.height * paperStore.scale,
      width: item.width * paperStore.scale,
      height: item.height * paperStore.scale,
      fontSize: Math.abs(tx[0]) * paperStore.scale,
    })
  }
  textBlocks.value = blocks
}

async function loadTranslations() {
  if (!paperStore.isTranslateMode || !paperStore.currentPaper) return
  for (const block of textBlocks.value) {
    if (block.text.length < 3) continue
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

function handleParagraphClick(block: TextBlock, event: MouseEvent) {
  const target = event.currentTarget as HTMLElement
  const rect = target.getBoundingClientRect()
  emit('paragraphClick', {
    text: block.text,
    pageNumber: props.pageNumber,
    rect,
  })
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
    class="relative mx-auto bg-white shadow-card my-3"
    :style="{ width: `${pageWidth}px`, height: `${pageHeight}px` }"
    @mouseup="handleMouseUp"
  >
    <canvas ref="canvasRef" class="block" />

    <!-- Invisible text layer for selection -->
    <div
      ref="textLayerRef"
      class="absolute inset-0 select-text"
    >
      <span
        v-for="(block, idx) in textBlocks"
        :key="idx"
        class="absolute cursor-text hover:bg-primary/5 transition-colors rounded-sm group"
        :style="{
          left: `${block.x}px`,
          top: `${block.y}px`,
          width: `${block.width}px`,
          height: `${block.height}px`,
          fontSize: `${block.fontSize}px`,
          lineHeight: `${block.height}px`,
          color: 'transparent',
        }"
        @click="handleParagraphClick(block, $event)"
      >
        {{ block.text }}

        <!-- Paragraph summary trigger icon -->
        <button
          class="absolute -right-6 top-0 w-5 h-5 rounded bg-primary/10 text-primary
                 flex items-center justify-center opacity-0 group-hover:opacity-100
                 transition-opacity text-xs"
          title="段落总结"
          @click.stop="handleParagraphClick(block, $event)"
        >
          ∑
        </button>
      </span>
    </div>

    <!-- Translation overlay -->
    <div
      v-if="paperStore.isTranslateMode"
      ref="translationOverlayRef"
      class="absolute inset-0 pointer-events-none"
    >
      <div
        v-for="(block, idx) in textBlocks.filter((b) => b.translation)"
        :key="`tr-${idx}`"
        class="absolute bg-white/90 text-primary-dark px-1 rounded-sm border border-primary/10"
        :style="{
          left: `${block.x}px`,
          top: `${block.y + block.height + 2}px`,
          maxWidth: `${Math.max(block.width, 200)}px`,
          fontSize: `${Math.max(block.fontSize * 0.8, 11)}px`,
          lineHeight: '1.4',
        }"
      >
        {{ block.translation }}
      </div>
    </div>
  </div>
</template>
