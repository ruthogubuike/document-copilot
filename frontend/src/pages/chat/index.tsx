import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { ChatErrorBanner } from '@/components/chat/chat-error-banner'
import { ChatInput } from '@/components/chat/chat-input'
import { EmptyThreadState } from '@/components/chat/empty-thread-state'
import { mapUnknownError, type ChatErrorDisplay } from '@/lib/chat/chat-errors'
import { useChatThreads } from '@/pages/chat/use-chat-threads'

export function ChatIndexPage() {
  const navigate = useNavigate()
  const { createThread } = useChatThreads()
  const [isCreating, setIsCreating] = useState(false)
  const [error, setError] = useState<ChatErrorDisplay | null>(null)

  async function handleStart(prompt: string) {
    if (isCreating) {
      return
    }
    setIsCreating(true)
    setError(null)
    try {
      const id = await createThread()
      navigate(`/chat/${id}`, { state: { pendingPrompt: prompt } })
    } catch (err: unknown) {
      setError(mapUnknownError(err))
    } finally {
      setIsCreating(false)
    }
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex min-h-0 flex-1 flex-col overflow-auto">
        <EmptyThreadState
          disabled={isCreating}
          onPromptSelect={(text) => {
            void handleStart(text)
          }}
        />
      </div>
      {error ? <ChatErrorBanner error={error} /> : null}
      <ChatInput
        disabled={isCreating}
        onSubmit={(text) => {
          void handleStart(text)
        }}
      />
    </div>
  )
}
