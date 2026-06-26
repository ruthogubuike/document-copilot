export type ChatThreadSummary = {
  id: string
  title: string
  createdAt: string
  updatedAt: string
}

import type { CitationData } from '@/lib/types/citation'

export type ChatMessagePart =
  | {
      type: 'text'
      text: string
    }
  | {
      type: 'data-citation'
      data: CitationData
    }
  | {
      type: string
      text?: string
    }

export type ChatUIMessage = {
  id: string
  role: 'user' | 'assistant' | 'system'
  parts: ChatMessagePart[]
}

export type ThreadMessagesResponse = {
  messages: ChatUIMessage[]
}
