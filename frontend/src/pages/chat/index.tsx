import { useState } from 'react'
import { MessageSquarePlusIcon } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { useChatThreads } from '@/pages/chat/chat-threads-context'

export function ChatIndexPage() {
  const navigate = useNavigate()
  const { createThread } = useChatThreads()
  const [isCreating, setIsCreating] = useState(false)

  async function handleNewChat() {
    setIsCreating(true)
    try {
      const id = await createThread()
      navigate(`/chat/${id}`)
    } finally {
      setIsCreating(false)
    }
  }

  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 p-8 text-center">
      <div className="max-w-md space-y-2">
        <h1 className="text-2xl font-semibold">Start a conversation</h1>
        <p className="text-muted-foreground text-sm">
          Ask questions about SEC filings. Responses are stubbed for now while
          retrieval is wired up.
        </p>
      </div>
      <Button
        type="button"
        onClick={() => {
          void handleNewChat()
        }}
        disabled={isCreating}
      >
        <MessageSquarePlusIcon />
        New chat
      </Button>
    </div>
  )
}
