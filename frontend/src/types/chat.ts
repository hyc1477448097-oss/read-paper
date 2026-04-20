export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  context?: ChatContext
}

export interface ChatContext {
  selectedText?: string
  pageNumber?: number
  sectionTitle?: string
}

export interface ChatSession {
  id: string
  paperId: string
  messages: ChatMessage[]
  createdAt: string
}
