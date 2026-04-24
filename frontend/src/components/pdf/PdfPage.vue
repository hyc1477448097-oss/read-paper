<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch, nextTick, toRaw } from 'vue'
import { normalizeUnicode, setLayerDimensions } from 'pdfjs-dist'
import { renderPage } from '@/utils/pdf'
import { removeNullCharacters } from '@/vendor/pdfjs-web/remove-null-characters'
import { TextLayerBuilder } from '@/vendor/pdfjs-web/text-layer-builder'
import { usePaperStore, useTranslationStore } from '@/stores'
import '@/vendor/pdfjs-web/text-layer-builder.css'

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

const pageRootRef = ref<HTMLDivElement>()
const canvasRef = ref<HTMLCanvasElement>()
const textLayerSlotRef = ref<HTMLDivElement>()

interface TranslationBlock {
  text: string
  el: HTMLElement
  translation?: string
}

const translationBlocks = ref<TranslationBlock[]>([])

let textLayerBuilder: TextLayerBuilder | null = null
let layerAbort: AbortController | null = null

async function render() {
  if (!canvasRef.value || !pageRootRef.value || !textLayerSlotRef.value || !props.pdf)
    return

  const rawPdf = toRaw(props.pdf)
  const pageRoot = pageRootRef.value
  const canvas = canvasRef.value
  const slot = textLayerSlotRef.value

  textLayerBuilder?.cancel()
  textLayerBuilder = null
  layerAbort?.abort()
  layerAbort = new AbortController()
  slot.replaceChildren()

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let viewport: any
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let page: any
  try {
    const result = await renderPage(
      rawPdf,
      props.pageNumber,
      canvas,
      paperStore.scale,
    )
    viewport = result.viewport
    page = result.page
  } catch {
    return
  }

  pageRoot.style.setProperty('--user-unit', String(viewport.userUnit))
  pageRoot.style.setProperty('--scale-factor', String(viewport.scale))
  pageRoot.style.setProperty('--total-scale-factor', String(viewport.scale))
  pageRoot.style.setProperty('--scale-round-x', '1px')
  pageRoot.style.setProperty('--scale-round-y', '1px')
  setLayerDimensions(pageRoot, viewport, true, false)

  const builder = new TextLayerBuilder({
    pdfPage: page,
    highlighter: null,
    accessibilityManager: null,
    enablePermissions: false,
    onAppend: (div) => {
      slot.append(div)
      attachSpanEvents(div)
      collectTranslationBlocks(div)
    },
    abortSignal: layerAbort.signal,
  })
  textLayerBuilder = builder

  try {
    await builder.render({ viewport })
  } catch {
    textLayerBuilder = null
    return
  }

  if (paperStore.isTranslateMode) {
    await nextTick()
    await loadTranslations()
  }
}

function attachSpanEvents(root: HTMLElement) {
  const spans = root.querySelectorAll<HTMLSpanElement>('span')
  for (const span of spans) {
    if (span.querySelector('span')) continue
    if (!span.textContent?.trim()) continue
    span.addEventListener('click', () => {
      const rect = span.getBoundingClientRect()
      emit('paragraphClick', {
        text: span.textContent?.trim() || '',
        pageNumber: props.pageNumber,
        rect,
      })
    })
  }
}

function collectTranslationBlocks(root: HTMLElement) {
  const blocks: TranslationBlock[] = []
  const spans = root.querySelectorAll<HTMLSpanElement>('span')
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
  const root = textLayerBuilder?.div
  const selection = window.getSelection()
  if (!selection || selection.isCollapsed || !selection.rangeCount || !root) return

  const range = selection.getRangeAt(0)
  if (!root.contains(range.commonAncestorContainer)) return

  const text = removeNullCharacters(normalizeUnicode(selection.toString())).trimEnd()
  if (text) {
    emit('textSelected', { text, pageNumber: props.pageNumber })
  }
}

function getBlockPosition(block: TranslationBlock) {
  const container = textLayerBuilder?.div
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

onBeforeUnmount(() => {
  textLayerBuilder?.cancel()
  textLayerBuilder = null
  layerAbort?.abort()
  layerAbort = null
})

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
    ref="pageRootRef"
    class="pdf-page relative mx-auto bg-white shadow-card my-3"
    @mouseup="handleMouseUp"
  >
    <div class="absolute inset-0 overflow-hidden">
      <canvas ref="canvasRef" class="block h-full w-full" />
    </div>

    <div ref="textLayerSlotRef" class="absolute inset-0 z-[1]" />

    <div
      v-if="paperStore.isTranslateMode"
      class="pointer-events-none absolute inset-0 z-[2]"
    >
      <div
        v-for="(block, idx) in translationBlocks.filter((b) => b.translation)"
        :key="`tr-${idx}`"
        class="absolute rounded-sm border border-primary/10 bg-white/90 px-1 text-primary-dark"
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
