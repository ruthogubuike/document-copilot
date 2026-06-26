import { cn } from '@/lib/utils'

type BrandLogoProps = {
  showWordmark?: boolean
  className?: string
}

const SIZES = {
  mark: 'size-9',
} as const

export function BrandLogo({ showWordmark = true, className }: BrandLogoProps) {
  return (
    <div className={cn('flex items-center gap-2.5', className)}>
      <img
        src="/favicon.png"
        alt="Document Copilot"
        className={cn('shrink-0 object-contain', SIZES.mark)}
      />
      {showWordmark ? (
        <span className="flex flex-col leading-none">
          <span className="text-[0.95rem] font-semibold tracking-tight">
            Document Copilot
          </span>
          <span className="text-muted-foreground text-xs">
            SEC filing research
          </span>
        </span>
      ) : null}
    </div>
  )
}
