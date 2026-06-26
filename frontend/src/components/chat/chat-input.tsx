import { useState, type FormEvent, type KeyboardEvent } from 'react'

import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'

type ChatInputProps = {
  disabled: boolean
  onSubmit: (text: string) => void
}

export function ChatInput({ disabled, onSubmit }: ChatInputProps) {
  const [value, setValue] = useState('')

  function submitCurrentValue() {
    const trimmed = value.trim()
    if (!trimmed || disabled) {
      return
    }
    onSubmit(trimmed)
    setValue('')
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    submitCurrentValue()
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    // Ignore Enter while an IME composition is active (e.g. CJK input), otherwise
    // selecting a candidate with Enter would send a half-finished message.
    if (event.nativeEvent.isComposing) {
      return
    }
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      submitCurrentValue()
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="from-background bg-gradient-to-t to-transparent px-4 pb-4 pt-2"
    >
      <div className="border-border bg-card focus-within:border-primary/50 focus-within:ring-primary/15 mx-auto flex w-full max-w-3xl items-end gap-2 rounded-2xl border p-2 shadow-sm transition-colors focus-within:ring-4">
        <Textarea
          value={value}
          onChange={(event) => setValue(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about SEC filings..."
          disabled={disabled}
          rows={1}
          className="min-h-9 resize-none border-0 bg-transparent shadow-none focus-visible:border-0 focus-visible:ring-0 dark:bg-transparent"
        />
        <Button type="submit" disabled={disabled || value.trim().length === 0}>
          Send
        </Button>
      </div>
    </form>
  )
}
