import { Button } from '@/components/ui/button'
import { formatCitationLabel } from '@/lib/chat/citations'
import type { CitationData } from '@/lib/types/citation'
import { cn } from '@/lib/utils'

type CitationChipProps = {
  citation: CitationData
  selected?: boolean
  onSelect: (citation: CitationData) => void
}

export function CitationChip({
  citation,
  selected = false,
  onSelect,
}: CitationChipProps) {
  return (
    <Button
      type="button"
      variant="outline"
      size="xs"
      aria-pressed={selected}
      className={cn(
        'mx-0.5 inline-flex h-auto max-w-full align-baseline px-1.5 py-0 font-normal',
        selected && 'border-primary bg-primary/10',
      )}
      onClick={() => {
        onSelect(citation)
      }}
    >
      <span className="truncate">{formatCitationLabel(citation)}</span>
    </Button>
  )
}
