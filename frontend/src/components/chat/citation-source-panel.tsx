import { FilingMarkdown } from '@/components/chat/filing-markdown'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { formatCitationLabel } from '@/lib/chat/citations'
import type { CitationData } from '@/lib/types/citation'
import { cn } from '@/lib/utils'

const filingDateFormatter = new Intl.DateTimeFormat(undefined, {
  month: 'long',
  day: 'numeric',
  year: 'numeric',
})

type CitationSourcePanelProps = {
  citation: CitationData | null
  onClose: () => void
}

export function CitationSourcePanel({
  citation,
  onClose,
}: CitationSourcePanelProps) {
  return (
    <Sheet
      open={citation !== null}
      onOpenChange={(open) => {
        if (!open) {
          onClose()
        }
      }}
    >
      <SheetContent side="right" className="w-full sm:max-w-md">
        {citation ? (
          <>
            <SheetHeader className="border-b pb-4">
              <div className="flex items-start gap-2 pr-8">
                <SheetTitle className="text-base leading-snug">
                  {citation.companyName}
                </SheetTitle>
                <span className="bg-muted text-muted-foreground shrink-0 rounded-md px-2 py-0.5 text-xs font-medium">
                  {citation.ticker}
                </span>
              </div>
              <SheetDescription>{formatCitationLabel(citation)}</SheetDescription>
            </SheetHeader>

            <div className="flex flex-1 flex-col gap-4 overflow-y-auto px-4 pb-4">
              <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-2 text-sm">
                <dt className="text-muted-foreground">Filing</dt>
                <dd>{citation.form}</dd>
                <dt className="text-muted-foreground">Date</dt>
                <dd>{filingDateFormatter.format(new Date(citation.filingDate))}</dd>
                {citation.page !== null ? (
                  <>
                    <dt className="text-muted-foreground">Page</dt>
                    <dd>{citation.page}</dd>
                  </>
                ) : null}
                {citation.section ? (
                  <>
                    <dt className="text-muted-foreground">Section</dt>
                    <dd>{citation.section}</dd>
                  </>
                ) : null}
              </dl>

              <div className="space-y-2">
                <p className="text-muted-foreground text-xs font-medium tracking-wide uppercase">
                  Source passage
                </p>
                {citation.context.length > 0 ? (
                  <div className="border-border divide-border divide-y overflow-hidden rounded-lg border">
                    {citation.context.map((chunk) => (
                      <div
                        key={chunk.chunkIndex}
                        className={cn(
                          'px-3 py-3 text-sm',
                          chunk.isCited
                            ? 'bg-primary/5 border-primary border-l-2'
                            : 'bg-muted/30 text-muted-foreground',
                        )}
                      >
                        {chunk.isCited ? null : (
                          <p className="mb-1.5 text-[0.65rem] font-medium tracking-wide uppercase">
                            Surrounding context
                          </p>
                        )}
                        <FilingMarkdown content={chunk.text} />
                      </div>
                    ))}
                  </div>
                ) : (
                  <blockquote className="bg-muted/50 border-border rounded-lg border px-3 py-3 text-sm leading-relaxed whitespace-pre-wrap">
                    {citation.excerpt}
                  </blockquote>
                )}
              </div>
            </div>
          </>
        ) : null}
      </SheetContent>
    </Sheet>
  )
}
