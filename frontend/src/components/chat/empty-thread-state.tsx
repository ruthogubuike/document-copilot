import { ArrowUpRightIcon, LightbulbIcon } from 'lucide-react'

import { CHAT_TIPS, EXAMPLE_PROMPTS } from '@/lib/chat/suggestions'

type EmptyThreadStateProps = {
  disabled: boolean
  onPromptSelect: (text: string) => void
}

export function EmptyThreadState({
  disabled,
  onPromptSelect,
}: EmptyThreadStateProps) {
  return (
    <div className="flex flex-1 items-center justify-center p-4">
      <div className="flex w-full max-w-2xl flex-col items-center gap-4 text-center sm:gap-5">
        <div className="flex flex-col items-center gap-2.5">
          <img
            src="/favicon.png"
            alt=""
            aria-hidden
            className="size-10 object-contain"
          />
          <div className="space-y-1">
            <h1 className="text-xl font-semibold tracking-tight">
              Ask your filings anything
            </h1>
            <p className="text-muted-foreground mx-auto max-w-md text-sm leading-relaxed">
              Query the SEC corpus in plain English. Every answer is grounded in
              real filings and cites its sources, so you can verify each figure.
            </p>
          </div>
        </div>

        <div className="grid w-full gap-2 text-left sm:grid-cols-2">
          {EXAMPLE_PROMPTS.map((prompt) => (
            <button
              key={prompt}
              type="button"
              className="group border-border bg-card hover:border-primary/40 hover:bg-accent/60 flex items-center gap-2.5 rounded-lg border px-3 py-2.5 text-sm transition-colors disabled:pointer-events-none disabled:opacity-50"
              disabled={disabled}
              onClick={() => onPromptSelect(prompt)}
            >
              <span className="flex-1 leading-snug">{prompt}</span>
              <ArrowUpRightIcon className="text-muted-foreground group-hover:text-primary size-4 shrink-0 transition-colors" />
            </button>
          ))}
        </div>

        <div className="border-border/70 bg-muted/40 w-full rounded-lg border p-3 text-left">
          <div className="text-muted-foreground mb-1.5 flex items-center gap-2 text-xs font-medium tracking-wide uppercase">
            <LightbulbIcon className="size-3.5" />
            Tips for sharper answers
          </div>
          <ul className="text-muted-foreground space-y-1 text-sm leading-relaxed">
            {CHAT_TIPS.map((tip) => (
              <li key={tip} className="flex gap-2">
                <span className="text-primary/70 mt-px">•</span>
                <span>{tip}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  )
}
