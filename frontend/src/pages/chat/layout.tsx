import { Outlet } from 'react-router-dom'

import { ChatHeader } from '@/components/chat/chat-header'
import { ChatSidebar } from '@/components/chat/chat-sidebar'
import { SidebarInset, SidebarProvider } from '@/components/ui/sidebar'
import { ChatThreadsProvider } from '@/pages/chat/chat-threads-context'

export function ChatLayout() {
  return (
    <SidebarProvider>
      <ChatThreadsProvider>
        <div className="flex h-svh w-full overflow-hidden">
          <ChatSidebar />
          <SidebarInset className="flex min-h-0 min-w-0 flex-col">
            <ChatHeader />
            <Outlet />
          </SidebarInset>
        </div>
      </ChatThreadsProvider>
    </SidebarProvider>
  )
}
