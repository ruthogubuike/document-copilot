import type { UIMessage } from 'ai'

import { AssistantMessage } from '@/components/chat/assistant-message'
import { getMessageText } from '@/components/chat/message-text'
import type { CitationData } from '@/lib/types/citation'
import { cn } from '@/lib/utils'

type MessageProps = {
  message: UIMessage
  selectedCitation: CitationData | null
  onCitationSelect: (citation: CitationData) => void
}

export function Message({
  message,
  selectedCitation,
  onCitationSelect,
}: MessageProps) {
  if (message.role === 'assistant') {
    return (
      <AssistantMessage
        message={message}
        selectedCitation={selectedCitation}
        onCitationSelect={onCitationSelect}
      />
    )
  }

  const text = getMessageText(message)
  const isUser = message.role === 'user'

  return (
    <div
      className={cn('flex w-full', isUser ? 'justify-end' : 'justify-start')}
    >
      <div
        className={cn(
          'max-w-[85%] px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap',
          isUser
            ? 'bg-brand-gradient rounded-2xl rounded-br-md text-white shadow-sm shadow-primary/20'
            : 'bg-muted text-foreground rounded-2xl rounded-bl-md',
        )}
      >
        {text}
      </div>
    </div>
  )
}
