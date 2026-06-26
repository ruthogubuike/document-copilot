import { createContext } from 'react'

import type { ChatThreadSummary } from '@/lib/types/chat'

export type ChatThreadsContextValue = {
  threads: ChatThreadSummary[]
  isLoading: boolean
  error: string | null
  refreshThreads: () => Promise<void>
  createThread: () => Promise<string>
  deleteThread: (threadId: string) => Promise<void>
}

export const ChatThreadsContext =
  createContext<ChatThreadsContextValue | null>(null)
