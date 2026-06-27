import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import { ProtectedRoute } from '@/components/protected-route'
import { TooltipProvider } from '@/components/ui/tooltip'
import { AuthProvider } from '@/lib/auth'
import { ChatLayout } from '@/pages/chat/layout'
import { ChatIndexPage } from '@/pages/chat/index'
import { ChatThreadPage } from '@/pages/chat/thread'
import { LoginPage } from '@/pages/login'

export default function App() {
  return (
    <AuthProvider>
      <TooltipProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/signup" element={<Navigate to="/login" replace />} />
            <Route element={<ProtectedRoute />}>
              <Route path="/" element={<Navigate to="/chat" replace />} />
              <Route path="/chat" element={<ChatLayout />}>
                <Route index element={<ChatIndexPage />} />
                <Route path=":threadId" element={<ChatThreadPage />} />
              </Route>
            </Route>
          </Routes>
        </BrowserRouter>
      </TooltipProvider>
    </AuthProvider>
  )
}
