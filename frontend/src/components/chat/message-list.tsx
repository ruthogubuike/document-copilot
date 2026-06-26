import { useEffect, useRef } from 'react'
import type { UIMessage } from 'ai'

import { Message } from '@/components/chat/message'
import { getMessageText } from '@/components/chat/message-text'
import { StreamingIndicator } from '@/components/chat/streaming-indicator'
import { ScrollArea } from '@/components/ui/scroll-area'
import { getCitationParts } from '@/lib/chat/citations'
import type { CitationData } from '@/lib/types/citation'

type MessageListProps = {
  messages: UIMessage[]
  isStreaming: boolean
  streamStatus: 'submitted' | 'streaming' | null
  selectedCitation: CitationData | null
  onCitationSelect: (citation: CitationData) => void
}

function isEmptyAssistantMessage(message: UIMessage): boolean {
  if (message.role !== 'assistant') {
    return false
  }
  return !getMessageText(message).trim() && getCitationParts(message).length === 0
}

function shouldShowStreamingIndicator(
  messages: UIMessage[],
  isStreaming: boolean,
  streamStatus: 'submitted' | 'streaming' | null,
): boolean {
  if (!isStreaming || !streamStatus) {
    return false
  }

  if (streamStatus === 'submitted') {
    return true
  }

  const lastMessage = messages.at(-1)
  if (lastMessage?.role === 'assistant' && !isEmptyAssistantMessage(lastMessage)) {
    return false
  }

  return true
}

export function MessageList({
  messages,
  isStreaming,
  streamStatus,
  selectedCitation,
  onCitationSelect,
}: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null)
  const viewportRef = useRef<HTMLElement | null>(null)
  const stickToBottom = useRef(true)
  const showStreamingIndicator = shouldShowStreamingIndicator(
    messages,
    isStreaming,
    streamStatus,
  )

  useEffect(() => {
    const viewport =
      bottomRef.current?.closest<HTMLElement>(
        '[data-slot="scroll-area-viewport"]',
      ) ?? null
    viewportRef.current = viewport
    if (!viewport) {
      return
    }

    const handleScroll = () => {
      const distanceFromBottom =
        viewport.scrollHeight - viewport.scrollTop - viewport.clientHeight
      stickToBottom.current = distanceFromBottom < 80
    }

    viewport.addEventListener('scroll', handleScroll, { passive: true })
    return () => viewport.removeEventListener('scroll', handleScroll)
  }, [])

  useEffect(() => {
    if (!stickToBottom.current) {
      return
    }
    // Jump instantly while tokens stream in (smooth-scrolling every token is
    // janky); animate only when a turn settles.
    bottomRef.current?.scrollIntoView({
      behavior: isStreaming ? 'auto' : 'smooth',
    })
  }, [messages, isStreaming, showStreamingIndicator])

  return (
    <ScrollArea className="min-h-0 flex-1 px-4">
      <div className="mx-auto flex w-full max-w-3xl flex-col gap-4 py-6">
        {messages.map((message, index) => {
          const isLast = index === messages.length - 1
          if (isStreaming && isLast && isEmptyAssistantMessage(message)) {
            return null
          }

          return (
            <Message
              key={message.id}
              message={message}
              selectedCitation={selectedCitation}
              onCitationSelect={onCitationSelect}
            />
          )
        })}
        {showStreamingIndicator && streamStatus ? (
          <StreamingIndicator status={streamStatus} />
        ) : null}
        <div ref={bottomRef} />
      </div>
    </ScrollArea>
  )
}
