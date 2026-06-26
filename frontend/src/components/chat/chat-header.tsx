import { useParams } from 'react-router-dom'

import { Separator } from '@/components/ui/separator'
import { SidebarTrigger } from '@/components/ui/sidebar'
import { useChatThreads } from '@/pages/chat/use-chat-threads'

export function ChatHeader() {
  const { threadId } = useParams()
  const { threads } = useChatThreads()
  const activeThread = threads.find((thread) => thread.id === threadId)
  const title = activeThread?.title ?? 'New chat'

  return (
    <header className="bg-background/80 flex h-12 shrink-0 items-center gap-2 border-b px-2 backdrop-blur-sm">
      <SidebarTrigger aria-label="Toggle sidebar" />
      <Separator orientation="vertical" className="h-5" />
      <span className="truncate text-sm font-medium">{title}</span>
    </header>
  )
}
