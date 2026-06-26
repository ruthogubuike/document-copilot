import { useMemo, useState, useEffect, useRef } from 'react'
import { useChat } from '@ai-sdk/react'
import { DefaultChatTransport, type UIMessage } from 'ai'

import { ChatErrorBanner } from '@/components/chat/chat-error-banner'
import { ChatInput } from '@/components/chat/chat-input'
import { CitationSourcePanel } from '@/components/chat/citation-source-panel'
import { EmptyThreadState } from '@/components/chat/empty-thread-state'
import { MessageList } from '@/components/chat/message-list'
import { mapStreamError } from '@/lib/chat/chat-errors'
import { env } from '@/lib/env'
import { getAccessToken } from '@/lib/supabase'
import type { CitationData } from '@/lib/types/citation'
import { useChatThreads } from '@/pages/chat/use-chat-threads'

type ChatPanelProps = {
  threadId: string
  initialMessages: UIMessage[]
  pendingPrompt?: string
}

export function ChatPanel({
  threadId,
  initialMessages,
  pendingPrompt,
}: ChatPanelProps) {
  const { refreshThreads } = useChatThreads()
  const [selectedCitation, setSelectedCitation] = useState<CitationData | null>(
    null,
  )

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
  const streamStatus =
    status === 'submitted' || status === 'streaming' ? status : null
  const streamError = error ? mapStreamError(error.message) : null
  const pendingPromptSent = useRef(false)

  useEffect(() => {
    if (
      !pendingPrompt ||
      pendingPromptSent.current ||
      status !== 'ready' ||
      initialMessages.length > 0
    ) {
      return
    }

    pendingPromptSent.current = true
    void sendMessage({ text: pendingPrompt })
  }, [pendingPrompt, status, initialMessages.length, sendMessage])

  const showEmptyState = messages.length === 0 && !isBusy && !pendingPrompt

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      {showEmptyState ? (
        <EmptyThreadState
          disabled={status !== 'ready'}
          onPromptSelect={(text) => {
            void sendMessage({ text })
          }}
        />
      ) : (
        <MessageList
          messages={messages}
          isStreaming={isBusy}
          streamStatus={streamStatus}
          selectedCitation={selectedCitation}
          onCitationSelect={setSelectedCitation}
        />
      )}
      {streamError ? <ChatErrorBanner error={streamError} /> : null}
      <ChatInput
        disabled={status !== 'ready'}
        onSubmit={(text) => {
          void sendMessage({ text })
        }}
      />
      <CitationSourcePanel
        citation={selectedCitation}
        onClose={() => {
          setSelectedCitation(null)
        }}
      />
    </div>
  )
}
