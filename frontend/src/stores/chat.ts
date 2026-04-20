import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { ChatMessage, ChatContext, ChatSession } from '@/types'
import * as api from '@/api'

export const useChatStore = defineStore('chat', () => {
  const sessions = ref<ChatSession[]>([])
  const currentSessionId = ref<string | null>(null)
  const loading = ref(false)

  const currentSession = computed(() =>
    sessions.value.find((s: ChatSession) => s.id === currentSessionId.value) ?? null,
  )

  const messages = computed(() => currentSession.value?.messages ?? [])

  function createSession(paperId: string): string {
    const id = crypto.randomUUID()
    sessions.value.push({
      id,
      paperId,
      messages: [],
      createdAt: new Date().toISOString(),
    })
    currentSessionId.value = id
    return id
  }

  function ensureSession(paperId: string): string {
    const existing = sessions.value.find((s: ChatSession) => s.paperId === paperId)
    if (existing) {
      currentSessionId.value = existing.id
      return existing.id
    }
    return createSession(paperId)
  }

  async function sendMessage(
    paperId: string,
    content: string,
    context?: ChatContext,
  ) {
    ensureSession(paperId)

    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
      context,
    }
    currentSession.value?.messages.push(userMsg)

    loading.value = true
    try {
      const { answer } = await api.askQuestion(paperId, content, {
        selectedText: context?.selectedText,
        pageNumber: context?.pageNumber,
      })

      const assistantMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: answer,
        timestamp: new Date().toISOString(),
      }
      currentSession.value?.messages.push(assistantMsg)
    } catch {
      const errorMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: '抱歉，回答生成失败，请稍后重试。',
        timestamp: new Date().toISOString(),
      }
      currentSession.value?.messages.push(errorMsg)
    } finally {
      loading.value = false
    }
  }

  function clearSession(sessionId: string) {
    const session = sessions.value.find((s: ChatSession) => s.id === sessionId)
    if (session) session.messages = []
  }

  function $reset() {
    sessions.value = []
    currentSessionId.value = null
    loading.value = false
  }

  return {
    sessions,
    currentSessionId,
    loading,
    currentSession,
    messages,
    createSession,
    ensureSession,
    sendMessage,
    clearSession,
    $reset,
  }
})
