import { useEffect, useState } from 'react'
import type { UIMessage } from 'ai'
import { useParams } from 'react-router-dom'

import { ChatPanel } from '@/components/chat/chat-panel'
import { api } from '@/lib/api'
import { ApiError } from '@/lib/http'

type ChatThreadViewProps = {
  threadId: string
}

function ChatThreadView({ threadId }: ChatThreadViewProps) {
  const [initialMessages, setInitialMessages] = useState<UIMessage[] | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)

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
        if (error instanceof ApiError) {
          setLoadError(error.detail)
          return
        }
        setLoadError('Could not load this conversation.')
      })

    return () => {
      cancelled = true
    }
  }, [threadId])

  if (loadError) {
    return (
      <div className="flex flex-1 items-center justify-center p-8">
        <p className="text-destructive text-sm">{loadError}</p>
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

  return <ChatPanel threadId={threadId} initialMessages={initialMessages} />
}

export function ChatThreadPage() {
  const { threadId } = useParams()

  if (!threadId) {
    return null
  }

  return <ChatThreadView key={threadId} threadId={threadId} />
}
