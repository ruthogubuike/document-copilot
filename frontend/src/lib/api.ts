import { http } from '@/lib/http'
import type {
  ChatThreadSummary,
  ThreadMessagesResponse,
} from '@/lib/types/chat'

export type CurrentUser = {
  id: string
  email: string
}

export const api = {
  get: http.get,
  post: http.post,
  put: http.put,
  patch: http.patch,
  delete: http.delete,

  getMe(): Promise<CurrentUser> {
    return http.get<CurrentUser>('/me')
  },

  listThreads(): Promise<ChatThreadSummary[]> {
    return http.get<ChatThreadSummary[]>('/chat/threads')
  },

  createThread(title?: string): Promise<ChatThreadSummary> {
    return http.post<ChatThreadSummary>('/chat/threads', title ? { title } : {})
  },

  deleteThread(threadId: string): Promise<void> {
    return http.delete<void>(`/chat/threads/${threadId}`)
  },

  getThreadMessages(threadId: string): Promise<ThreadMessagesResponse> {
    return http.get<ThreadMessagesResponse>(`/chat/threads/${threadId}/messages`)
  },
}
