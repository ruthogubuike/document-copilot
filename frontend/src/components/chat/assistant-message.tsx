import { getMessageText } from '@/components/chat/message-text'
import { CitationChip } from '@/components/chat/citation-chip'
import {
  getCitationParts,
  shouldShowNoCorpusCallout,
  splitTextWithCitationMarkers,
} from '@/lib/chat/citations'
import type { CitationData } from '@/lib/types/citation'
import type { UIMessage } from 'ai'
import { cn } from '@/lib/utils'

type AssistantMessageProps = {
  message: UIMessage
  selectedCitation: CitationData | null
  onCitationSelect: (citation: CitationData) => void
}

export function AssistantMessage({
  message,
  selectedCitation,
  onCitationSelect,
}: AssistantMessageProps) {
  const text = getMessageText(message)
  const citations = getCitationParts(message)
  const segments = splitTextWithCitationMarkers(text, citations)
  const showNoCorpusCallout = shouldShowNoCorpusCallout(text, citations)

  return (
    <div className="flex w-full justify-start">
      <div className="flex max-w-[85%] flex-col gap-2">
        <div
          className={cn(
            'bg-card text-foreground ring-foreground/5 rounded-2xl rounded-bl-md px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap shadow-sm ring-1',
          )}
        >
          {segments.length > 0 ? (
            <span>
              {segments.map((segment, index) => {
                if (segment.kind === 'text') {
                  return <span key={`text-${index}`}>{segment.value}</span>
                }

                if (segment.citation) {
                  return (
                    <CitationChip
                      key={`citation-${segment.index}-${index}`}
                      citation={segment.citation}
                      selected={
                        selectedCitation?.chunkId === segment.citation.chunkId &&
                        selectedCitation.citationIndex === segment.citation.citationIndex
                      }
                      onSelect={onCitationSelect}
                    />
                  )
                }

                return (
                  <span key={`marker-${segment.index}-${index}`}>
                    [{segment.index}]
                  </span>
                )
              })}
            </span>
          ) : (
            text
          )}
        </div>

        {citations.length > 0 ? (
          <div className="flex flex-wrap gap-1.5 px-1">
            {citations.map((citation) => (
              <CitationChip
                key={`${citation.chunkId}-${citation.citationIndex}`}
                citation={citation}
                selected={
                  selectedCitation?.chunkId === citation.chunkId &&
                  selectedCitation.citationIndex === citation.citationIndex
                }
                onSelect={onCitationSelect}
              />
            ))}
          </div>
        ) : null}

        {showNoCorpusCallout ? (
          <p className="text-muted-foreground border-border bg-background rounded-lg border px-3 py-2 text-xs">
            No matching passages in the corpus — verify before using in research.
          </p>
        ) : null}
      </div>
    </div>
  )
}
