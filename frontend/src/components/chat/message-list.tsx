import { useEffect, useRef } from 'react'
import type { UIMessage } from 'ai'

import { Message } from '@/components/chat/message'
import { StreamingIndicator } from '@/components/chat/streaming-indicator'
import { ScrollArea } from '@/components/ui/scroll-area'

type MessageListProps = {
  messages: UIMessage[]
  isStreaming: boolean
}

export function MessageList({ messages, isStreaming }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isStreaming])

  return (
    <ScrollArea className="flex-1 px-4">
      <div className="mx-auto flex w-full max-w-3xl flex-col gap-4 py-6">
        {messages.map((message) => (
          <Message key={message.id} message={message} />
        ))}
        {isStreaming ? <StreamingIndicator /> : null}
        <div ref={bottomRef} />
      </div>
    </ScrollArea>
  )
}
