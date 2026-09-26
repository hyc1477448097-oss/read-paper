<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import {
  BulbOutlined,
  AimOutlined,
  ReadOutlined,
  UnorderedListOutlined,
} from '@ant-design/icons-vue'
import { usePaperStore } from '@/stores'
import * as api from '@/api'
import type { PdfOutlineNode } from '@/utils/pdf-outline'
import { READING_PURPOSE_LABELS, type ReadingPurpose } from '@/types'

const paperStore = usePaperStore()
const selectedPurpose = ref<ReadingPurpose | null>(null)

const selectedOutlineKey = ref<string | null>(null)
const lastOutlineNode = ref<PdfOutlineNode | null>(null)
const chapterSummary = ref('')
const chapterSummaryLoading = ref(false)
const chapterSummaryError = ref('')
let chapterReqId = 0

function flattenOutline(nodes: PdfOutlineNode[], depth = 0): { node: PdfOutlineNode; depth: number }[] {
  const rows: { node: PdfOutlineNode; depth: number }[] = []
  for (const n of nodes) {
    rows.push({ node: n, depth })
    rows.push(...flattenOutline(n.children, depth + 1))
  }
  return rows
}

function outlineRowKey(n: PdfOutlineNode): string {
  return `${n.pageStart}::${n.title}`
}

const flatOutlineRows = computed(() =>
  paperStore.pdfOutline?.length ? flattenOutline(paperStore.pdfOutline) : [],
)

watch(
  () => paperStore.currentPaper?.id,
  () => {
    chapterReqId += 1
    chapterSummary.value = ''
    chapterSummaryError.value = ''
    chapterSummaryLoading.value = false
    selectedOutlineKey.value = null
    lastOutlineNode.value = null
  },
)

async function fetchChapterSummary(n: PdfOutlineNode, forceRefresh = false) {
  if (!paperStore.currentPaper) return

  const myId = ++chapterReqId
  chapterSummaryLoading.value = true
  chapterSummaryError.value = ''
  if (!forceRefresh) {
    chapterSummary.value = ''
  }
  try {
    const domain = paperStore.currentPaper.domain ?? undefined
    const { summary } = await api.summarizeChapter(paperStore.currentPaper.id, {
      outline_title: n.title,
      page_start: n.pageStart,
      page_end: n.pageEnd,
      domain: domain || undefined,
      force_refresh: forceRefresh,
    })
    if (myId !== chapterReqId) return
    chapterSummary.value = summary
  } catch (e: unknown) {
    if (myId !== chapterReqId) return
    const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    chapterSummaryError.value =
      typeof detail === 'string' ? detail : '章节总结加载失败'
  } finally {
    if (myId === chapterReqId) chapterSummaryLoading.value = false
  }
}

async function onOutlineClick(n: PdfOutlineNode) {
  if (!paperStore.currentPaper) return
  selectedOutlineKey.value = outlineRowKey(n)
  lastOutlineNode.value = n
  const tp = paperStore.totalPages || 1
  const page = Math.max(1, Math.min(tp, n.pageStart))
  paperStore.setPage(page)
  await fetchChapterSummary(n, false)
}

async function onRegenerateChapterSummary() {
  if (!lastOutlineNode.value || chapterSummaryLoading.value) return
  await fetchChapterSummary(lastOutlineNode.value, true)
}

async function loadSummary() {
  await paperStore.loadOneSentenceSummary()
}

async function selectPurpose(purpose: ReadingPurpose) {
  selectedPurpose.value = purpose
  await paperStore.getRecommendation(purpose)
}

onMounted(loadSummary)
</script>

<template>
  <div class="p-4 space-y-5 overflow-auto h-full">
    <!-- Innovation points -->
    <section v-if="paperStore.oneSentenceSummary?.innovations?.length">
      <div class="flex items-center gap-2 mb-2">
        <BulbOutlined class="text-warning" />
        <h4 class="text-sm font-semibold text-text-primary">创新点</h4>
      </div>
      <div class="space-y-2">
        <div
          v-for="(point, idx) in paperStore.oneSentenceSummary.innovations"
          :key="idx"
          class="p-3 rounded-lg border border-border bg-panel"
        >
          <div class="flex items-start gap-2">
            <span
              class="shrink-0 mt-0.5 w-5 h-5 rounded-full text-xs flex items-center justify-center font-semibold"
              :class="{
                'bg-danger/10 text-danger': point.significance === 'high',
                'bg-warning/10 text-warning': point.significance === 'medium',
                'bg-success/10 text-success': point.significance === 'low',
              }"
            >
              {{ idx + 1 }}
            </span>
            <div>
              <p class="text-sm font-medium text-text-primary">{{ point.title }}</p>
              <p class="text-xs text-text-secondary mt-1 leading-relaxed">
                {{ point.description }}
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Chapter summary: PDF bookmarks + AI -->
    <section>
      <div class="flex items-center gap-2 mb-2">
        <UnorderedListOutlined class="text-primary" />
        <h4 class="text-sm font-semibold text-text-primary">章节总结</h4>
      </div>
      <p class="text-[11px] text-text-muted mb-2 leading-snug">
        目录来自 PDF 嵌入书签（Outlines）。点击条目将跳转至对应页并生成总结。
      </p>
      <div v-if="!paperStore.pdfOutline?.length" class="text-xs text-text-muted py-2">
        该 PDF 未嵌入书签或尚未加载完成，无法显示目录。请使用带书签的论文，或稍后重试。
      </div>
      <div v-else class="flex gap-3 min-h-[100px]">
        <div
          class="w-[40%] shrink-0 border border-border rounded-lg p-1.5 max-h-72 overflow-y-auto text-xs"
        >
          <button
            v-for="(row, idx) in flatOutlineRows"
            :key="`${idx}-${outlineRowKey(row.node)}`"
            type="button"
            class="w-full text-left py-1 px-1.5 rounded truncate hover:bg-primary/10 transition-colors"
            :style="{ paddingLeft: `${6 + row.depth * 12}px` }"
            :class="
              selectedOutlineKey === outlineRowKey(row.node)
                ? 'bg-primary/15 text-primary font-medium'
                : 'text-text-secondary'
            "
            :title="row.node.title"
            @click="onOutlineClick(row.node)"
          >
            {{ row.node.title }}
            <span class="text-text-muted font-normal whitespace-nowrap"> p.{{ row.node.pageStart }} </span>
          </button>
        </div>
        <div
          class="flex-1 min-w-0 border border-border rounded-lg p-3 text-sm text-text-secondary leading-relaxed max-h-72 overflow-y-auto"
        >
          <template v-if="chapterSummaryLoading">
            <p class="text-text-muted text-xs">正在生成总结...</p>
          </template>
          <template v-else-if="chapterSummaryError">
            <p class="text-danger text-xs">{{ chapterSummaryError }}</p>
          </template>
          <template v-else-if="chapterSummary">
            <div class="flex justify-end mb-1.5">
              <button
                type="button"
                class="text-[11px] text-primary hover:underline disabled:opacity-50"
                :disabled="chapterSummaryLoading"
                @click="onRegenerateChapterSummary"
              >
                重新生成
              </button>
            </div>
            <p class="whitespace-pre-wrap">{{ chapterSummary }}</p>
          </template>
          <template v-else>
            <p class="text-text-muted text-xs">点击左侧目录项：中间 PDF 将滚动到对应页，此处展示该章节 AI 总结。</p>
          </template>
        </div>
      </div>
    </section>

    <!-- Reading recommendation -->
    <section>
      <div class="flex items-center gap-2 mb-2">
        <ReadOutlined class="text-success" />
        <h4 class="text-sm font-semibold text-text-primary">阅读推荐</h4>
      </div>
      <p class="text-xs text-text-muted mb-2">
        根据您的需求，推荐最值得阅读的段落：
      </p>
      <div class="flex flex-wrap gap-1.5 mb-3">
        <button
          v-for="(label, purpose) in READING_PURPOSE_LABELS"
          :key="purpose"
          class="px-2.5 py-1 rounded-md text-xs font-medium transition-colors"
          :class="
            selectedPurpose === purpose
              ? 'bg-primary text-white'
              : 'bg-surface-alt text-text-secondary hover:bg-primary/10 hover:text-primary'
          "
          @click="selectPurpose(purpose as ReadingPurpose)"
        >
          {{ label }}
        </button>
      </div>

      <div v-if="paperStore.recommendReason" class="space-y-2">
        <p class="text-xs text-primary bg-primary/5 p-2 rounded-md">
          <AimOutlined class="mr-1" />
          {{ paperStore.recommendReason }}
        </p>
        <div
          v-for="section in paperStore.recommendedSections"
          :key="section.id"
          class="p-2 rounded-md border border-primary/20 bg-primary/5 text-xs cursor-pointer
                 hover:border-primary/40 transition-colors"
        >
          <span class="font-medium text-primary">{{ section.title }}</span>
          <span class="text-text-secondary" v-if="section.summary">
            — {{ typeof section.summary === 'string' ? section.summary : section.summary.content }}
          </span>
        </div>
      </div>
    </section>
  </div>
</template>
