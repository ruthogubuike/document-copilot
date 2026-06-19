import { useMemo } from 'react'
import { useChat } from '@ai-sdk/react'
import { DefaultChatTransport, type UIMessage } from 'ai'

import { ChatInput } from '@/components/chat/chat-input'
import { MessageList } from '@/components/chat/message-list'
import { env } from '@/lib/env'
import { getAccessToken } from '@/lib/supabase'
import { useChatThreads } from '@/pages/chat/chat-threads-context'

type ChatPanelProps = {
  threadId: string
  initialMessages: UIMessage[]
}

export function ChatPanel({ threadId, initialMessages }: ChatPanelProps) {
  const { refreshThreads } = useChatThreads()

  const transport = useMemo(
    () =>
      new DefaultChatTransport({
        api: `${env.apiBaseUrl}/chat/stream`,
        headers: async () => {
          const token = await getAccessToken()
          if (!token) {
            throw new Error('Not authenticated')
          }
          return { Authorization: `Bearer ${token}` }
        },
        body: { threadId },
      }),
    [threadId],
  )

  const { messages, sendMessage, status, error } = useChat({
    id: threadId,
    messages: initialMessages,
    transport,
    onFinish: () => {
      void refreshThreads()
    },
  })

  const isBusy = status === 'submitted' || status === 'streaming'

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <MessageList messages={messages} isStreaming={isBusy} />
      {error ? (
        <div className="text-destructive px-4 pb-2 text-sm">{error.message}</div>
      ) : null}
      <ChatInput
        disabled={status !== 'ready'}
        onSubmit={(text) => {
          void sendMessage({ text })
        }}
      />
    </div>
  )
}
