import { useContext } from 'react'

import {
  ChatThreadsContext,
  type ChatThreadsContextValue,
} from '@/pages/chat/chat-threads-context-value'

export function useChatThreads(): ChatThreadsContextValue {
  const context = useContext(ChatThreadsContext)
  if (!context) {
    throw new Error('useChatThreads must be used within ChatThreadsProvider')
  }
  return context
}
