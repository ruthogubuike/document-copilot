type StreamingIndicatorProps = {
  status: 'submitted' | 'streaming'
}

const STATUS_LABELS: Record<StreamingIndicatorProps['status'], string> = {
  submitted: 'Searching filings…',
  streaming: 'Drafting answer…',
}

export function StreamingIndicator({ status }: StreamingIndicatorProps) {
  return (
    <div className="flex justify-start">
      <div className="bg-muted text-muted-foreground flex items-center gap-2 rounded-2xl px-4 py-2 text-sm">
        <span className="flex gap-1">
          <span className="bg-muted-foreground/70 size-1.5 animate-bounce rounded-full [animation-delay:0ms]" />
          <span className="bg-muted-foreground/70 size-1.5 animate-bounce rounded-full [animation-delay:150ms]" />
          <span className="bg-muted-foreground/70 size-1.5 animate-bounce rounded-full [animation-delay:300ms]" />
        </span>
        {STATUS_LABELS[status]}
      </div>
    </div>
  )
}
