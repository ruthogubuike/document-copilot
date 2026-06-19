import type { UIMessage } from 'ai'

import { cn } from '@/lib/utils'

import { getMessageText } from '@/components/chat/message-text'

type MessageProps = {
  message: UIMessage
}

export function Message({ message }: MessageProps) {
  const text = getMessageText(message)
  const isUser = message.role === 'user'

  return (
    <div
      className={cn('flex w-full', isUser ? 'justify-end' : 'justify-start')}
    >
      <div
        className={cn(
          'max-w-[85%] rounded-2xl px-4 py-2 text-sm leading-relaxed whitespace-pre-wrap',
          isUser
            ? 'bg-primary text-primary-foreground'
            : 'bg-muted text-foreground',
        )}
      >
        {text}
      </div>
    </div>
  )
}
