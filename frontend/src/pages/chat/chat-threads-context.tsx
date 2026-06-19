import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

import { api } from '@/lib/api'
import { ApiError } from '@/lib/http'
import type { ChatThreadSummary } from '@/lib/types/chat'

type ChatThreadsContextValue = {
  threads: ChatThreadSummary[]
  isLoading: boolean
  error: string | null
  refreshThreads: () => Promise<void>
  createThread: () => Promise<string>
}

const ChatThreadsContext = createContext<ChatThreadsContextValue | null>(null)

export function ChatThreadsProvider({ children }: { children: ReactNode }) {
  const [threads, setThreads] = useState<ChatThreadSummary[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refreshThreads = useCallback(async () => {
    try {
      const nextThreads = await api.listThreads()
      setThreads(nextThreads)
      setError(null)
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.detail)
      } else {
        setError('Could not load conversations.')
      }
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    let cancelled = false

    void api
      .listThreads()
      .then((nextThreads) => {
        if (!cancelled) {
          setThreads(nextThreads)
          setError(null)
        }
      })
      .catch((err: unknown) => {
        if (cancelled) {
          return
        }
        if (err instanceof ApiError) {
          setError(err.detail)
        } else {
          setError('Could not load conversations.')
        }
      })
      .finally(() => {
        if (!cancelled) {
          setIsLoading(false)
        }
      })

    return () => {
      cancelled = true
    }
  }, [])

  const createThread = useCallback(async () => {
    const thread = await api.createThread()
    await refreshThreads()
    return thread.id
  }, [refreshThreads])

  const value = useMemo(
    () => ({
      threads,
      isLoading,
      error,
      refreshThreads,
      createThread,
    }),
    [threads, isLoading, error, refreshThreads, createThread],
  )

  return (
    <ChatThreadsContext.Provider value={value}>
      {children}
    </ChatThreadsContext.Provider>
  )
}

export function useChatThreads() {
  const context = useContext(ChatThreadsContext)
  if (!context) {
    throw new Error('useChatThreads must be used within ChatThreadsProvider')
  }
  return context
}
