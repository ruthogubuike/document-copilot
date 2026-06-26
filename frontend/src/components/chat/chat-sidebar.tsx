import { useState } from 'react'
import { MessageSquarePlusIcon, LogOutIcon, Trash2Icon } from 'lucide-react'
import { Link, NavLink, useNavigate, useParams } from 'react-router-dom'

import { BrandLogo } from '@/components/brand-logo'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
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
  SidebarMenuAction,
  SidebarMenuButton,
  SidebarMenuItem,
} from '@/components/ui/sidebar'
import { formatRelativeTime } from '@/lib/format-relative-time'
import { useAuth } from '@/lib/use-auth'
import { useChatThreads } from '@/pages/chat/use-chat-threads'

export function ChatSidebar() {
  const navigate = useNavigate()
  const { threadId } = useParams()
  const { signOut, user } = useAuth()
  const { threads, isLoading, error, deleteThread } = useChatThreads()
  const [pendingDelete, setPendingDelete] = useState<{
    id: string
    title: string
  } | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)

  const fullName = user?.user_metadata.full_name
  const displayName = typeof fullName === 'string' ? fullName.trim() : ''
  const email = user?.email ?? ''
  const primaryLabel = displayName || email || 'Account'
  const initials = getInitials(primaryLabel)

  async function confirmDelete() {
    if (!pendingDelete) {
      return
    }
    const { id } = pendingDelete
    setIsDeleting(true)
    try {
      await deleteThread(id)
      if (threadId === id) {
        navigate('/chat')
      }
      setPendingDelete(null)
    } finally {
      setIsDeleting(false)
    }
  }

  return (
    <Sidebar>
      <SidebarHeader className="border-b px-4 py-4">
        <div className="flex flex-col gap-3">
          <Link
            to="/chat"
            aria-label="Document Copilot home"
            className="rounded-md outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring"
          >
            <BrandLogo />
          </Link>
          <Button
            type="button"
            className="w-full justify-start"
            onClick={() => {
              navigate('/chat')
            }}
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
                  <SidebarMenuAction
                    showOnHover
                    aria-label={`Delete ${thread.title}`}
                    title="Delete conversation"
                    className="top-2 text-muted-foreground hover:text-destructive"
                    onClick={() => {
                      setPendingDelete({ id: thread.id, title: thread.title })
                    }}
                  >
                    <Trash2Icon />
                  </SidebarMenuAction>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="border-t p-2">
        <div className="flex items-center gap-2.5 rounded-md px-1.5 py-1.5">
          <span className="bg-brand-gradient grid size-8 shrink-0 place-items-center rounded-full text-xs font-semibold text-white ring-1 ring-white/15">
            {initials}
          </span>
          <div className="flex min-w-0 flex-col">
            <span className="truncate text-sm leading-tight font-medium">
              {primaryLabel}
            </span>
            {displayName && email ? (
              <span className="text-muted-foreground truncate text-xs leading-tight">
                {email}
              </span>
            ) : null}
          </div>
        </div>
        <button
          type="button"
          onClick={() => {
            void signOut()
          }}
          className="text-muted-foreground hover:text-foreground flex w-full cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-sm underline-offset-4 transition-colors hover:underline"
        >
          <LogOutIcon className="size-4" />
          Sign out
        </button>
      </SidebarFooter>

      <AlertDialog
        open={pendingDelete !== null}
        onOpenChange={(open) => {
          if (!open && !isDeleting) {
            setPendingDelete(null)
          }
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete conversation?</AlertDialogTitle>
            <AlertDialogDescription>
              {pendingDelete
                ? `“${pendingDelete.title}” and its messages will be permanently removed. This can't be undone.`
                : null}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              variant="destructive"
              disabled={isDeleting}
              onClick={(event) => {
                event.preventDefault()
                void confirmDelete()
              }}
            >
              {isDeleting ? 'Deleting…' : 'Delete'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Sidebar>
  )
}

function getInitials(label: string): string {
  const words = label.trim().split(/\s+/).filter(Boolean)
  if (words.length >= 2) {
    return (words[0][0] + words[1][0]).toUpperCase()
  }
  const base = label.includes('@') ? label.split('@')[0] : label
  return base.slice(0, 2).toUpperCase() || '?'
}
