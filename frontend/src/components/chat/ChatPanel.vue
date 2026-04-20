<script setup lang="ts">
import { ref, computed, nextTick, watch } from 'vue'
import { SendOutlined, DeleteOutlined } from '@ant-design/icons-vue'
import { useChatStore, usePaperStore } from '@/stores'
import type { ChatContext } from '@/types'

const props = defineProps<{
  selectedContext?: { text: string; pageNumber: number } | null
}>()

const chatStore = useChatStore()
const paperStore = usePaperStore()

const inputText = ref('')
const messagesRef = ref<HTMLDivElement>()

const paperId = computed(() => paperStore.currentPaper?.id ?? '')

function scrollToBottom() {
  nextTick(() => {
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  })
}

watch(
  () => chatStore.messages.length,
  () => scrollToBottom(),
)

async function send() {
  const text = inputText.value.trim()
  if (!text || !paperId.value) return

  const context: ChatContext | undefined = props.selectedContext
    ? {
        selectedText: props.selectedContext.text,
        pageNumber: props.selectedContext.pageNumber,
      }
    : undefined

  inputText.value = ''
  await chatStore.sendMessage(paperId.value, text, context)
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    send()
  }
}

function clearChat() {
  if (chatStore.currentSession) {
    chatStore.clearSession(chatStore.currentSession.id)
  }
}
</script>

<template>
  <div class="flex flex-col h-full">
    <!-- Messages -->
    <div ref="messagesRef" class="flex-1 overflow-auto p-4 space-y-3">
      <!-- Empty state -->
      <div
        v-if="chatStore.messages.length === 0"
        class="flex items-center justify-center h-full"
      >
        <div class="text-center text-text-muted">
          <div class="w-12 h-12 mx-auto mb-3 rounded-xl bg-accent/10 flex items-center justify-center">
            <span class="text-2xl">💬</span>
          </div>
          <p class="text-sm">选中论文中的文字，然后提问</p>
          <p class="text-xs mt-1">AI 会结合论文上下文和领域知识回答</p>
        </div>
      </div>

      <!-- Message list -->
      <div
        v-for="msg in chatStore.messages"
        :key="msg.id"
        class="flex"
        :class="msg.role === 'user' ? 'justify-end' : 'justify-start'"
      >
        <div
          class="max-w-[85%] rounded-xl px-3.5 py-2.5 text-sm leading-relaxed"
          :class="
            msg.role === 'user'
              ? 'bg-primary text-white rounded-br-sm'
              : 'bg-surface-alt text-text-primary rounded-bl-sm'
          "
        >
          <!-- Context badge -->
          <div
            v-if="msg.context?.selectedText"
            class="text-xs mb-1.5 pb-1.5 border-b"
            :class="
              msg.role === 'user'
                ? 'border-white/20 text-white/80'
                : 'border-border text-text-muted'
            "
          >
            📌 「{{ msg.context.selectedText.slice(0, 60) }}{{ msg.context.selectedText.length > 60 ? '...' : '' }}」
          </div>
          <p class="whitespace-pre-wrap">{{ msg.content }}</p>
        </div>
      </div>

      <!-- Loading indicator -->
      <div v-if="chatStore.loading" class="flex justify-start">
        <div class="bg-surface-alt rounded-xl px-4 py-3 rounded-bl-sm">
          <div class="flex gap-1">
            <span class="w-2 h-2 bg-text-muted rounded-full animate-bounce" style="animation-delay: 0ms" />
            <span class="w-2 h-2 bg-text-muted rounded-full animate-bounce" style="animation-delay: 150ms" />
            <span class="w-2 h-2 bg-text-muted rounded-full animate-bounce" style="animation-delay: 300ms" />
          </div>
        </div>
      </div>
    </div>

    <!-- Selected context preview -->
    <div
      v-if="selectedContext"
      class="mx-4 px-3 py-2 bg-primary/5 border border-primary/20 rounded-lg text-xs text-primary"
    >
      📌 已选中：「{{ selectedContext.text.slice(0, 80) }}{{ selectedContext.text.length > 80 ? '...' : '' }}」
      <span class="text-text-muted ml-1">第 {{ selectedContext.pageNumber }} 页</span>
    </div>

    <!-- Input area -->
    <div class="p-3 border-t border-border">
      <div class="flex items-end gap-2">
        <textarea
          v-model="inputText"
          rows="2"
          placeholder="输入问题，AI 会结合论文上下文回答..."
          class="flex-1 resize-none rounded-lg border border-border bg-surface px-3 py-2
                 text-sm text-text-primary placeholder:text-text-muted
                 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/30"
          @keydown="handleKeydown"
        />
        <div class="flex flex-col gap-1.5">
          <button
            class="w-9 h-9 rounded-lg bg-primary text-white flex items-center justify-center
                   hover:bg-primary-light transition-colors disabled:opacity-40"
            :disabled="!inputText.trim() || chatStore.loading"
            @click="send"
          >
            <SendOutlined class="text-sm" />
          </button>
          <button
            class="w-9 h-9 rounded-lg text-text-muted flex items-center justify-center
                   hover:bg-surface-alt hover:text-danger transition-colors"
            title="清空对话"
            @click="clearChat"
          >
            <DeleteOutlined class="text-sm" />
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
