<script setup lang="ts">
import { ref, onMounted } from 'vue'
import {
  BulbOutlined,
  FileTextOutlined,
  AimOutlined,
  TagOutlined,
  ReadOutlined,
} from '@ant-design/icons-vue'
import { usePaperStore } from '@/stores'
import {
  SECTION_CATEGORY_LABELS,
  READING_PURPOSE_LABELS,
  type PaperSection,
  type ReadingPurpose,
  type SectionCategory,
} from '@/types'

const paperStore = usePaperStore()
const selectedPurpose = ref<ReadingPurpose | null>(null)

const categoryIcons: Record<SectionCategory, string> = {
  background: '📚',
  methodology: '⚙️',
  innovation: '💡',
  experiment: '🧪',
  discussion: '💬',
  conclusion: '🔮',
  other: '📎',
}

async function loadSummary() {
  await paperStore.loadOneSentenceSummary()
  if (paperStore.sections.every((s: PaperSection) => !s.summary)) {
    await paperStore.summarizeAll()
  }
}

async function selectPurpose(purpose: ReadingPurpose) {
  selectedPurpose.value = purpose
  await paperStore.getRecommendation(purpose)
}

onMounted(loadSummary)
</script>

<template>
  <div class="p-4 space-y-5 overflow-auto h-full">
    <!-- One-sentence summary -->
    <section v-if="paperStore.oneSentenceSummary">
      <div class="flex items-center gap-2 mb-2">
        <FileTextOutlined class="text-primary" />
        <h4 class="text-sm font-semibold text-text-primary">一句话总结</h4>
      </div>
      <p class="text-sm text-text-secondary leading-relaxed bg-primary/5 rounded-lg p-3">
        {{ paperStore.oneSentenceSummary.summary }}
      </p>
    </section>

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

    <!-- Section summaries by category -->
    <section>
      <div class="flex items-center gap-2 mb-2">
        <TagOutlined class="text-accent" />
        <h4 class="text-sm font-semibold text-text-primary">章节总结</h4>
      </div>

      <div v-if="paperStore.summarizing" class="text-center py-8 text-text-muted text-sm">
        正在分析论文结构...
      </div>

      <div v-else class="space-y-2">
        <div
          v-for="(sections, category) in paperStore.sectionsByCategory"
          :key="category"
        >
          <div class="flex items-center gap-1.5 mb-1.5">
            <span class="text-sm">{{ categoryIcons[category as SectionCategory] }}</span>
            <span class="text-xs font-medium text-text-secondary">
              {{ SECTION_CATEGORY_LABELS[category as SectionCategory] }}
            </span>
          </div>
          <div class="space-y-1.5 ml-5">
            <div
              v-for="section in sections"
              :key="section.id"
              class="p-2 rounded-md bg-surface-alt text-xs text-text-secondary leading-relaxed cursor-pointer
                     hover:bg-primary/5 transition-colors"
            >
              <span class="font-medium text-text-primary">{{ section.title }}</span>
              <span v-if="section.summary">
                — {{ typeof section.summary === 'string' ? section.summary : section.summary.content }}
              </span>
            </div>
          </div>
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
