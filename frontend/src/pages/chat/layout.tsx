import { Outlet } from 'react-router-dom'

import { ChatSidebar } from '@/components/chat/chat-sidebar'
import { SidebarInset, SidebarProvider } from '@/components/ui/sidebar'
import { ChatThreadsProvider } from '@/pages/chat/chat-threads-context'

export function ChatLayout() {
  return (
    <SidebarProvider>
      <ChatThreadsProvider>
        <div className="flex min-h-svh w-full">
          <ChatSidebar />
          <SidebarInset className="flex min-h-svh flex-col">
            <Outlet />
          </SidebarInset>
        </div>
      </ChatThreadsProvider>
    </SidebarProvider>
  )
}
