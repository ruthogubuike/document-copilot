import { useEffect, useState } from 'react'
import type { UIMessage } from 'ai'
import { useLocation, useParams } from 'react-router-dom'

import { ChatErrorBanner } from '@/components/chat/chat-error-banner'
import { ChatPanel } from '@/components/chat/chat-panel'
import { api } from '@/lib/api'
import { mapUnknownError } from '@/lib/chat/chat-errors'

type ChatThreadViewProps = {
  threadId: string
}

function ChatThreadView({ threadId }: ChatThreadViewProps) {
  const location = useLocation()
  const pendingPrompt =
    typeof location.state === 'object' &&
    location.state !== null &&
    'pendingPrompt' in location.state &&
    typeof location.state.pendingPrompt === 'string'
      ? location.state.pendingPrompt
      : undefined
  const [initialMessages, setInitialMessages] = useState<UIMessage[] | null>(null)
  const [loadError, setLoadError] = useState<ReturnType<
    typeof mapUnknownError
  > | null>(null)

  useEffect(() => {
    let cancelled = false

    void api
      .getThreadMessages(threadId)
      .then((response) => {
        if (!cancelled) {
          setInitialMessages(response.messages as UIMessage[])
        }
      })
      .catch((error: unknown) => {
        if (cancelled) {
          return
        }
        setLoadError(mapUnknownError(error))
      })

    return () => {
      cancelled = true
    }
  }, [threadId])

  if (loadError) {
    return (
      <div className="flex flex-1 items-center justify-center p-8">
        <div className="max-w-md">
          <ChatErrorBanner error={loadError} />
        </div>
      </div>
    )
  }

  if (initialMessages === null) {
    return (
      <div className="flex flex-1 items-center justify-center p-8">
        <p className="text-muted-foreground text-sm">Loading conversation...</p>
      </div>
    )
  }

  return (
    <ChatPanel
      threadId={threadId}
      initialMessages={initialMessages}
      pendingPrompt={pendingPrompt}
    />
  )
}

export function ChatThreadPage() {
  const { threadId } = useParams()

  if (!threadId) {
    return null
  }

  return <ChatThreadView key={threadId} threadId={threadId} />
}
