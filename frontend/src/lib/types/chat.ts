export type ChatThreadSummary = {
  id: string
  title: string
  createdAt: string
  updatedAt: string
}

export type ChatMessagePart = {
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
