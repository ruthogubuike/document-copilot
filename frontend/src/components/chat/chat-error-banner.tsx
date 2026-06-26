import { Link } from 'react-router-dom'

import type { ChatErrorDisplay } from '@/lib/chat/chat-errors'

type ChatErrorBannerProps = {
  error: ChatErrorDisplay
}

export function ChatErrorBanner({ error }: ChatErrorBannerProps) {
  return (
    <div className="border-destructive/30 bg-destructive/5 text-destructive mx-4 mb-2 rounded-lg border px-3 py-2 text-sm">
      <p>{error.message}</p>
      {error.showLoginLink ? (
        <p className="mt-1">
          <Link to="/login" className="underline underline-offset-2">
            Sign in
          </Link>
        </p>
      ) : null}
    </div>
  )
}
