<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import {
  BarChartOutlined,
  CalendarOutlined,
  BankOutlined,
} from '@ant-design/icons-vue'
import type { ReferenceAnalysis as RefAnalysis } from '@/types'
import { usePaperStore } from '@/stores'
import * as api from '@/api'

const paperStore = usePaperStore()
const analysis = ref<RefAnalysis | null>(null)
const loading = ref(false)

const maxYearCount = computed(() =>
  analysis.value
    ? Math.max(...analysis.value.yearDistribution.map((y: { year: number; count: number }) => y.count), 1)
    : 1,
)

const sourceTypeLabels: Record<string, string> = {
  journal: '期刊',
  conference: '会议',
  preprint: '预印本',
  book: '书籍',
  other: '其他',
}

async function load() {
  if (!paperStore.currentPaper) return
  loading.value = true
  try {
    analysis.value = await api.getReferenceAnalysis(paperStore.currentPaper.id)
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="p-4 space-y-5 overflow-auto h-full">
    <div v-if="loading" class="flex items-center justify-center h-40 text-text-muted text-sm">
      正在分析引用文献...
    </div>

    <template v-else-if="analysis">
      <!-- Overview -->
      <section>
        <div class="flex items-center gap-2 mb-3">
          <BarChartOutlined class="text-primary" />
          <h4 class="text-sm font-semibold text-text-primary">引用概览</h4>
        </div>
        <div class="grid grid-cols-3 gap-3">
          <div class="bg-primary/5 rounded-lg p-3 text-center">
            <p class="text-2xl font-bold text-primary">{{ analysis.totalCount }}</p>
            <p class="text-xs text-text-muted mt-1">总引用数</p>
          </div>
          <div class="bg-success/5 rounded-lg p-3 text-center">
            <p class="text-2xl font-bold text-success">
              {{ Math.round(analysis.recentThreeYearRatio * 100) }}%
            </p>
            <p class="text-xs text-text-muted mt-1">近三年占比</p>
          </div>
          <div class="bg-accent/5 rounded-lg p-3 text-center">
            <p class="text-2xl font-bold text-accent">
              {{ Math.round(analysis.recentTenYearRatio * 100) }}%
            </p>
            <p class="text-xs text-text-muted mt-1">近十年占比</p>
          </div>
        </div>
      </section>

      <!-- Year distribution -->
      <section>
        <div class="flex items-center gap-2 mb-3">
          <CalendarOutlined class="text-warning" />
          <h4 class="text-sm font-semibold text-text-primary">年份分布</h4>
        </div>
        <div class="space-y-1.5">
          <div
            v-for="item in analysis.yearDistribution"
            :key="item.year"
            class="flex items-center gap-2"
          >
            <span class="text-xs text-text-muted w-10 text-right tabular-nums">
              {{ item.year }}
            </span>
            <div class="flex-1 h-5 bg-surface-alt rounded-sm overflow-hidden">
              <div
                class="h-full bg-primary/60 rounded-sm transition-all duration-500"
                :style="{ width: `${(item.count / maxYearCount) * 100}%` }"
              />
            </div>
            <span class="text-xs text-text-secondary w-6 tabular-nums">
              {{ item.count }}
            </span>
          </div>
        </div>
      </section>

      <!-- Source type distribution -->
      <section>
        <div class="flex items-center gap-2 mb-3">
          <BankOutlined class="text-accent" />
          <h4 class="text-sm font-semibold text-text-primary">来源类型</h4>
        </div>
        <div class="space-y-2">
          <div
            v-for="item in analysis.sourceTypeDistribution"
            :key="item.type"
            class="flex items-center justify-between p-2.5 rounded-lg bg-surface-alt"
          >
            <span class="text-sm text-text-primary">
              {{ sourceTypeLabels[item.type] || item.type }}
            </span>
            <div class="flex items-center gap-2">
              <span class="text-sm font-medium text-text-primary tabular-nums">
                {{ item.count }}
              </span>
              <span class="text-xs text-text-muted tabular-nums w-12 text-right">
                {{ Math.round(item.ratio * 100) }}%
              </span>
            </div>
          </div>
        </div>
      </section>

      <!-- Top sources -->
      <section v-if="analysis.topSources.length">
        <h4 class="text-sm font-semibold text-text-primary mb-3">高频来源</h4>
        <div class="space-y-1.5">
          <div
            v-for="(src, idx) in analysis.topSources.slice(0, 10)"
            :key="idx"
            class="flex items-center justify-between py-2 px-3 rounded-md
                   hover:bg-surface-alt transition-colors"
          >
            <div class="flex items-center gap-2 min-w-0">
              <span class="text-xs text-text-muted w-4">{{ idx + 1 }}</span>
              <span class="text-xs text-text-primary truncate">{{ src.source }}</span>
              <span
                v-if="src.level"
                class="shrink-0 px-1.5 py-0.5 rounded text-[10px] font-medium bg-warning/10 text-warning"
              >
                {{ src.level }}
              </span>
            </div>
            <span class="text-xs font-medium text-text-secondary tabular-nums ml-2">
              {{ src.count }}
            </span>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>
