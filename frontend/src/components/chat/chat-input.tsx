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
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      submitCurrentValue()
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="border-t bg-background px-4 py-4"
    >
      <div className="mx-auto flex w-full max-w-3xl items-end gap-2">
        <Textarea
          value={value}
          onChange={(event) => setValue(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about SEC filings..."
          disabled={disabled}
          rows={1}
          className="min-h-11 resize-none"
        />
        <Button type="submit" disabled={disabled || value.trim().length === 0}>
          Send
        </Button>
      </div>
    </form>
  )
}
