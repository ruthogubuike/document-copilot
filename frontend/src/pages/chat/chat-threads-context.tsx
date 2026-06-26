import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

import { api } from '@/lib/api'
import { ApiError } from '@/lib/http'
import type { ChatThreadSummary } from '@/lib/types/chat'
import { ChatThreadsContext } from '@/pages/chat/chat-threads-context-value'

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

  const deleteThread = useCallback(async (threadId: string) => {
    await api.deleteThread(threadId)
    setThreads((current) => current.filter((thread) => thread.id !== threadId))
  }, [])

  const value = useMemo(
    () => ({
      threads,
      isLoading,
      error,
      refreshThreads,
      createThread,
      deleteThread,
    }),
    [threads, isLoading, error, refreshThreads, createThread, deleteThread],
  )

  return (
    <ChatThreadsContext.Provider value={value}>
      {children}
    </ChatThreadsContext.Provider>
  )
}
