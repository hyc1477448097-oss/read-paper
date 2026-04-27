<script setup lang="ts">
import { ref, watch } from 'vue'
import {
  FileTextOutlined,
  TranslationOutlined,
  MessageOutlined,
  BookOutlined,
  MenuUnfoldOutlined,
  ArrowRightOutlined,
} from '@ant-design/icons-vue'
import CoreContribution from '@/components/analysis/CoreContribution.vue'
import ChatPanel from '@/components/chat/ChatPanel.vue'
import ReferenceAnalysis from '@/components/analysis/ReferenceAnalysis.vue'
import { usePaperStore, useTranslationStore } from '@/stores'

const props = defineProps<{
  selectedContext?: { text: string; pageNumber: number } | null
  translationResult?: { original: string; translated: string } | null
}>()

const emit = defineEmits<{
  collapse: []
}>()

const paperStore = usePaperStore()
const translationStore = useTranslationStore()

type FuncKey = 'summary' | 'translate' | 'chat' | 'references'

const activeFunc = ref<FuncKey>('summary')
const userDomain = ref('')
const domainConfirmed = ref(false)
const domainSaving = ref(false)

watch(
  () => paperStore.currentPaper?.domain,
  (domain) => {
    userDomain.value = domain ?? ''
    domainConfirmed.value = !!domain
  },
  { immediate: true },
)

function onDomainInput() {
  domainConfirmed.value = false
}

async function confirmDomain() {
  if (domainSaving.value) return
  domainSaving.value = true
  try {
    await paperStore.updateDomain(userDomain.value)
    domainConfirmed.value = true
  } finally {
    domainSaving.value = false
  }
}

function onDomainKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter') {
    e.preventDefault()
    confirmDomain()
  }
}

const funcButtons: { key: FuncKey; label: string; icon: typeof FileTextOutlined }[] = [
  { key: 'summary', label: '结构化总结', icon: FileTextOutlined },
  { key: 'translate', label: '智能翻译', icon: TranslationOutlined },
  { key: 'chat', label: '上下文答疑', icon: MessageOutlined },
  { key: 'references', label: '引用分析', icon: BookOutlined },
]

function switchTo(key: FuncKey) {
  activeFunc.value = key
}

defineExpose({ switchTo, activeFunc, userDomain })
</script>

<template>
  <div class="flex flex-col h-full bg-panel">
    <!-- Header with collapse button -->
    <div class="h-11 flex items-center justify-between px-3 border-b border-border shrink-0">
      <span class="text-xs font-semibold text-text-secondary uppercase tracking-wider">
        智能分析
      </span>
      <button
        class="w-6 h-6 rounded flex items-center justify-center text-text-muted
               hover:bg-surface-alt hover:text-text-primary transition-colors"
        title="收起面板"
        @click="emit('collapse')"
      >
        <MenuUnfoldOutlined class="text-xs" />
      </button>
    </div>

    <!-- Function buttons row -->
    <div class="flex gap-2 px-3 py-2.5 border-b border-border shrink-0">
      <button
        v-for="btn in funcButtons"
        :key="btn.key"
        class="flex-1 flex flex-col items-center gap-1 py-2 rounded-lg text-xs font-medium
               transition-all"
        :class="
          activeFunc === btn.key
            ? 'bg-primary text-white shadow-sm shadow-primary/25'
            : 'bg-surface-alt text-text-secondary hover:bg-primary/10 hover:text-primary'
        "
        @click="activeFunc = btn.key"
      >
        <component :is="btn.icon" class="text-base" />
        <span class="leading-none">{{ btn.label }}</span>
      </button>
    </div>

    <!-- Output area -->
    <div class="flex-1 overflow-hidden">
      <Transition name="fade" mode="out-in">
        <!-- Summary -->
        <CoreContribution v-if="activeFunc === 'summary'" key="summary" />

        <!-- Translation -->
        <div
          v-else-if="activeFunc === 'translate'"
          key="translate"
          class="flex flex-col h-full overflow-hidden"
        >
          <!-- Domain input -->
          <div class="px-4 pt-3 pb-2 border-b border-border shrink-0">
            <label class="text-[10px] text-text-muted font-medium uppercase tracking-wider mb-1.5 block">
              翻译领域
            </label>
            <div class="relative flex items-center">
              <input
                v-model="userDomain"
                type="text"
                placeholder="如：计算机视觉、自然语言处理…"
                class="w-full pl-2.5 pr-8 py-1.5 text-sm rounded-md border bg-surface
                       placeholder:text-text-muted/50
                       focus:outline-none focus:ring-1 focus:ring-primary/40 focus:border-primary/40
                       transition-colors"
                :class="domainConfirmed
                  ? 'text-text-muted border-border'
                  : 'text-text-primary border-border'"
                @input="onDomainInput"
                @keydown="onDomainKeydown"
              />
              <button
                class="absolute right-1.5 w-5 h-5 rounded flex items-center justify-center
                       transition-colors"
                :class="domainConfirmed
                  ? 'text-green-500 cursor-default'
                  : 'text-text-muted hover:text-primary hover:bg-primary/10 cursor-pointer'"
                :disabled="domainSaving"
                :title="domainConfirmed ? '已保存' : '按 Enter 或点击确认'"
                @click="confirmDomain"
              >
                <ArrowRightOutlined class="text-xs" />
              </button>
            </div>
            <p class="text-[10px] text-text-muted mt-1 leading-tight">
              输入后按 Enter 确认保存；留空则使用论文 Keywords 自动识别
            </p>
          </div>

          <!-- Translation content -->
          <div class="flex-1 p-4 overflow-auto">
            <!-- Has translation result -->
            <template v-if="translationResult">
              <div class="space-y-3">
                <div class="p-3 rounded-lg bg-surface-alt">
                  <p class="text-[10px] text-text-muted mb-1.5 font-medium uppercase tracking-wider">原文</p>
                  <p class="text-sm text-text-primary leading-relaxed whitespace-pre-wrap">{{ translationResult.original }}</p>
                </div>
                <div class="p-3 rounded-lg bg-primary/5 border border-primary/10">
                  <p class="text-[10px] text-primary mb-1.5 font-medium uppercase tracking-wider">译文</p>
                  <p class="text-sm text-text-primary leading-relaxed whitespace-pre-wrap">{{ translationResult.translated }}</p>
                </div>
              </div>
            </template>

            <!-- Loading -->
            <template v-else-if="translationStore.loading">
              <div class="flex items-center justify-center h-full text-text-muted text-sm">
                正在翻译...
              </div>
            </template>

            <!-- Empty state -->
            <template v-else>
              <div class="flex flex-col items-center justify-center h-full text-center text-text-muted">
                <TranslationOutlined class="text-3xl mb-3 text-primary/40" />
                <p class="text-sm font-medium text-text-secondary mb-1">领域智能翻译</p>
                <p class="text-xs leading-relaxed max-w-[240px]">
                  在 PDF 中选中文字，翻译结果将自动显示在此处
                </p>
              </div>
            </template>
          </div>
        </div>

        <!-- Chat / Q&A -->
        <ChatPanel
          v-else-if="activeFunc === 'chat'"
          key="chat"
          :selected-context="selectedContext"
        />

        <!-- References -->
        <ReferenceAnalysis
          v-else-if="activeFunc === 'references'"
          key="references"
        />
      </Transition>
    </div>
  </div>
</template>
