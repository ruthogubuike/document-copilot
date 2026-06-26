import { ApiError } from '@/lib/http'

export type ChatErrorDisplay = {
  message: string
  showLoginLink: boolean
}

export function mapStreamError(message: string): ChatErrorDisplay {
  if (message === 'Not authenticated') {
    return {
      message: 'Session expired — sign in again.',
      showLoginLink: true,
    }
  }

  if (
    message === 'Network request failed' ||
    message === 'Failed to fetch' ||
    message.toLowerCase().includes('network')
  ) {
    return {
      message:
        "Can't reach the server. Check that the backend is running and CORS is configured.",
      showLoginLink: false,
    }
  }

  if (
    message.includes('Answers without citations must explicitly state') ||
    message.includes('Citation markers require matching citations') ||
    message.includes('excerpt is not a substring') ||
    message.includes('missing a [n] marker') ||
    message.includes('question asked about') ||
    message.includes('different fiscal year than')
  ) {
    return {
      message:
        'This answer could not be verified — citations were missing or invalid, or the filings did not match the requested period. The text above was not saved. Please try again.',
      showLoginLink: false,
    }
  }

  return {
    message,
    showLoginLink: false,
  }
}

export function mapApiError(error: ApiError): ChatErrorDisplay {
  if (error.status === 401) {
    return {
      message: 'Session expired — sign in again.',
      showLoginLink: true,
    }
  }

  if (error.isNetworkError) {
    return {
      message:
        "Can't reach the server. Check that the backend is running and CORS is configured.",
      showLoginLink: false,
    }
  }

  if (error.status === 403) {
    return {
      message: "You don't have access to this conversation.",
      showLoginLink: false,
    }
  }

  if (error.status === 404) {
    return {
      message: 'This conversation was not found.',
      showLoginLink: false,
    }
  }

  return {
    message: error.detail,
    showLoginLink: false,
  }
}

export function mapUnknownError(error: unknown): ChatErrorDisplay {
  if (error instanceof ApiError) {
    return mapApiError(error)
  }

  if (error instanceof Error) {
    return mapStreamError(error.message)
  }

  return {
    message: 'Something went wrong.',
    showLoginLink: false,
  }
}
