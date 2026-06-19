import { useState } from 'react'
import { MessageSquarePlusIcon, LogOutIcon } from 'lucide-react'
import { NavLink, useNavigate, useParams } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from '@/components/ui/sidebar'
import { formatRelativeTime } from '@/lib/format-relative-time'
import { useAuth } from '@/lib/auth'
import { useChatThreads } from '@/pages/chat/chat-threads-context'

export function ChatSidebar() {
  const navigate = useNavigate()
  const { threadId } = useParams()
  const { signOut } = useAuth()
  const { threads, isLoading, error, createThread } = useChatThreads()
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
    <Sidebar>
      <SidebarHeader className="border-b px-4 py-4">
        <div className="flex flex-col gap-3">
          <div>
            <p className="text-sm font-semibold">Document Copilot</p>
            <p className="text-muted-foreground text-xs">SEC filing research</p>
          </div>
          <Button
            type="button"
            className="w-full justify-start"
            onClick={() => {
              void handleNewChat()
            }}
            disabled={isCreating}
          >
            <MessageSquarePlusIcon />
            New chat
          </Button>
        </div>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Conversations</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {isLoading ? (
                <SidebarMenuItem>
                  <SidebarMenuButton disabled>Loading...</SidebarMenuButton>
                </SidebarMenuItem>
              ) : null}
              {error ? (
                <SidebarMenuItem>
                  <SidebarMenuButton disabled>{error}</SidebarMenuButton>
                </SidebarMenuItem>
              ) : null}
              {!isLoading && !error && threads.length === 0 ? (
                <SidebarMenuItem>
                  <SidebarMenuButton disabled>No conversations yet</SidebarMenuButton>
                </SidebarMenuItem>
              ) : null}
              {threads.map((thread) => (
                <SidebarMenuItem key={thread.id}>
                  <SidebarMenuButton
                    asChild
                    isActive={threadId === thread.id}
                    className="h-auto items-start py-2"
                  >
                    <NavLink to={`/chat/${thread.id}`}>
                      <div className="flex min-w-0 flex-col gap-0.5">
                        <span className="truncate font-medium">{thread.title}</span>
                        <span className="text-muted-foreground text-xs">
                          {formatRelativeTime(thread.updatedAt)}
                        </span>
                      </div>
                    </NavLink>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="border-t p-2">
        <Button
          type="button"
          variant="ghost"
          className="w-full justify-start"
          onClick={() => {
            void signOut()
          }}
        >
          <LogOutIcon />
          Sign out
        </Button>
      </SidebarFooter>
    </Sidebar>
  )
}
