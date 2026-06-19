import { env } from '@/lib/env'
import { getAccessToken } from '@/lib/supabase'

const DEFAULT_TIMEOUT_MS = 30_000

type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'

export type RequestOptions = {
  body?: unknown
  timeoutMs?: number
  signal?: AbortSignal
}

export class ApiError extends Error {
  readonly status: number
  readonly detail: string
  readonly isNetworkError: boolean

  constructor(options: {
    message: string
    status: number
    detail: string
    isNetworkError?: boolean
  }) {
    super(options.message)
    this.name = 'ApiError'
    this.status = options.status
    this.detail = options.detail
    this.isNetworkError = options.isNetworkError ?? false
  }
}

function joinUrl(base: string, path: string): string {
  const normalizedBase = base.replace(/\/$/, '')
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${normalizedBase}${normalizedPath}`
}

async function parseErrorDetail(response: Response): Promise<string> {
  try {
    const body: unknown = await response.json()
    if (typeof body === 'object' && body !== null && 'detail' in body) {
      const { detail } = body as { detail: unknown }
      if (typeof detail === 'string') {
        return detail
      }
      if (Array.isArray(detail)) {
        return detail
          .map((item) => {
            if (typeof item === 'string') {
              return item
            }
            if (
              typeof item === 'object' &&
              item !== null &&
              'msg' in item &&
              typeof item.msg === 'string'
            ) {
              return item.msg
            }
            return JSON.stringify(item)
          })
          .join(', ')
      }
    }
  } catch {
    // Response body is not JSON.
  }

  return response.statusText || 'Request failed'
}

async function request<T>(
  method: HttpMethod,
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS
  const timeoutController = new AbortController()
  const timeoutId = window.setTimeout(() => timeoutController.abort(), timeoutMs)

  const headers = new Headers({
    Accept: 'application/json',
  })

  if (options.body !== undefined) {
    headers.set('Content-Type', 'application/json')
  }

  const accessToken = await getAccessToken()
  if (accessToken) {
    headers.set('Authorization', `Bearer ${accessToken}`)
  }

  try {
    const response = await fetch(joinUrl(env.apiBaseUrl, path), {
      method,
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      signal: options.signal ?? timeoutController.signal,
    })

    if (!response.ok) {
      const detail = await parseErrorDetail(response)
      throw new ApiError({
        message: detail,
        status: response.status,
        detail,
      })
    }

    if (response.status === 204) {
      return undefined as T
    }

    return (await response.json()) as T
  } catch (error) {
    if (error instanceof ApiError) {
      throw error
    }

    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new ApiError({
        message: 'Request timed out',
        status: 0,
        detail: 'Request timed out',
        isNetworkError: true,
      })
    }

    throw new ApiError({
      message: 'Network request failed',
      status: 0,
      detail: 'Network request failed',
      isNetworkError: true,
    })
  } finally {
    window.clearTimeout(timeoutId)
  }
}

export const http = {
  get<T>(path: string, options?: Omit<RequestOptions, 'body'>): Promise<T> {
    return request<T>('GET', path, options)
  },

  post<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T> {
    return request<T>('POST', path, { ...options, body })
  },

  put<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T> {
    return request<T>('PUT', path, { ...options, body })
  },

  patch<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T> {
    return request<T>('PATCH', path, { ...options, body })
  },

  delete<T>(path: string, options?: Omit<RequestOptions, 'body'>): Promise<T> {
    return request<T>('DELETE', path, options)
  },
}
